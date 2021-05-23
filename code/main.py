import kopf
import os
import kubernetes
import yaml


@kopf.on.create('instances')
def create_fn(spec, name, namespace, logger, **kwargs):
  
  mysql_password = spec.get('mysql_password')

  deploy = os.path.join(os.path.dirname(__file__), "manifests/mysql.yaml")
  service = os.path.join(os.path.dirname(__file__), "manifests/mysql-svc.yaml")
  svc_tmpl = open(service, 'rt').read()
  deploy_tmpl = open(deploy, 'rt').read()
  deploy_text = deploy_tmpl.format(name=name, mysql_password=mysql_password)
  svc_text = svc_tmpl.format(name=name)
  deploy_data = yaml.safe_load(deploy_text)
  svc_data = yaml.safe_load(svc_text)

  kopf.adopt(deploy_data)
  kopf.adopt(svc_data)

  api = kubernetes.client.AppsV1Api()
  deploy_obj = api.create_namespaced_deployment(
        namespace=namespace,
        body=deploy_data,
  )
  
  svc_api = kubernetes.client.CoreV1Api()
  svc_obj = svc_api.create_namespaced_service(
        namespace=namespace,
        body=svc_data,
  )

  logger.info("New mysql instance was created")  

  return {'deploy-name': deploy_obj.metadata.name}

@kopf.on.update('instances')
def update_fn(spec, status, namespace, logger, **kwargs):
  
  mysql_password = spec.get('mysql_password', None)
  
  deploy_name = status['create_fn']['deploy-name']
  deploy_patch = {'spec': {'containers': [{"name": deploy_name, "env":[{'name': "MYSQL_ROOT_PASSWORD", 'value': mysql_password}]}]}}

  api = kubernetes.client.AppsV1Api()

  obj = api.patch_namespaced_deployment(
      namespace=namespace,
      name=deploy_name,
      body=deploy_patch,
  )

  logger.info("Deploy is updated")

@kopf.on.create('databases')
def create_db(spec, name, namespace, logger,  **kwargs):
  
  label_selector = "app=mysql"
  instance_name = spec.get('instance')
  database_name = spec.get('databaseName')
  if not instance_name:
    raise kopf.PermanentError("Instance does not exist")

  api = kubernetes.client.CoreV1Api()

  resp = api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

  for x in resp.items:
    pod_name = x.metadata.name
    logger.info(name)

    resp = api.read_namespaced_pod(name=pod_name, namespace=namespace)

    exec_command = [
    '/bin/sh',
    '-c',
    "mysql -p${MYSQL_ROOT_PASSWORD} -e 'create database %s'" % (database_name,)
    ]

    resp = kubernetes.stream.stream(api.connect_get_namespaced_pod_exec, pod_name, namespace,
                          command=exec_command,
                          stderr=True, stdin=False,
                          stdout=True, tty=False)

    logger.info(resp)

@kopf.on.delete('databases')
def delete_db(spec, name, namespace, logger, **kwargs):

  label_selector = "app=mysql"

  instance_name = spec.get('instance')
  database_name = spec.get('databaseName')
  if not instance_name:
    raise kopf.PermanentError("Instance does not exist")

  api = kubernetes.client.CoreV1Api()

  resp = api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

  for x in resp.items:
    pod_name = x.metadata.name
    logger.info(name)

    resp = api.read_namespaced_pod(name=pod_name, namespace=namespace)

    exec_command = [
    '/bin/sh',
    '-c',
    'mysql -p${MYSQL_ROOT_PASSWORD} -e "drop database "' + database_name
    ]

    resp = kubernetes.stream.stream(api.connect_get_namespaced_pod_exec, pod_name, namespace,
                          command=exec_command,
                          stderr=True, stdin=False,
                          stdout=True, tty=False)

    logger.info(resp)

@kopf.on.create('users')
def create_user(spec, name, namespace, logger,  **kwargs):

  label_selector = "app=mysql"
  instance_name = spec.get('instance')
  user_name = spec.get('userName')
  mysql_password = spec.get('mysqlPassword')
  if not instance_name:
    raise kopf.PermanentError("Instance does not exist")

  api = kubernetes.client.CoreV1Api()

  resp = api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

  for x in resp.items:
    name = x.metadata.name
    logger.info(name)

    resp = api.read_namespaced_pod(name=name, namespace=namespace)

    exec_command = [
    '/bin/sh',
    '-c',
    'mysql -p${MYSQL_ROOT_PASSWORD} -e "CREATE USER \'' + user_name + '\'@\'%\' IDENTIFIED BY \'' + mysql_password + '\'"'
    ]

    resp = kubernetes.stream.stream(api.connect_get_namespaced_pod_exec, name, namespace,
                          command=exec_command,
                          stderr=True, stdin=False,
                          stdout=True, tty=False)

    logger.info(resp)

@kopf.on.delete('users')
def delete_user(spec, name, namespace, logger, **kwargs):

  label_selector = "app=mysql"

  instance_name = spec.get('instance')
  user_name = spec.get('userName')
  if not instance_name:
    raise kopf.PermanentError("Instance does not exist")

  api = kubernetes.client.CoreV1Api()

  resp = api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

  for x in resp.items:
    name = x.metadata.name
    logger.info(name)

    resp = api.read_namespaced_pod(name=name, namespace=namespace)

    exec_command = [
    '/bin/sh',
    '-c',
    'mysql -p${MYSQL_ROOT_PASSWORD} -e "DROP USER \'' + user_name + '\'@\'%\'"'
    ]

    resp = kubernetes.stream.stream(api.connect_get_namespaced_pod_exec, name, namespace,
                          command=exec_command,
                          stderr=True, stdin=False,
                          stdout=True, tty=False)

    logger.info(resp)

@kopf.on.create('permissions')
def create_permissions(spec, name, namespace, logger,  **kwargs):

  label_selector = "app=mysql"
  instance_name = spec.get('instance')
  user_name = spec.get('userName')
  permissions = spec.get('permissions')
  mysql_permissions = ""

  if "read" in permissions:
    mysql_permissions += "select"

  if "write" in permissions:
    if len(mysql_permissions) > 1:
      mysql_permissions += ","
    mysql_permissions += "insert,update,delete"

  if not instance_name:
    raise kopf.PermanentError("Instance does not exist")

  if not user_name:
    raise kopf.PermanentError("User does not exist")

  api = kubernetes.client.CoreV1Api()

  resp = api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

  for x in resp.items:
    name = x.metadata.name
    logger.info(name)

    resp = api.read_namespaced_pod(name=name, namespace=namespace)

    exec_command = [
    '/bin/sh',
    '-c',
    'mysql -p${MYSQL_ROOT_PASSWORD} -e "GRANT ' + mysql_permissions + ' ON *.* TO \'' + user_name + '\'@\'%\'"'
    ]

    resp = kubernetes.stream.stream(api.connect_get_namespaced_pod_exec, name, namespace,
                          command=exec_command,
                          stderr=True, stdin=False,
                          stdout=True, tty=False)

    logger.info(resp)

@kopf.on.delete('permissions')
def delete_permissions(spec, name, namespace, logger, **kwargs):

  label_selector = "app=mysql"

  instance_name = spec.get('instance')
  user_name = spec.get('userName')
  permissions = spec.get('permissions')
  if not instance_name:
    raise kopf.PermanentError("Instance does not exist")
  
  if not user_name:
    raise kopf.PermanentError("User does not exist")

  api = kubernetes.client.CoreV1Api()

  resp = api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

  for x in resp.items:
    name = x.metadata.name
    logger.info(name)

    resp = api.read_namespaced_pod(name=name, namespace=namespace)

    exec_command = [
    '/bin/sh',
    '-c',
    'mysql -p${MYSQL_ROOT_PASSWORD} -e "REVOKE ALL PRIVILEGES ON *.* FROM \'' + user_name + '\'@\'%\'"'
    ]

    resp = kubernetes.stream.stream(api.connect_get_namespaced_pod_exec, name, namespace,
                          command=exec_command,
                          stderr=True, stdin=False,
                          stdout=True, tty=False)

    logger.info(resp)

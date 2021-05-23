import subprocess

exportSql = "kubectl exec red-instance-7ccf597985-lx89w -- cat dump.sql > local_dump.sql"

process = subprocess.Popen(exportSql.split(), stdout=subprocess.PIPE)
output, error = process.communicate()
print(output)
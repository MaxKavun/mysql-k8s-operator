#!/bin/bash

docker build -t agent ../code

export DOCKER_IMAGE_URL=public.ecr.aws/k8a2n9l0/agent:latest

# Replace public.ecr.aws/k8a2n9l0/ with your tag from your docker image host
docker tag kops:latest ${DOCKER_IMAGE_URL}
docker push ${DOCKER_IMAGE_URL}

# Replace docker image inside deployment.yaml with yours
kubectl apply -f ../code/rbac.yaml
kubectl apply -f ../code/deployment.yaml
#!/bin/bash

export NAME=test.k8s.local
export KOPS_STATE_STORE=s3://shit2021key
kops create cluster --name=test.k8s.local --zones=eu-north-1a --node-count=1 --node-size=t3.small --master-size=t3.small
kops update cluster --name test.k8s.local --yes --admin
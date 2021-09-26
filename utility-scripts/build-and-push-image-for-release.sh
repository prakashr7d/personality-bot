#!/usr/bin/env bash

set -e

export NS_ACR_PATH="textclouddev.azurecr.io/neuralspace/dash-ecomm"

DOCKER_IMAGE_TAG=$1
echo "the latest git tag is ${DOCKER_IMAGE_TAG}"

# export NS_CORE_NLP_IMAGE_TAG=latest
docker build -t "${NS_ACR_PATH}:${DOCKER_IMAGE_TAG}" -f docker/Dockerfile .

docker tag ${NS_ACR_PATH}:${DOCKER_IMAGE_TAG} ${NS_ACR_PATH}:latest

echo "Pushing ${NS_ACR_PATH}:${DOCKER_IMAGE_TAG}"
docker push "${NS_ACR_PATH}:${DOCKER_IMAGE_TAG}"

echo "Pushing ${NS_ACR_PATH}:latest"
docker push "${NS_ACR_PATH}:latest"

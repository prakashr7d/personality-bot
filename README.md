# Dash E-Comm Bot

This is a bot for our e-comm demo
A bot that will take care of all of your shopping needs in one go.

# Demo URL and Rasa X
- Demo: [https://ns-botlibrary-ecomm.uksouth.cloudapp.azure.com/ecomm/index.html](https://ns-botlibrary-ecomm.uksouth.cloudapp.azure.com/ecomm/index.html)
- Rasa X: [https://ns-botlibrary-ecomm.uksouth.cloudapp.azure.com/](https://ns-botlibrary-ecomm.uksouth.cloudapp.azure.com/)
- Kibana: [https://ns-botlibrary-ecomm.uksouth.cloudapp.azure.com/bot-analytics/](https://ns-botlibrary-ecomm.uksouth.cloudapp.azure.com/bot-analytics/)

For username and password for both contact the product owner

## Features:
- [x] Login n Logout
- [x] Check All Orders
- [x] Show More
- [ ] Product Return/Replace
- [ ] Product Inquiry
- [ ] Personalize shopping and so on....

# Prerequisites
- Python 3.7
    If you don't have Python3.7, then consider [installing conda with python3.7](https://phoenixnap.com/kb/how-to-install-anaconda-ubuntu-18-04-or-20-04). 
    Once you have installed it, activate the base environment and then run the following instructions.
- [Docker](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/)
- Helm
- Kubernetes
- Azure CLI

# Dev Setup

### `PYTHONPATH` setup

- Pycharm: Mark `./src` as content root
- Others: Set this environment variable `export PYTHONPATH=./src`

### Environment Setup
Use the following command 

- **A Makefile** with various helpful targets. E.g.,
  ```bash
  # to install system level dependencies
  make bootstrap
   
  # Configuring NS Private PyPi repo
  # Get username and password from the project Admin
  poetry config http-basic.neuralspace <private-pypi-username> <private-pypi-password>

  # install virtual environment and project level dependencies
  make install
  
  # run unit tests
  make test
  
  # run black code formatting and isort
  make format
  
  # to run flake8 and validate code formatting
  make lint
  ```

# How to upload data in elastic search
First do:
```commandline
make install
```
To update packages
After that build docker image,
Run docker-compose up and initialize elastic search first time..
Make sure to upload data. To do that:
Run following command
```commandline
python src/dash_ecomm/elastic_search_data_upload.py
```
This command will run the script to upload data onto elasticsearch node

# Instructions on where to check kibana
When you run docker-compose up, kibana will start within 5mins
You can check it on:
```
http://localhost:5601
```

# How to run the bot with docker

### Train a model if needed

### Build the Docker image

Then, to setup image run:
```shell script
docker-compose build

```

### Train a model

```shell script
docker-compose run rasa-x poetry run rasa train
```

### Start all the services

Then, start `docker-compose.yml` to start all servers:
```commandline
docker-compose up
```

`config.yml`, `credentials.yml` and `enpoints.yml` get added to the docker image. 
Make sure to rebuild the image after making changes to these files.

### Checkout the demo
Once all the containers are up go to [http://localhost:7000](http://localhost:7000)

### NOTE:
Models trained using docker-compose won't work locally. If you are running things locally you have to train a model locally by following the instructions in the next section.

# How to run the bot without docker

### Train a model
```shell script
poetry run rasa train --config configs/local/config.yml
```

### Start action server
Then, to run, first set up your action server in one terminal window:
```bash
poetry run rasa run actions
```

### Start Duckling server
In another window, run the duckling server (for entity extraction):
```bash
docker run -p 8000:8000 rasa/duckling
```

### Start Callback server
In another window, run the callback server for reminders and scheduled requests:
```bash
poetry run python -m dash_ecomm.callback_server
```

### Start Rasa server

Then talk to your bot by running:

```bash
poetry run rasa run --enable-api --cors "*" --endpoints configs/local/endpoints.yml --credentials configs/local/credentials.yml
```

### Open demo page

Open the file in [demo/local/index.html](demo/local/index.html)

### [OPTIONAL] Run Rasa shell in Debug mode
poetry run rasa shell --debug --endpoints endpoints-local.yml

Note that `--debug` mode will produce a lot of output meant to help you understand how the bot is working
under the hood. To simply talk to the bot, you can remove this flag.


# Update the demo page locally and on prod

Note that there are two copies of the demo page. One at `demo/local` and another one at `demo/prod`. 
If you want any changes to reflect on prod then update the prod files as well


# [Prod] Config files for Prod

Config files for prod are kept in `configs/prod`. Make sure to change these files to reflect in prod.

## Overview of the files

`data/stories` - contains stories

`data/nlu` - contains NLU training data

`data/rules.yml` - contains rules

`actions.py` - contains custom action/api code

`domain.yml` - the domain file, including bot response templates

`config.yml` - training configurations for the NLU pipeline and policy ensemble

`tests/test_stories.yml` - end-to-end test stories


## Testing the bot

You can test the bot on test conversations by running  `rasa test`.
This will run [end-to-end testing](https://rasa.com/docs/rasa/user-guide/testing-your-assistant/#end-to-end-testing) on the conversations in `tests/test_stories.yml`.

Note that if duckling isn't running when you do this, you'll see some failures.

## Development workflow
##### Development workflow with just 9 simple steps

1. Start development with initializing rasa bot
2. While, developing bot first start with creating intents.
3. Now, start `Rasa X` and start interactive training
4. Add `utters` as needed directly to `domain.yml` instead of using `Rasa X` for adding them
5. Add `stories` directly into 'stories' or into their respective files
6. Add `intents` directly into `nlu.yml` or into their respective files
7. Add `rules` directly into `rules.yml` or into their respective files
6. Why to do this? <hr>
    1. Rasa x makes formating different and its not clean at all
    2. This will make flow bad and when added too many use cases it will look mess <hr>
7. Add `actions` as needed while doing interactive training
8. Make sure to follow clean code methodology
9. Commit code every day even if you did very less addition


# Deployment

## Bootstrapping
These steps need to followed while setting up the cluster for the first time

- **Create a namespace**
  ```shell script
  kubectl apply -f deployment/namespace.yml
  ```

- **Create a static IP**
  ```shell script
  az network public-ip create --resource-group <your-cluster-resource-group> --name <some-name-for-your-ip> --sku Standard --allocation-method static --query publicIp.ipAddress -o tsv
  ```
  
- **Create an Ingress Controller**
  Make sure to update the `YOUR_STATIC_IP` and `DNS_LABEL` variables 
  ```shell script
  helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx

  helm install nginx-ingress ingress-nginx/ingress-nginx \
        --namespace dash-ecomm \
        --set controller.replicaCount=2 \
        --set controller.nodeSelector."beta\.kubernetes\.io/os"=linux \
        --set defaultBackend.nodeSelector."beta\.kubernetes\.io/os"=linux \
        --set controller.admissionWebhooks.patch.nodeSelector."beta\.kubernetes\.io/os"=linux \
        --set controller.service.loadBalancerIP="YOUR_STATIC_IP" \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-dns-label-name"="ns-botlibrary-ecomm"  
  ```

- **Test if you have an external IP**
  ```shell script
  kubectl --namespace dash-ecomm get services -o wide -w nginx-ingress-ingress-nginx-controller 
  ```
  
- **Install a certificate manager if you don't have one already**
  
  Label the cert-manager namespace to disable resource validation
  ```shell script
  kubectl label namespace dash-ecomm cert-manager.io/disable-validation=true
  ```
  
  Add the Jetstack Helm repository
  ```shell script
  helm repo add jetstack https://charts.jetstack.io
  
  helm repo update
  ```
  Deploy a certificate manager on the cluster  
  
  ```shell script
  helm install \
      cert-manager \
      --namespace dash-ecomm \
      --version v0.16.1 \
      --set installCRDs=true \
      --set nodeSelector."beta\.kubernetes\.io/os"=linux \
      jetstack/cert-manager
  ```
  
- **Deploy a CA Issuer**
  ```shell script
    kubectl apply -f deployment/cluster-issuer.yml
   ```

- **Create an SSL Certificate**
  ```shell script
    kubectl apply -f deployment/certificates.yml
   ```

- **Create a username and password to protect the demo page**
  ```shell script
  # Create a username and password
  htpasswd -c auth <some-username> 
  
  # Create a kubernetes secret to store the credentials
  kubectl -n dash-ecomm create secret generic basic-auth --from-file=auth
  ```

- **Deploy RabbitMQ, Kibana, and Elasticsearch for the first time**
  - RabbitMQ
  - Elasticsearch (single node)
  - Kibana
  ```shell script
  make deploy-es-kib-rmq
  ```

- **Deploy all services for the first time**
  This deploys the following services:
  - Rasa Actions Server
  - Rasa Callback Server
  - Duckling Server
  - Rasa X
  - Ecomm Demo Page
  - Ingress for Rasa X, Rasa Core, Demo
  - Rasa event consumer (for logging and analytics)
 
  ```shell script
    make deloy-all
   ```


## Deployment - Staging

Staging deployment happens in the CI pipeline. 
Every time we merge something with master, a new version of the bot is deployed.

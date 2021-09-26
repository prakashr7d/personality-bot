# Setup the environment

SYSTEM_DEPENDENCIES := poetry==1.1.3 pre-commit coveralls flake8

.PHONY: check-py3
check-py3:
	./utility-scripts/check_python37.sh

.PHONY: install-system-deps
install-system-deps:
	pip install -U $(SYSTEM_DEPENDENCIES)


.PHONY: install-system-deps-user
install-system-deps-user:
	pip install --user -U $(SYSTEM_DEPENDENCIES)

## To install system level dependencies
.PHONY: bootstrap
bootstrap: check-py3 install-system-deps
	curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

## Install system dependencies in user dir (Linux)
.PHONY: bootstrap-user
bootstrap-user: check-py3 install-system-deps-user
	curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

.PHONY: bootstrap-mac
bootstrap-mac: check-py3 install-system-deps
	brew install azure-cli

## Install system dependencies in user dir (Linux)
.PHONY: bootstrap-user-mac
bootstrap-user-mac: check-py3 install-system-deps-user
	brew install azure-cli

## Setup poetry
.PHONY: poetry-setup
poetry-setup:
	poetry config virtualenvs.in-project true
	poetry run pip install pip==21.0.1
	poetry install --no-root
	poetry install

## Setup pre-commit
.PHONY: pre-commit-setup
pre-commit-setup:
	pre-commit install


# Setup virtual environment and dependencies
.PHONY: install
install: pre-commit-setup poetry-setup

# Environment setup for Conda
.PHONY: conda-env-setup
conda-env-setup:
	mkdir -p ${CONDA_PREFIX}/etc/conda/activate.d
	mkdir -p ${CONDA_PREFIX}/etc/conda/deactivate.d
	touch ${CONDA_PREFIX}/etc/conda/activate.d/env_vars.sh
	touch ${CONDA_PREFIX}/etc/conda/deactivate.d/env_vars.sh
	echo "export CONDA_OLD_PATH=${PATH}" >> ${CONDA_PREFIX}/etc/conda/activate.d/env_vars.sh
	echo "export PATH=${HOME}/.local/bin:${PATH}" >> ${CONDA_PREFIX}/etc/conda/activate.d/env_vars.sh
	echo "unset PATH" >> ${CONDA_PREFIX}/etc/conda/deactivate.d/env_vars.sh
	echo "export PATH=${CONDA_OLD_PATH}" >> ${CONDA_PREFIX}/etc/conda/deactivate.d/env_vars.sh

# Format code
.PHONY: format
format:
	# calling make _format within poetry make it so that we only init poetry once
	poetry run isort -rc -y src/dash_ecomm tests actions
	poetry run black src/dash_ecomm tests actions

# Flake8 to check code formatting
.PHONY: lint
lint:
	poetry run flake8 src/dash_ecomm tests actions

.PHONY: train
train:
	PYTHONPATH='./src/' poetry run rasa train

N_THREADS=1
# Run tests
.PHONY: test-nlu
test-nlu:
	PYTHONPATH='./src/' poetry run rasa test nlu --nlu data/nlu --cross-validation

.PHONY: test-core
test-core:
	PYTHONPATH='./src/' poetry run rasa test core --stories test/test_stories.yml --fail-on-prediction-errors

# Run coverage
.PHONY: coverage
coverage:
	PYTHONPATH='./src/' poetry run coverage run --concurrency=multiprocessing -m pytest tests/ -s
	poetry run coverage combine
	poetry run coverage report -m


# Run tests and coverage
.PHONY: test-coverage
test-coverage: test coverage

# Deploy all services
.PHONY: deploy-all
deploy-all:
	#duckling
	kubectl apply -f deployment/duckling/service.yml
	kubectl apply -f deployment/duckling/deployment.yml

	# rasa actions
	kubectl apply -f deployment/rasa-actions/service.yml
	kubectl apply -f deployment/rasa-actions/deployment.yml

	# callback server
	kubectl apply -f deployment/callback-server/service.yml
	kubectl apply -f deployment/callback-server/deployment.yml

	# rasa x
	kubectl apply -f deployment/rasa-x/rasa-x-service.yml
	kubectl apply -f deployment/rasa-x/rasa-x-deployment.yml
	kubectl apply -f deployment/rasa-x/rasa-x-ingress.yml

	# rasa prod
	kubectl apply -f deployment/rasa-prod/rasa-prod-service.yml
	kubectl apply -f deployment/rasa-prod/rasa-prod-deployment.yml
	kubectl apply -f deployment/rasa-prod/rasa-prod-ingress.yml

	# demo
	kubectl apply -f deployment/demo/service.yml
	kubectl apply -f deployment/demo/deployment.yml
	kubectl apply -f deployment/demo/ingress.yml

	# event consumer
	kubectl apply -f deployment/event-consumer/deployment.yml

# Restart and Rollout
.PHONY: restart-rollout
restart-rollout:
	kubectl rollout restart  -f deployment/duckling/deployment.yml
	kubectl rollout restart  -f deployment/rasa-actions/deployment.yml
	kubectl rollout restart  -f deployment/callback-server/deployment.yml
	kubectl rollout restart  -f deployment/rasa-x/rasa-x-deployment.yml
	kubectl rollout restart  -f deployment/rasa-prod/rasa-prod-deployment.yml
	kubectl rollout restart  -f deployment/demo/deployment.yml
	kubectl rollout restart  -f deployment/event-consumer/deployment.yml


# Deploy all services
.PHONY: deploy-es-kib
deploy-es-kib-rmq:
	kubectl apply -f deployment/rabbitmq/service.yml
	kubectl apply -f deployment/rabbitmq/deployment.yml

	kubectl apply -f deployment/elasticsearch/service.yml
	kubectl apply -f deployment/elasticsearch/deployment.yml

	kubectl apply -f deployment/kibana/service.yml
	kubectl apply -f deployment/kibana/deployment.yml
	kubectl apply -f deployment/ingress/deployment.yml

VERSION=""
# Build and push Docker image
.PHONY: build-and-push-for-release
build-and-push-for-release:
	./utility-scripts/build-and-push-image-for-release.sh ${VERSION}
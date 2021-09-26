FROM python:3.7.7-stretch AS BASE

RUN apt-get update \
    && apt-get --assume-yes --no-install-recommends install \
        build-essential \
        curl \
        git \
        jq \
        libgomp1 \
        vim

WORKDIR /app

# upgrade pip version
RUN pip install --no-cache-dir --upgrade pip==20.1.1

# install poetry
RUN pip install poetry==1.1.3

# config poetry
RUN poetry config virtualenvs.in-project true
RUN poetry config virtualenvs.create true

# install python dependencies
ADD pyproject.toml .
ADD poetry.lock .
RUN poetry install --no-dev

RUN rm -rf /root/.cache/pip \
    && rm -rf /root/.cache/pypoetry/cache

RUN poetry run python -m spacy download en_core_web_md
RUN poetry run python -m spacy link en_core_web_md en

ENV PYTHONPATH=./src

ADD configs/k8s/config.yml config.yml
ADD domain.yml domain.yml
ADD configs/k8s/credentials.yml credentials.yml
ADD configs/k8s/endpoints.yml endpoints.yml
ADD configs/k8s/endpoints-rasa-prod.yml endpoints-rasa-prod.yml
ADD src src
ADD actions actions
ADD data data
ADD demo demo
ADD models models

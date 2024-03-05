ARG PIP_DOWNLOAD_CACHE=/.cache/pip
ARG PYTHON_VERSION=3.11
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

FROM python:${PYTHON_VERSION} AS base_image
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

COPY requirements-dev.txt /tmp/requirements/
COPY requirements/ /tmp/requirements/requirements/
RUN python3 -m pip install pip --upgrade && pip install -r /tmp/requirements/requirements-dev.txt

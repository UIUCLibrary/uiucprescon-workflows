ARG PIP_DOWNLOAD_CACHE=/.cache/pip
ARG PYTHON_VERSION=3.11
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

FROM python:${PYTHON_VERSION}
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

COPY requirements-dev.txt /tmp/requirements/
COPY requirements/ /tmp/requirements/requirements/
RUN python3 -m pip install pip --upgrade && pip install -r /tmp/requirements/requirements-dev.txt

ARG PIP_DOWNLOAD_CACHE=/.cache/pip
ARG PIPX_HOME=/pipx
ENV PIPX_HOME=${PIPX_HOME}
ENV PIPX_BIN_DIR=${PIPX_HOME}/bin
RUN python3 -m pip install --no-cache-dir pipx && \
    pipx ensurepath && \
    mkdir -p $PIPX_HOME  && chmod -R 777 $PIPX_HOME

RUN PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install 'devpi-client<7.0' && \
    PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install 'twine'

# syntax = docker/dockerfile:1.2

ARG PIPX_HOME=/pipx
ARG PIP_DOWNLOAD_CACHE=/.cache/pip
ARG UV_CACHE_DIR=/.cache/uv
FROM ubuntu:22.04 AS wheel_builder_base
RUN rm -f /etc/apt/apt.conf.d/docker-clean
COPY ci/docker/linux/tox/apt-packages.txt /tmp/
RUN --mount=type=cache,id=apt-cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y software-properties-common gpg-agent --no-install-recommends && \
    add-apt-repository ppa:deadsnakes/ppa && \
    DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata && \
    apt-get update && \
     < /tmp/apt-packages.txt xargs apt-get install -y && \
    rm -rf /var/lib/apt/lists/*

ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
ARG PIP_DOWNLOAD_CACHE
ARG UV_CACHE_DIR
RUN mkdir -p ${PIP_DOWNLOAD_CACHE} && \
    chmod -R 777 ${PIP_DOWNLOAD_CACHE} && \
    mkdir -p ${UV_CACHE_DIR} && \
    chmod -R 777 ${UV_CACHE_DIR}

ENV UV_CACHE_DIR=${UV_CACHE_DIR}
ENV PIP_DOWNLOAD_CACHE=${PIP_DOWNLOAD_CACHE}
COPY requirements-dev.txt /tmp/python_requirements/
COPY requirements/ /tmp/python_requirements/requirements/
RUN python3 -m pip install --no-cache-dir pip --upgrade && pip3 install --no-cache-dir -r /tmp/python_requirements/requirements-dev.txt && pip3 install --no-cache-dir tox-uv

ARG PIPX_HOME
ENV PIPX_HOME=${PIPX_HOME}
ENV PIPX_BIN_DIR=${PIPX_HOME}/bin
RUN pip3 install --no-cache-dir pipx && \
    pipx ensurepath && \
    mkdir -p $PIPX_HOME  && chmod -R 777 $PIPX_HOME
RUN PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install 'devpi-client<7.0' &&  \
    PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install pip-audit

ENV QT_QPA_PLATFORM="offscreen"
ENV UV_INDEX_STRATEGY=unsafe-best-match
WORKDIR /src
CMD ["tox", "--workdir", "/tmp/tox", "--recreate"]
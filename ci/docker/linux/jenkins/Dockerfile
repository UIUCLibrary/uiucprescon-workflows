ARG PIP_DOWNLOAD_CACHE=/.cache/pip
ARG PYTHON_VERSION=3.11
ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL
ARG SONAR_SCANNER_VERSION=5.0.1.3006


FROM python:${PYTHON_VERSION} AS base_image
ARG PYTHON_VERSION
RUN rm -f /etc/apt/apt.conf.d/docker-clean
COPY ci/docker/linux/jenkins/apt-packages.txt /tmp/
RUN --mount=type=cache,id=apt-cache-python-${PYTHON_VERSION},target=/var/cache/apt \
    apt-get update && \
    apt-get install -y software-properties-common gpg-agent --no-install-recommends && \
    DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata --no-install-recommends && \
    apt-get update && \
     < /tmp/apt-packages.txt xargs apt-get install -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*


ARG PIP_EXTRA_INDEX_URL
ARG PIP_INDEX_URL

#==============================================================================
FROM base_image AS SONAR_BUILDER
RUN apt-get update && \
    apt-get install --no-install-recommends -y unzip

ARG SONAR_SCANNER_VERSION
ARG SONAR_SCANNER_HOME=/opt/sonar/${SONAR_SCANNER_VERSION}-linux
ENV SONAR_USER_HOME=/opt/sonar/.sonar
RUN curl --create-dirs -sSLo /tmp/sonar-scanner.zip \
        https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SONAR_SCANNER_VERSION}-linux.zip && \
    unzip -o /tmp/sonar-scanner.zip -d /opt/sonar/ && \
    rm /tmp/sonar-scanner.zip && \
    mkdir -p ${SONAR_USER_HOME}/cache && \
    chmod -R 777 "${SONAR_USER_HOME}" &&\
    ln -s /opt/sonar/sonar-scanner-${SONAR_SCANNER_VERSION}-linux/bin/sonar-scanner /usr/local/bin/sonar-scanner && \
    which sonar-scanner

FROM base_image
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

RUN PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install 'twine' && \
    PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install 'pip-audit'

COPY --from=SONAR_BUILDER /opt/sonar /opt/sonar/
ARG SONAR_SCANNER_VERSION
ENV SONAR_SCANNER_VERSION=${SONAR_SCANNER_VERSION}
ARG SONAR_SCANNER_HOME=/opt/sonar/${SONAR_SCANNER_VERSION}-linux
ENV SONAR_USER_HOME=/opt/sonar/.sonar
RUN ln -s /opt/sonar/sonar-scanner-${SONAR_SCANNER_VERSION}-linux/bin/sonar-scanner /usr/local/bin/sonar-scanner && \
    which sonar-scanner
RUN mkdir -p /home/user/.sonar/ && chmod -R 777 /home/user/

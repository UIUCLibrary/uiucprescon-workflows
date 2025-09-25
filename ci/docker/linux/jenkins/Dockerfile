FROM python:latest
RUN --mount=type=bind,source=./ci/docker/linux/jenkins/apt-packages.txt,target=/tmp/apt-packages.txt\
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
	rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && \
	  < /tmp/apt-packages.txt xargs apt-get install -yqq --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

FROM python:3.11-slim AS backend

ARG APT_MIRROR=https://mirrors.aliyun.com
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com
ARG PIP_TIMEOUT=120
ARG PIP_RETRIES=8

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=${PIP_TIMEOUT} \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

RUN set -eux; \
    if [ -n "$APT_MIRROR" ] && [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i "s|http://deb.debian.org/debian-security|${APT_MIRROR}/debian-security|g; s|http://deb.debian.org/debian|${APT_MIRROR}/debian|g" /etc/apt/sources.list.d/debian.sources; \
    fi; \
    apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl locales \
    && sed -i 's/# en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN set -eux; \
    PIP_ARGS="--timeout ${PIP_TIMEOUT} --retries ${PIP_RETRIES}"; \
    if [ -n "$PIP_INDEX_URL" ]; then PIP_ARGS="$PIP_ARGS -i $PIP_INDEX_URL"; fi; \
    if [ -n "$PIP_TRUSTED_HOST" ]; then PIP_ARGS="$PIP_ARGS --trusted-host $PIP_TRUSTED_HOST"; fi; \
    python -m pip install $PIP_ARGS --upgrade pip \
    && python -m pip install $PIP_ARGS -r /tmp/requirements.txt

COPY backend /app/backend
COPY scripts /app/scripts

RUN mkdir -p /app/logs /app/backend/logs /app/chroma_db /app/config

WORKDIR /app/backend

EXPOSE 5002

# Backend container now starts Flask directly. Schema migrations and
# idempotent setup have been moved to backend/migrate.py, which is
# executed by the one-shot Docker Compose "migrate" service before
# this container starts. Restarting this container no longer replays
# migrations or built-in dataset syncs.
CMD ["python", "app.py"]


# ---- migrate one-shot image (build with `--target migrate`) ----
# Builds an image whose default command is `python migrate.py`.
# This stage is used by the docker-compose `migrate` service to run
# database schema migrations automatically before backend startup,
# and can also be used standalone for manual migration operations.
FROM python:3.11-slim AS migrate

ARG APT_MIRROR=https://mirrors.aliyun.com
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com
ARG PIP_TIMEOUT=120
ARG PIP_RETRIES=8

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=${PIP_TIMEOUT} \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

RUN set -eux; \
    if [ -n "$APT_MIRROR" ] && [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i "s|http://deb.debian.org/debian-security|${APT_MIRROR}/debian-security|g; s|http://deb.debian.org/debian|${APT_MIRROR}/debian|g" /etc/apt/sources.list.d/debian.sources; \
    fi; \
    apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN set -eux; \
    PIP_ARGS="--timeout ${PIP_TIMEOUT} --retries ${PIP_RETRIES}"; \
    if [ -n "$PIP_INDEX_URL" ]; then PIP_ARGS="$PIP_ARGS -i $PIP_INDEX_URL"; fi; \
    if [ -n "$PIP_TRUSTED_HOST" ]; then PIP_ARGS="$PIP_ARGS --trusted-host $PIP_TRUSTED_HOST"; fi; \
    python -m pip install $PIP_ARGS --upgrade pip \
    && python -m pip install $PIP_ARGS -r /tmp/requirements.txt

COPY backend /app/backend
COPY scripts /app/scripts

RUN mkdir -p /app/logs /app/backend/logs /app/chroma_db /app/config

WORKDIR /app/backend

CMD ["python", "migrate.py"]

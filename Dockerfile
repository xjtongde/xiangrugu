# syntax=docker/dockerfile:1.7

ARG PYTHON_BASE=python:3.11.16-slim-bookworm@sha256:4b4c524dc3dce996864e030c7bd9c6b0e517597189fee48f48e05b499442444b

FROM ${PYTHON_BASE} AS base

ARG BUILD_DATE=unknown
ARG SOURCE_STATUS=dirty
ARG VCS_REF=unknown
ARG VERSION=0.1.0

LABEL org.opencontainers.image.title="xiangrugu" \
      org.opencontainers.image.description="Xiangrugu reproducible data-management runtime" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      io.xiangrugu.source.status="${SOURCE_STATUS}"

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROJ_NETWORK=OFF \
    TZ=Etc/UTC

WORKDIR /app

RUN test "${BUILD_DATE}" != "unknown" \
    && printf '%s\n' "${BUILD_DATE}" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' \
    && test "${VCS_REF}" != "unknown" \
    && printf '%s\n' "${VCS_REF}" | grep -Eq '^[0-9a-f]{40}$' \
    && test "${VERSION}" != "unknown" \
    && printf '%s\n' "${SOURCE_STATUS}" | grep -Eq '^(clean|dirty)$' \
    && test "$(dpkg-query -W -f='${Version}' ca-certificates)" = "20250419~deb12u1" \
    && test "$(dpkg-query -W -f='${Version}' tzdata)" = "2026b-0+deb12u1" \
    && groupadd --gid 10001 xiangrugu \
    && useradd --uid 10001 --gid 10001 --create-home \
        --home-dir /home/xiangrugu --shell /usr/sbin/nologin xiangrugu

COPY datamgmt/requirements.lock /tmp/requirements.lock
RUN python -m pip install --disable-pip-version-check --no-cache-dir \
        --only-binary=:all: --require-hashes --requirement /tmp/requirements.lock \
    && rm /tmp/requirements.lock

COPY datamgmt/pyproject.toml /app/datamgmt/pyproject.toml
COPY datamgmt/config/contract.schema.json /app/datamgmt/config/contract.schema.json
COPY datamgmt/src /app/datamgmt/src
RUN python -m pip install --disable-pip-version-check --no-cache-dir \
        --no-deps --no-build-isolation /app/datamgmt

FROM base AS runtime

USER 10001:10001
ENTRYPOINT ["python", "-m", "xiangrugu_datamgmt"]
CMD ["--help"]

FROM base AS development

COPY datamgmt/requirements-dev.lock /tmp/requirements-dev.lock
RUN python -m pip install --disable-pip-version-check --no-cache-dir \
        --only-binary=:all: --require-hashes --requirement /tmp/requirements-dev.lock \
    && rm /tmp/requirements-dev.lock

FROM development AS dev

USER 10001:10001
CMD ["python", "-m", "xiangrugu_datamgmt.devwatch"]

FROM development AS test

COPY datamgmt/config/roots.yaml /app/datamgmt/config/roots.yaml
COPY docker-compose.yml /app/docker-compose.yml
COPY scripts /app/scripts
COPY datamgmt/tests /app/datamgmt/tests
USER 10001:10001
CMD ["python", "-m", "pytest", "datamgmt/tests", "-q"]

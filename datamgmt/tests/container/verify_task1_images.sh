#!/bin/sh
set -eu

TEST_IMAGE="${TEST_IMAGE:-xiangrugu:test}"
RUNTIME_IMAGE="${RUNTIME_IMAGE:-xiangrugu:runtime}"
DEV_IMAGE="${DEV_IMAGE:-xiangrugu:dev}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

: "${EXPECTED_BUILD_DATE:?EXPECTED_BUILD_DATE is required}"
: "${EXPECTED_SOURCE_STATUS:?EXPECTED_SOURCE_STATUS is required}"
: "${EXPECTED_VCS_REF:?EXPECTED_VCS_REF is required}"
: "${EXPECTED_VERSION:?EXPECTED_VERSION is required}"

check_common_image_contract() {
    image="$1"

    test "$(docker image inspect "${image}" --format '{{.Config.User}}')" = "10001:10001"
    test "$(docker image inspect "${image}" --format '{{index .Config.Labels "org.opencontainers.image.created"}}')" = "${EXPECTED_BUILD_DATE}"
    test "$(docker image inspect "${image}" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}')" = "${EXPECTED_VCS_REF}"
    test "$(docker image inspect "${image}" --format '{{index .Config.Labels "org.opencontainers.image.version"}}')" = "${EXPECTED_VERSION}"
    test "$(docker image inspect "${image}" --format '{{index .Config.Labels "io.xiangrugu.source.status"}}')" = "${EXPECTED_SOURCE_STATUS}"
}

check_common_image_contract "${TEST_IMAGE}"
check_common_image_contract "${RUNTIME_IMAGE}"
check_common_image_contract "${DEV_IMAGE}"

test "$(docker image inspect "${RUNTIME_IMAGE}" --format '{{json .Config.Entrypoint}}')" = '["python","-m","xiangrugu_datamgmt"]'
test "$(docker image inspect "${RUNTIME_IMAGE}" --format '{{json .Config.Cmd}}')" = '["--help"]'
test "$(docker run --rm --entrypoint id "${RUNTIME_IMAGE}" -u)" = "10001"

docker run --rm --entrypoint python "${RUNTIME_IMAGE}" -m pip check
docker run --rm --entrypoint python "${RUNTIME_IMAGE}" -c \
    "import importlib.util; assert importlib.util.find_spec('pytest') is None"
docker run --rm --entrypoint python "${DEV_IMAGE}" -c \
    "import importlib.util; assert importlib.util.find_spec('pytest') is not None"
docker run --rm "${RUNTIME_IMAGE}" --help >/dev/null
docker run --rm "${TEST_IMAGE}" python -m pytest \
    -W error::pytest.PytestCacheWarning \
    datamgmt/tests/unit \
    datamgmt/tests/container/test_image_contract.py \
    datamgmt/tests/container/test_dev_environment.py -q
docker compose --file "${COMPOSE_FILE}" \
    --profile dev --profile runtime --profile test --profile test-db config --quiet

printf '%s\n' "Task 1 image contract passed."

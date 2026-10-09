#!/bin/sh
set -eu

: "${VCS_REF:?Set VCS_REF to the Windows Git HEAD}"
: "${SOURCE_STATUS:?Set SOURCE_STATUS to clean or dirty}"
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
VERSION=0.1.0
for target in dev test runtime; do
    docker build --target "$target" -t "xiangrugu:$target" \
        --build-arg "BUILD_DATE=$BUILD_DATE" \
        --build-arg "VCS_REF=$VCS_REF" \
        --build-arg "SOURCE_STATUS=$SOURCE_STATUS" \
        --build-arg "VERSION=$VERSION" .
done
EXPECTED_BUILD_DATE="$BUILD_DATE" EXPECTED_VCS_REF="$VCS_REF" \
EXPECTED_SOURCE_STATUS="$SOURCE_STATUS" EXPECTED_VERSION="$VERSION" \
    sh datamgmt/tests/container/verify_task1_images.sh

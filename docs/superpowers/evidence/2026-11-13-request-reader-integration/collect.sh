#!/bin/bash
set -euo pipefail
r=/opt/mydocker/xiangrugu/data/var/batch-runner-request-reader-20261113
cd "$r"
mkdir raw
full=(request-reader-red request-reader-green dev-metadata dev-remainder dev-fixtures installed-metadata installed-remainder installed-fixtures)
runtime=(reader-prepare-change reader-request-change reader-prepare-large reader-large-cancel reader-large)
for run in "${full[@]}" "${runtime[@]}"; do
    id=$(cat "$run/container-id.txt")
    [[ "$id" =~ ^[0-9a-f]{64}$ && -z "$(timeout 5 docker ps -a -q --no-trunc --filter id="$id")" ]]
    printf 'CONFIRMED_ABSENT %s\n' "$id" >> raw/absence.txt
done
find "${full[@]}" "${runtime[@]}" -type f \
    \( -name '*.json' -o -name '*.jsonl' -o -name '*.txt' -o -name '*.log' -o -name '*.yaml' -o -name '*.xml' -o -name '*.sha256' \) \
    ! -path '*/disk-scratch/*' ! -path '*/fixture/snapshots/*' ! -path '*/test-memory/*' ! -path '*/scratch/*' ! -path '*/tests/*' \
    | sort > collection-files.txt
while IFS= read -r file; do
    [[ ! -L "$file" && "$(realpath -e -- "$file")" == "$r/$file" ]]
    mkdir -p "raw/$(dirname -- "$file")"
    cp -- "$file" "raw/$file"
done < collection-files.txt
cp -r build raw/build
cp source-green-*-check.txt raw/
{
    date -u
    cat /proc/sys/kernel/random/boot_id
    docker inspect --format '{{.Id}} {{.State.StartedAt}} {{.State.Health.Status}}' pg32 pg32b
    grep '^pswpout ' /proc/vmstat
    docker top xiangrugu-dev -eo pid,ppid,comm
    sleep 3
    docker top xiangrugu-dev -eo pid,ppid,comm
    for run in reader-request-change reader-large-cancel reader-large; do
        [[ -z "$(find "$run/output/disk-scratch" -mindepth 1 -print -quit)" ]]
        printf 'SCRATCH_EMPTY %s\n' "$run"
    done
    docker ps --filter name=xiangrugu-evidence --format '{{.Names}} {{.Status}}'
} > raw/final-state.txt
(cd raw; find . -type f -print0 | sort -z | xargs -0 sha256sum) > raw.sha256
tar --hard-dereference -czf raw.tar.gz -C raw .
sha256sum raw.tar.gz raw.sha256 > collection.sha256

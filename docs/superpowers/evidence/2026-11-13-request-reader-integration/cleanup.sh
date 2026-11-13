#!/bin/bash
set -euo pipefail
r=/opt/mydocker/xiangrugu/data/var/batch-runner-request-reader-20261113
[[ ! -L "$r" && "$(realpath -e -- "$r")" == "$r" ]]
cd "$r"
sha256sum -c collection.sha256
[[ $(wc -l < raw/absence.txt) == 13 ]]
while read -r marker id; do
    [[ "$marker" == CONFIRMED_ABSENT && "$id" =~ ^[0-9a-f]{64}$ ]]
    [[ -z "$(timeout 5 docker ps -a -q --no-trunc --filter id="$id")" ]]
done < raw/absence.txt
targets=()
for run in request-reader-red request-reader-green dev-metadata dev-remainder dev-fixtures installed-metadata installed-remainder installed-fixtures; do
    for kind in tests scratch test-memory; do targets+=("$run/output/$kind"); done
done
for run in reader-prepare-change reader-request-change reader-prepare-large reader-large-cancel reader-large; do
    targets+=("$run/output/scratch" "$run/output/disk-scratch")
done
for run in reader-prepare-change reader-prepare-large; do
    targets+=("$run/output/project")
done
# Validate every exact target before deleting any. No source copies or other rounds.
for relative in "${targets[@]}"; do
    target="$r/$relative"
    [[ ! -L "$target" ]]
    if [[ -e "$target" ]]; then
        [[ -d "$target" && "$(realpath -e -- "$target")" == "$target" ]]
    fi
done
{
    date -u
    printf 'ARCHIVE_VERIFIED_AND_13_CANDIDATES_ABSENT\n'
    for relative in "${targets[@]}"; do
        target="$r/$relative"
        if [[ -d "$target" ]]; then
            rm -rf -- "$target"
            [[ ! -e "$target" && ! -L "$target" ]]
            printf 'REMOVED %s\n' "$relative"
        else
            printf 'ALREADY_ABSENT %s\n' "$relative"
        fi
    done
    cat /proc/sys/kernel/random/boot_id
    docker inspect --format '{{.Id}} {{.State.StartedAt}} {{.State.Health.Status}}' pg32 pg32b
    grep '^pswpout ' /proc/vmstat
    df -h "$r"
} > cleanup.txt
cat cleanup.txt

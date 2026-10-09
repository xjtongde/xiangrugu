#!/bin/bash
# Linux / host 32. Source bytes stay on 32; project logic runs in its own image.
set -euo pipefail
: "${SNAPSHOT_ID:?Set a new, never-used snapshot identifier}"
: "${VCS_REF:?Set the authoritative Windows Git HEAD}"
source_root=/mnt/wd61workmetadata/usedata
project_root=/opt/mydocker/xiangrugu
image_digest=$(docker image inspect xiangrugu:runtime --format '{{.Id}}')

identity() {
    test "$(realpath -e "$source_root")" = "$source_root"
    test ! -L "$source_root"
    test -d "$source_root"
    findmnt -rn -t cifs -o TARGET,SOURCE,FSTYPE |
        awk '$1=="/mnt/wd61workmetadata" && $2=="//192.168.3.61/workmetadata" && $3=="cifs" {n++} END {if(n!=1)exit 1}'
    stat -c '%d %i' "$source_root"
}
initial_identity=$(identity)
read -r source_device source_inode <<< "$initial_identity"

receiver() {
    nice -n 19 docker run --rm -i --network none --read-only \
        --cpus 1 --memory 768m --pids-limit 64 --user 10001:10001 \
        --mount "type=bind,src=$project_root/deploy/datamgmt/config/roots.yaml,dst=/config/roots.yaml,readonly" \
        --mount "type=bind,src=$project_root/data/imports/usedata,dst=/data/imports/usedata" \
        --mount "type=bind,src=$project_root/data/var,dst=/data/var" \
        --entrypoint python "$image_digest" -m xiangrugu_datamgmt.snapshot_transfer \
        --config /config/roots.yaml --snapshot-id "$SNAPSHOT_ID" \
        --source-path "$source_root" --device "$source_device" --inode "$source_inode" \
        --vcs-ref "$VCS_REF" --image-digest "$image_digest" "$1"
}

for phase in prepare copy check; do
    test "$(identity)" = "$initial_identity"
    # Gate each pass; no persistent service or database operation is performed.
    awk '{if ($1>=4) exit 1}' /proc/loadavg
    printf 'Starting snapshot phase: %s\n' "$phase"
    nice -n 19 ionice -c 3 tar --format=ustar --hard-dereference \
        -cf - -C "$source_root" . | receiver "$phase"
    # pipefail must succeed BEFORE the next phase / final certification.
    test "$(identity)" = "$initial_identity"
done
receiver finish </dev/null

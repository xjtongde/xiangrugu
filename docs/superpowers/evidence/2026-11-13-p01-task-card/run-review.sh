#!/bin/bash
# Linux shell on host 32 only. Pure metadata: no real snapshot, NAS or database
# network. Adapted from 2026-11-09-p01-read-review/run-review.sh for the
# verified 2026-11-13 request-reader runtime and the new closed p01 task card.
# Modes:
#   metadata                container: prepare closed review + closed task card
#   product-gate            container: installed task_control must refuse the
#                           closed project_snapshot template without authorization
#   reject-no-authorization host-only: refuse before any materialize/candidate
#                           when authorization.json is absent (expected exit 2)
set -Eeuo pipefail
image=${1:-}
suffix=${2:-}
runtime_root=${3:-}
mode=${4:-}
revision=${5:-}
metadata_suffix=${6:-}
EXPECTED_IMAGE=sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a
EXPECTED_REVISION=8fbc8c97fcf1d818caddf6ab556fa82d986643ed
ROOTS_SHA=6235c356fca754a687a2f02998770c9609b20748ade674d0050d86a0a428e07c
ATTEMPT=real-p01-20261113-a
EVIDENCE_REL=docs/superpowers/evidence/2026-11-13-p01-task-card
[[ "$image" == "$EXPECTED_IMAGE" ]] || { echo 'Require the verified 2026-11-13 runtime image ID' >&2; exit 2; }
[[ "$revision" == "$EXPECTED_REVISION" ]] || { echo 'Invalid revision' >&2; exit 2; }
if [[ ! "$suffix" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]]; then
    echo 'Invalid run identity' >&2; exit 2
fi
if [[ "$runtime_root" != /opt/mydocker/xiangrugu/data/var/batch-runner-p01-task-card-20261113 ||
      "$(realpath -e -- "$runtime_root")" != "$runtime_root" || ! -d "$runtime_root" ]]; then
    echo 'Require existing private runtime root' >&2; exit 2
fi
case "$mode" in
    metadata) (( $# == 5 )) || exit 2 ;;
    product-gate|reject-no-authorization)
        (( $# == 6 )) || exit 2
        [[ "$metadata_suffix" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]] || exit 2
        [[ -d "$runtime_root/$metadata_suffix/output/review" ]] || { echo 'Missing metadata run review output' >&2; exit 2; }
        ;;
    *) exit 2 ;;
esac
source_root=$(realpath -e -- "$(dirname -- "$0")/../../../..")
[[ "$source_root" == "$runtime_root"/source-green* ]] || exit 2
for required in "$EVIDENCE_REL/prepare-closed-review.py" "$EVIDENCE_REL/product-gate-probe.py" \
    "$EVIDENCE_REL/verify.sh" scripts/controller-evidence.sh scripts/controller-heartbeat.sh \
    docs/superpowers/evidence/2026-11-13-request-reader-integration/installed-origin.py \
    metadata/selected-certificate.json metadata/runtime-verification.json metadata/build-inputs.sha256; do
    [[ -f "$source_root/$required" ]] || { echo "Missing staged input: $required" >&2; exit 2; }
done
[[ "$(sha256sum -- "$source_root/metadata/datamgmt/config/roots.yaml" | cut -d' ' -f1)" == "$ROOTS_SHA" ]] || exit 2
image_identity=$(timeout 5 docker image inspect --format '{{.Id}} {{index .Config.Labels "org.opencontainers.image.revision"}} {{.Config.User}} {{index .Config.Labels "io.xiangrugu.source.status"}}' "$image")
read -r actual_id actual_revision actual_user actual_status <<< "$image_identity"
[[ "$image_identity" == "$image $EXPECTED_REVISION 10001:10001 dirty" ]] || { echo 'Image identity mismatch' >&2; exit 2; }
# Resident dev service must be idle; this runner never touches it.
quiet=0
for attempt in $(seq 1 20); do
    count=$(timeout 5 docker top xiangrugu-dev -eo pid,ppid,comm | awk 'NR>1 {n++} END {print n+0}')
    if [[ "$count" == 1 ]]; then quiet=$((quiet+1)); else quiet=0; fi
    [[ "$quiet" -ge 2 ]] && break
    sleep 3
done
[[ "$quiet" -ge 2 ]] || { echo 'Dev service not idle' >&2; exit 1; }
# The SSH controller must actively renew the connection, not just stay open.
IFS= read -r -t 10 controller || { echo 'Missing SSH controller heartbeat' >&2; exit 2; }
controller=${controller#$'\xef\xbb\xbf'}
[[ "$controller" == tick ]] || { echo 'Invalid controller heartbeat' >&2; exit 2; }
name="xiangrugu-evidence-$suffix"
run="$runtime_root/$suffix"
mkdir -- "$run"
chmod 755 "$run"
mkdir -- "$run/control" "$run/output"
chown 10001:10001 "$run/output"
# This lock is shared by every invocation of this synthetic runner on host 32.
exec 9>/opt/mydocker/xiangrugu/data/var/sqlite-synthetic-batch.lock
flock -n 9 || { echo 'Another synthetic batch is active' >&2; exit 2; }
seq=0
owned=false
cancel_requested=false
source "${source_root}/scripts/controller-evidence.sh"
source "${source_root}/scripts/controller-heartbeat.sh"
stop_owned() {
    if "$owned"; then
        [[ "$(timeout 5 docker inspect --format '{{.Id}}' "$name")" == "$id" ]] || return 1
        controller_note stop_requested cleanup
        timeout 15 docker stop --time 10 "$name" >/dev/null 2>&1 || true
        running=$(timeout 5 docker inspect --format '{{.State.Running}}' "$name") || return 1
        if [[ "$running" != false ]]; then
            controller_note kill_requested cleanup
            timeout 5 docker kill "$name" >/dev/null 2>&1 || true
            [[ "$(timeout 5 docker inspect --format '{{.State.Running}}' "$name")" == false ]] || return 1
        fi
    fi
}
finish() {
    original=$?
    trap - EXIT ERR
    if [[ "$original" != 0 ]] && ! "$controller_first_trigger"; then
        controller_note trigger runner_error null "$original"
    fi
    if ! stop_owned; then
        echo 'cancel_unconfirmed; retain container and evidence' >&2
        controller_note runner_exit cleanup null 1
        exit 1
    fi
    if "$owned"; then
        timeout 5 docker logs "$name" > "$run/worker.log" 2>&1 || true
        timeout 5 docker inspect --format '{{json .State}}' "$name" > "$run/container-state.json" || true
        printf '%s\n' "$original" > "$run/runner-exit.txt" || true
        timeout 10 docker rm "$name" > "$run/removal.txt" || { echo 'removal_unconfirmed' >&2; controller_note runner_exit cleanup null 1; exit 1; }
        owned=false
    fi
    controller_note runner_exit runner_exit null "$original"
    exit "$original"
}
trap finish EXIT
trap 'controller_error "$?"' ERR
trap 'controller_signal TERM' TERM
trap 'controller_signal INT' INT
trap 'controller_signal HUP' HUP
printf '%s\n' "$image_identity" > "$run/image-identity.txt"
service_state() {
    timeout 5 docker inspect --format '{{.Id}} {{.State.StartedAt}} {{.State.Status}} {{.State.Health.Status}}' pg32 pg32b
}
baseline=$(service_state)
printf '%s\n' "$baseline" > "$run/services-before.txt"
cat /proc/sys/kernel/random/boot_id > "$run/boot-id.txt"
sample() {
    seq=$((seq+1))
    services=$(service_state)
    healthy=false
    if [[ "$services" == "$baseline" && "$(printf '%s\n' "$services" | grep -c ' running healthy$')" == 2 ]]; then
        healthy=true
    fi
    {
        date +%s
        printf '%s\n' "$seq"
        grep '^MemAvailable:' /proc/meminfo
        cat /proc/loadavg
        grep '^some ' /proc/pressure/io
        grep '^some ' /proc/pressure/memory
        grep '^pswpout ' /proc/vmstat
        df -B1 --output=avail "$runtime_root" | tail -n 1 | tr -d ' '
        printf '%s\n' "$healthy"
    } > "$run/control/.lease-next"
    mv -T -- "$run/control/.lease-next" "$run/control/lease"
    cat "$run/control/lease" >> "$run/host-samples.txt"
}

if [[ "$mode" == reject-no-authorization ]]; then
    # Host-side authorization gate. No container is created in this mode. The
    # future authorized runner must verify authorization.json against the card
    # SHA-256 before calling materialize_project_partition_request; this closed
    # package contains no materialize path at all.
    card="$runtime_root/$metadata_suffix/output/task-card.closed.json"
    [[ -f "$card" && ! -L "$card" && "$(realpath -e -- "$card")" == "$card" ]] || { echo 'Missing closed task card' >&2; exit 2; }
    card_sha=$(sha256sum -- "$card" | cut -d' ' -f1)
    grep -q '"status":"CLOSED_REAL_PARTITION_TASK_CARD_NOT_EXECUTABLE"' "$card" || exit 2
    grep -q "\"attempt_id\":\"$ATTEMPT\"" "$card" || exit 2
    for flag in source_read_authorized postgresql_authorized contract_frozen ready_for_import; do
        grep -q "\"$flag\":false" "$card" || exit 2
    done
    grep -q '"expected_count":null' "$card" || exit 2
    grep -q '"expected_sha256":null' "$card" || exit 2
    authorization_present=false
    [[ ! -e "$runtime_root/authorization" ]] || authorization_present=true
    executable_files=$(find "$runtime_root" -type f \( -name request.json -o -name approval.json -o -name scope.json -o -name budget.json \) | wc -l)
    materialize_dir_found=false
    [[ ! -e "$runtime_root/executions" ]] || materialize_dir_found=true
    real_candidate_container_found=false
    if [[ -n "$(timeout 5 docker ps -a --filter "label=io.xiangrugu.synthetic-run=$ATTEMPT" --format '{{.ID}}')" ]]; then
        real_candidate_container_found=true
    fi
    if [[ -n "$(timeout 5 docker ps -a --format '{{.Names}}' | grep -x "xiangrugu-evidence-$ATTEMPT" || true)" ]]; then
        real_candidate_container_found=true
    fi
    refused=true
    if [[ "$authorization_present" != false || "$executable_files" != 0 ||
          "$materialize_dir_found" != false || "$real_candidate_container_found" != false ]]; then
        refused=false
    fi
    printf '{"version":1,"status":"REAL_EXECUTION_REFUSED_NO_AUTHORIZATION","exit_code":2,"attempt_id":"%s","task_card_sha256":"%s","authorization_present":%s,"executable_request_or_approval_files":%s,"materialize_dir_found":%s,"real_candidate_container_found":%s,"refused_before_materialize":%s,"source_bytes_read":false,"postgresql_connected":false,"ready_for_import":false}\n' \
        "$ATTEMPT" "$card_sha" "$authorization_present" "$executable_files" "$materialize_dir_found" "$real_candidate_container_found" "$refused" \
        > "$run/rejection-receipt.json"
    service_state > "$run/services-after.txt"
    cmp -s "$run/services-before.txt" "$run/services-after.txt" || { echo 'Final service state differs' >&2; exit 1; }
    [[ "$refused" == true ]] || { echo 'Closed-state invariants violated; see receipt' >&2; exit 1; }
    printf '2\n' > "$run/exit-code.txt"
    # The intentional refusal is the first trigger; finish only records runner_exit.
    controller_first_trigger=true
    exit 2
fi

controller_phase=collector
sample
controller_phase=runner
seconds=300
host_seconds=$((seconds+30))
printf '%s\n' "$seconds" "$host_seconds" > "$run/deadlines.txt"
input_mount=(--mount "type=bind,src=$source_root/docs/superpowers/evidence/2026-11-13-request-reader-integration/installed-origin.py,dst=/installed-origin.py,readonly")
if [[ "$mode" == metadata ]]; then
    input_mount+=(--mount "type=bind,src=$source_root/metadata,dst=/metadata,readonly"
        --mount "type=bind,src=$source_root/$EVIDENCE_REL/prepare-closed-review.py,dst=/closed-review.py,readonly")
    worker=(python /installed-origin.py /closed-review.py "$image" "$revision")
else
    review_dir="$runtime_root/$metadata_suffix/output/review"
    [[ "$(realpath -e -- "$review_dir")" == "$review_dir" ]] || exit 2
    request_template="$review_dir/request.review.json"
    [[ -f "$request_template" && ! -L "$request_template" ]] || exit 2
    template_pin=$(sha256sum -- "$request_template" | cut -d' ' -f1)
    printf '%s\n' "$template_pin" > "$run/request-template.sha256"
    grep -q '"status":"DRAFT_PROJECT_PARTITION_REQUEST_REVIEW"' "$request_template" || exit 2
    input_mount+=(--mount "type=bind,src=$review_dir,dst=/review-input,readonly"
        --mount "type=bind,src=$source_root/$EVIDENCE_REL/product-gate-probe.py,dst=/product-gate-probe.py,readonly")
    worker=(python /installed-origin.py /product-gate-probe.py "$ROOTS_SHA" "$image" "$revision")
fi
id=$(docker create --name "$name" --label "io.xiangrugu.synthetic-run=$suffix" \
    --cpus 0.5 --memory 768m --memory-swap 768m --pids-limit 128 \
    --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
    --tmpfs /tmp:rw,nosuid,nodev,size=33554432,uid=10001,gid=10001,mode=1777 \
    --tmpfs /data/var/run/scratch:rw,nosuid,nodev,size=67108864,uid=10001,gid=10001,mode=700 \
    --mount "type=bind,src=$run/control,dst=/control,readonly" \
    --mount "type=bind,src=$run/output,dst=/data/var/run" \
    "${input_mount[@]}" --workdir /app \
    --entrypoint python "$image" -m xiangrugu_datamgmt.candidate_supervisor \
    --lease /control/lease --evidence /data/var/run/monitor.json --seconds "$seconds" \
    -- "${worker[@]}")
owned=true
printf '%s\n' "$id" > "$run/container-id.txt"
docker inspect --format '{{json .HostConfig}}' "$name" > "$run/host-config.json"
docker start "$name" >/dev/null
started=$SECONDS
last_controller=$SECONDS
next_sample=$((SECONDS+10))
final_sample_sent=false
while [[ "$(timeout 5 docker inspect --format '{{.State.Running}}' "$name")" == true ]]; do
    if controller_read_heartbeat; then
        last_controller=$SECONDS
    else
        read_code=$?
        if (( read_code == 2 )); then
            controller_note trigger invalid_heartbeat
            stop_owned
            break
        fi
        if (( read_code == 3 || SECONDS-last_controller >= 15 )); then
            if (( read_code == 3 )); then
                controller_note trigger controller_eof
            else
                controller_note trigger controller_idle
            fi
            printf '%s\n' controller_lost > "$run/controller-stop.txt"
            stop_owned
            break
        fi
    fi
    if "$cancel_requested"; then
        controller_note trigger artificial_cancel
        stop_owned
        break
    fi
    if (( SECONDS-started >= host_seconds )); then
        controller_note trigger host_deadline
        printf '%s\n' host_deadline > "$run/controller-stop.txt"
        stop_owned
        break
    fi
    if [[ -f "$run/output/final-sample-request.json" ]] && ! "$final_sample_sent"; then
        controller_phase=collector
        sample
        controller_phase=runner
        final_sample_sent=true
        next_sample=$((SECONDS+10))
    elif (( SECONDS >= next_sample )); then
        controller_phase=collector
        sample
        controller_phase=runner
        next_sample=$((SECONDS+10))
    fi
    sleep 1
done
docker logs "$name" > "$run/worker.log" 2>&1
docker inspect --format '{{json .State}}' "$name" > "$run/container-state.json"
service_state > "$run/services-after.txt"
cmp -s "$run/services-before.txt" "$run/services-after.txt" || { echo 'Final service state differs' >&2; exit 1; }
code=$(docker inspect --format '{{.State.ExitCode}}' "$name")
printf '%s\n' "$code" > "$run/exit-code.txt"
[[ "$(docker inspect --format '{{.State.Running}}' "$name")" == false ]]
docker rm "$name" > "$run/removal.txt"
owned=false
[[ "$code" == 0 && "$(grep -o '"OOMKilled":true' "$run/container-state.json" || true)" == '' ]] || exit 1
if [[ "$mode" == metadata ]]; then
    out="$run/output"
    grep -q '"status":"DRAFT_PROJECT_PARTITION_REVIEW_NOT_EXECUTABLE"' "$out/review/review.json" || exit 1
    grep -q '"missing":\[\]' "$out/review/review.json" || exit 1
    [[ -f "$out/task-card.closed.json" && -f "$out/card-receipt.json" && -f "$out/installed-origin.json" ]] || exit 1
    grep -q '"status":"CLOSED_TASK_CARD_GENERATED"' "$out/card-receipt.json" || exit 1
    [[ -z "$(find "$out" -type f \( -name request.json -o -name approval.json -o -name scope.json -o -name budget.json -o -name batch.json \))" ]] || exit 1
else
    out="$run/output"
    [[ -f "$out/product-gate-receipt.json" && -f "$out/installed-origin.json" ]] || exit 1
    grep -q '"refused":true' "$out/product-gate-receipt.json" || exit 1
    grep -q '"reason":"real_execution_closed"' "$out/product-gate-receipt.json" || exit 1
    grep -q '"batch_created":false' "$out/product-gate-receipt.json" || exit 1
    [[ ! -e "$out/batch.json" ]] || exit 1
fi

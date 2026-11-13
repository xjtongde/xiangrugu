#!/bin/bash
# Owned artificial protocol only; no NAS, real snapshot or database network.
set -Eeuo pipefail
image=${1:-}; suffix=${2:-}; runtime_root=${3:-}; mode=${4:-}; revision=${5:-}
fixture_suffix=${6:-}; request_pin=${7:-}; approval_pin=${8:-}; roots_pin=${9:-}
source_root=$(realpath -e -- "$(dirname -- "$0")/../../../..")
[[ "$runtime_root" == /opt/mydocker/xiangrugu/data/var/batch-runner-request-reader-20261113 && "$source_root" == "$runtime_root"/source-green* ]] || exit 2
[[ "$revision" == 8fbc8c97fcf1d818caddf6ab556fa82d986643ed ]] || exit 2
[[ "$image" == "$(cat "$runtime_root/build/runtime-image.id")" ]] || exit 2
request_name=executions/large-p01/request.json
approval_name=executions/large-p01/approval.json
roots_name=metadata-repository/datamgmt/config/roots.yaml
scenario=
input_mount=()
if [[ "$mode" == readonly-prepare ]]; then
    [[ $# == 5 ]] || exit 2
    case "$suffix" in
        reader-prepare-small-v2|reader-prepare-baseline|reader-prepare-change) scenario=coverage ;;
        reader-prepare-large|reader-prepare-baseline-large) scenario=reader-multi-merge ;;
        *) exit 2 ;;
    esac
elif [[ "$mode" == readonly-controlled ]]; then
    [[ $# == 9 && "$request_pin" =~ ^[0-9a-f]{64}$ && "$approval_pin" =~ ^[0-9a-f]{64}$ && "$roots_pin" =~ ^[0-9a-f]{64}$ ]] || exit 2
    case "$suffix:$fixture_suffix" in
        reader-small:small|reader-small-profile:small) prepared=reader-prepare-small-v2 ;;
        reader-baseline:baseline) prepared=reader-prepare-baseline ;;
        reader-baseline-large:baseline-large) prepared=reader-prepare-baseline-large ;;
        reader-large:large|reader-large-cancel:large) prepared=reader-prepare-large ;;
        reader-request-change:change) prepared=reader-prepare-change ;;
        *) exit 2 ;;
    esac
    fixture="$runtime_root/$prepared/output/project"
    [[ "$(realpath -e -- "$fixture")" == "$fixture" && "$(stat -c %u -- "$fixture")" == 10001 && -f "$runtime_root/$prepared/removal.txt" ]] || exit 2
    files=("$request_name" "$approval_name" "$roots_name")
    pins=("$request_pin" "$approval_pin" "$roots_pin")
    for index in 0 1 2; do
        file="$fixture/${files[$index]}"
        [[ ! -L "$file" && "$(realpath -e -- "$file")" == "$file" && "$(sha256sum -- "$file" | cut -d' ' -f1)" == "${pins[$index]}" ]] || exit 2
    done
    input_mount=(--mount "type=bind,src=$fixture,dst=/data/var/run/project,readonly")
else exit 2; fi
for required in docs/superpowers/evidence/2026-10-24-real-partition-control/cancel-probe.py docs/superpowers/evidence/2026-10-24-real-partition-control/prepare-retry.py docs/superpowers/evidence/2026-11-13-request-reader-integration/runtime-profile.py docs/superpowers/evidence/2026-11-13-request-reader-integration/installed-origin.py docs/superpowers/evidence/2026-11-08-metadata-reader-integration/assert-negative.sh; do
    [[ -f "$source_root/$required" ]] || exit 2
done
image_identity=$(timeout 5 docker image inspect --format '{{.Id}} {{index .Config.Labels "org.opencontainers.image.revision"}} {{.Config.User}} {{index .Config.Labels "io.xiangrugu.source.status"}}' "$image")
read -r actual_id actual_revision actual_user actual_status <<< "$image_identity"
[[ "$image_identity" == "$image $revision 10001:10001 dirty" ]] || exit 2
quiet=0
for attempt in $(seq 1 20); do
    count=$(timeout 5 docker top xiangrugu-dev -eo pid,ppid,comm | awk 'NR>1 {n++} END {print n+0}')
    if [[ "$count" == 1 ]]; then quiet=$((quiet+1)); else quiet=0; fi
    [[ "$quiet" -ge 2 ]] && break
    sleep 3
done
[[ "$quiet" -ge 2 ]] || exit 1
# The SSH controller must actively renew the connection, not just stay open.
IFS= read -r -t 10 controller || { echo 'Missing SSH controller heartbeat' >&2; exit 2; }
# Windows PowerShell 5's redirected StreamWriter may prepend a UTF-8 BOM.
controller=${controller#$'\xef\xbb\xbf'}
[[ "$controller" == tick ]] || { echo 'Invalid controller heartbeat' >&2; exit 2; }
name="xiangrugu-evidence-$suffix"
run="$runtime_root/$suffix"
mkdir -- "$run"
chmod 755 "$run"
mkdir -- "$run/control" "$run/output"
chown 10001:10001 "$run/output"
mkdir "$run/output/disk-scratch"
chown 10001:10001 "$run/output/disk-scratch"
# This lock is shared by every invocation of this synthetic runner on host 32.
exec 9>/opt/mydocker/xiangrugu/data/var/sqlite-synthetic-batch.lock
flock -n 9 || { echo 'Another synthetic batch is active' >&2; exit 2; }
seq=0
owned=false
cancel_requested=false
source ${source_root}/scripts/controller-evidence.sh
source ${source_root}/scripts/controller-heartbeat.sh
source "$source_root/docs/superpowers/evidence/2026-11-08-metadata-reader-integration/assert-negative.sh"
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
        # Preserve whatever incomplete diagnostics are readable, then remove
        # only our exact, confirmed stopped container; never prune by prefix.
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
if [[ "$mode" == readonly-controlled ]]; then
    printf '%s\n' "$image_identity" > "$run/image-identity.txt"
    printf '%s\n' "$request_pin" "$approval_pin" "$roots_pin" > "$run/controller-pins.txt"
fi
service_state() {
    timeout 5 docker inspect --format '{{.Id}} {{.State.StartedAt}} {{.State.Status}} {{.State.Health.Status}}' pg32 pg32b
}
baseline=$(service_state)
printf '%s\n' "$baseline" > "$run/services-before.txt"
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
controller_phase=collector
sample
controller_phase=runner
# Baseline resource rejection happens inside supervisor before it starts worker.
seconds=300
final=()
diagnostic=()
case "$mode" in
    readonly-prepare)
        worker=(python /fixture-tools/prepare_project_protocol.py --image "$image" --revision "$revision" --scenario "$scenario")
        if [[ "$scenario" == retry || "$scenario" == cancel ]]; then worker=(python /prepare-retry.py --image "$image" --revision "$revision" --attempt-choice "$scenario"); fi ;;
    readonly-controlled)
        seconds=1800
        final=(--authorized-source-mode project_snapshot --request-sha256 "$request_pin" --final /data/var/run/project/results/batch.json)
        diagnostic=(--worker-failure /data/var/run/worker-failure.json --worker-request-sha256 "$request_pin" --controller-request-file "/data/var/run/project/$request_name" --controller-request-sha256 "$request_pin")
        worker=(python -m xiangrugu_datamgmt.task_control --request "/data/var/run/project/$request_name"
            --request-sha256 "$request_pin" --approval-sha256 "$approval_pin" --roots-sha256 "$roots_pin"
            --image-id "$actual_id" --git-revision "$actual_revision" --image-user "$actual_user"
            --source-status "$actual_status" --lifecycle-seconds 1800 --authorized-source-mode project_snapshot
            --failure-evidence /data/var/run/worker-failure.json) ;;
esac
host_seconds=$((seconds+30))
printf '%s\n' "$seconds" "$host_seconds" > "$run/deadlines.txt"
if [[ "$suffix" == reader-small-profile || "$suffix" == reader-large ]]; then worker=(python /runtime-profile.py "${worker[@]:3}"); fi
if [[ "$suffix" == reader-large-cancel || "$suffix" == reader-request-change ]]; then worker=(python /cancel-probe.py "${worker[@]:3}"); fi
worker=(python /installed-origin.py "${worker[@]:1}")
results_mount=()
if [[ "$mode" == readonly-controlled ]]; then results_mount=(--mount "type=bind,src=$run/output,dst=/data/var/run/project/results"); fi
id=$(docker create --name "$name" --label io.xiangrugu.synthetic-run="$suffix" \
    --cpus 0.5 --memory 768m --memory-swap 768m --pids-limit 128 \
    --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
    --tmpfs /tmp:rw,nosuid,nodev,size=33554432,uid=10001,gid=10001,mode=1777 \
    --tmpfs /data/var/run/scratch:rw,nosuid,nodev,size=67108864,uid=10001,gid=10001,mode=700 \
    --mount "type=bind,src=$run/control,dst=/control,readonly" \
    --mount "type=bind,src=$run/output,dst=/data/var/run" \
    "${input_mount[@]}" "${results_mount[@]}" --mount type=bind,src=${source_root}/docs/superpowers/evidence/2026-11-13-request-reader-integration/fixture-tools,dst=/fixture-tools,readonly --mount type=bind,src=${source_root}/docs/superpowers/evidence/2026-10-24-real-partition-control/cancel-probe.py,dst=/cancel-probe.py,readonly \
    --mount type=bind,src=${source_root}/docs/superpowers/evidence/2026-10-24-real-partition-control/prepare-retry.py,dst=/prepare-retry.py,readonly \
    --mount type=bind,src=${source_root}/docs/superpowers/evidence/2026-11-13-request-reader-integration/installed-origin.py,dst=/installed-origin.py,readonly \
    --mount "type=bind,src=$source_root/docs/superpowers/evidence/2026-11-13-request-reader-integration/runtime-profile.py,dst=/runtime-profile.py,readonly" \
    --entrypoint python "$image" -m xiangrugu_datamgmt.candidate_supervisor \
    --lease /control/lease --evidence /data/var/run/monitor.json --seconds "$seconds" \
    "${final[@]}" "${diagnostic[@]}" -- "${worker[@]}")
owned=true
printf '%s\n' "$id" > "$run/container-id.txt"
docker inspect --format '{{json .HostConfig}}' "$name" > "$run/host-config.json"
docker start "$name" >/dev/null
started=$SECONDS
last_controller=$SECONDS
next_sample=$((SECONDS+10))
final_sample_sent=false
request_changed=false
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
        # Timeout is allowed within the lease; EOF proves SSH/controller loss.
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
    if [[ "$suffix" == reader-request-change && -f "$run/output/read-frame-marker.json" ]] && ! "$request_changed"; then
        cp -- "$fixture/$request_name" "$run/request-before-change.json"
        printf ' ' >> "$fixture/$request_name"
        sha256sum -- "$fixture/$request_name" > "$run/request-after-change.sha256"
        printf 'OWNED_REQUEST_CHANGED_AFTER_FIRST_FRAME\n' > "$run/request-change.txt"
        request_changed=true
    fi
    if "$cancel_requested" || [[ "$suffix" == reader-large-cancel && -f "$run/output/read-frame-marker.json" ]]; then
        if ! "$cancel_requested"; then controller_note trigger artificial_cancel; fi
        stop_owned
        break
    fi
    if [[ "$mode" == collector-failure && $((SECONDS-started)) -ge 3 ]]; then
        controller_phase=collector
        echo 'Artificial collector failure' >&2
        false
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
    elif (( SECONDS >= next_sample )) && [[ "$mode" != lease-loss ]]; then
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
# Only this owned, confirmed stopped candidate is removed. Keep all run evidence.
[[ "$(docker inspect --format '{{.State.Running}}' "$name")" == false ]]
docker rm "$name" > "$run/removal.txt"
owned=false
if [[ "$suffix" == reader-large-cancel || "$suffix" == reader-request-change ]]; then
    kind=cancel
    [[ "$suffix" != reader-request-change ]] || kind=change
    assert_negative_case "$run" "$kind" "$code" "$request_changed" "$request_pin"
else
    [[ "$code" == 0 && "$(grep -o '"OOMKilled":true' "$run/container-state.json" || true)" == '' ]]
fi

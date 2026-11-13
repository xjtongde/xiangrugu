#!/bin/bash
# Linux shell on host 32 only. No real data volumes or database network.
set -Eeuo pipefail
image=${1:-}
suffix=${2:-}
runtime_root=${3:-}
mode=${4:-}
revision=${5:-}
flavor=${6:-development}
[[ "$flavor" == development || "$flavor" == installed ]] || exit 2
fixture_suffix=
request_pin=${7:-}
approval_pin=${8:-}
roots_pin=${9:-}
if [[ ! "$image" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo 'Require immutable candidate image ID' >&2
    exit 2
fi
if [[ ! "$suffix" =~ ^[a-z0-9][a-z0-9-]{0,40}$ || ! "$revision" =~ ^[0-9a-f]{40}$ ]]; then
    echo 'Invalid run identity' >&2
    exit 2
fi
if [[ "$runtime_root" != /opt/mydocker/xiangrugu/data/var/batch-runner-* ||
      "$(realpath -e -- "$runtime_root")" != "$runtime_root" || ! -d "$runtime_root" ]]; then
    echo 'Require existing private runtime root' >&2
    exit 2
fi
[[ "$mode" == metadata && "$flavor" == installed ]] || exit 2
(( $# <= 6 )) || exit 2
source_root=$(realpath -e -- "$(dirname -- "$0")/../../../..")
[[ "$source_root" == "$runtime_root"/source-* ]] || exit 2
input_mount=(--mount "type=bind,src=$source_root/docs/superpowers/evidence/2026-11-08-metadata-reader-integration/installed-origin.py,dst=/installed-origin.py,readonly")
input_mount+=(--mount "type=bind,src=$source_root/metadata,dst=/metadata,readonly" --mount "type=bind,src=$source_root/docs/superpowers/evidence/2026-11-09-p01-read-review/prepare-closed-review.py,dst=/closed-review.py,readonly")
if [[ "$mode" == offline-* ]]; then
    [[ "$flavor" == installed && -d "$runtime_root/offline-input/project" && -d "$runtime_root/offline-input/receipts" ]] || exit 2
    input_mount+=(--mount "type=bind,src=$runtime_root/offline-input/project,dst=/data/var/run/project,readonly" --mount "type=bind,src=$runtime_root/offline-input/receipts,dst=/data/var/run/receipts,readonly" --mount "type=bind,src=$source_root/docs/superpowers/evidence/2026-10-24-real-partition-control/offline-probe.py,dst=/offline-probe.py,readonly")
fi
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
# This lock is shared by every invocation of this synthetic runner on host 32.
exec 9>/opt/mydocker/xiangrugu/data/var/sqlite-synthetic-batch.lock
flock -n 9 || { echo 'Another synthetic batch is active' >&2; exit 2; }
seq=0
owned=false
cancel_requested=false
source ${source_root}/scripts/controller-evidence.sh
source ${source_root}/scripts/controller-heartbeat.sh
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
 red) worker=(python -m pytest datamgmt/tests/unit/test_project_partition_coverage.py::test_rehashed_application_resource_receipt_rejected datamgmt/tests/unit/test_project_partition_coverage.py::test_host_swap_is_run_relative -q -p no:cacheprovider -W error --basetemp=/data/var/run/test-memory/tests --junitxml=/data/var/run/full.xml) ;;
 metadata) worker=(python /closed-review.py "$image" "$revision") ;;
 fixture-coverage|fixture-fit|fixture-over)
    case "$mode" in fixture-coverage) scenario=coverage ;; fixture-fit) scenario=wide-fit ;; fixture-over) scenario=wide-over ;; esac
    worker=(python -m pytest "datamgmt/tests/unit/test_project_protocol_fixture.py::test_project_protocol_fixed_owned_data[$scenario]" -q -p no:cacheprovider -W error --basetemp=/data/var/run/tests --junitxml=/data/var/run/full.xml) ;;
 fixture-negative) worker=(python -m pytest datamgmt/tests/unit/test_project_protocol_fixture.py -k 'not project_protocol_fixed_owned_data' -q -p no:cacheprovider -W error --basetemp=/data/var/run/tests --junitxml=/data/var/run/full.xml) ;;
 remainder) worker=(python -m pytest datamgmt/tests --ignore=datamgmt/tests/unit/test_project_partition.py --ignore=datamgmt/tests/unit/test_project_partition_execution.py --ignore=datamgmt/tests/unit/test_task_partition.py --ignore=datamgmt/tests/unit/test_project_task_control.py --ignore=datamgmt/tests/unit/test_readonly_batch.py --ignore=datamgmt/tests/unit/test_candidate_supervisor.py --ignore=datamgmt/tests/unit/test_artificial_request_guard.py --ignore=datamgmt/tests/unit/test_project_partition_coverage.py --ignore=datamgmt/tests/unit/test_partition_coverage.py --ignore=datamgmt/tests/unit/test_project_protocol_fixture.py -q -p no:cacheprovider -W error --basetemp=/data/var/run/tests --junitxml=/data/var/run/full.xml) ;;
 offline-nine|offline-ten|offline-duplicate|offline-conflict) worker=(python /offline-probe.py --scenario "${mode#offline-}" --with-retry) ;;
esac
if [[ "$flavor" == installed ]]; then worker=(python /installed-origin.py "${worker[@]:1}"); fi
host_seconds=$((seconds+30))
printf '%s\n' "$seconds" "$host_seconds" > "$run/deadlines.txt"
workspace_mount=(--mount type=bind,src=$source_root,dst=/workspace,readonly --workdir /workspace --env PYTHONPATH=/workspace/datamgmt/src)
if [[ "$flavor" == installed ]]; then workspace_mount=(--workdir /app); fi
test_tmpfs=()
if [[ "$mode" == red || "$mode" == metadata ]]; then test_tmpfs=(--tmpfs /data/var/run/test-memory:rw,nosuid,nodev,size=268435456,uid=10001,gid=10001,mode=700); fi
id=$(docker create --name "$name" --label io.xiangrugu.synthetic-run="$suffix" \
    --cpus 0.5 --memory 768m --memory-swap 768m --pids-limit 128 \
    --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
    "${test_tmpfs[@]}" \
    --tmpfs /tmp:rw,nosuid,nodev,size=33554432,uid=10001,gid=10001,mode=1777 \
    --tmpfs /data/var/run/scratch:rw,nosuid,nodev,size=67108864,uid=10001,gid=10001,mode=700 \
    --mount "type=bind,src=$run/control,dst=/control,readonly" \
    --mount "type=bind,src=$run/output,dst=/data/var/run" \
    "${input_mount[@]}" "${workspace_mount[@]}" \
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
    if "$cancel_requested" || [[ "$mode" == cancel && $((SECONDS-started)) -ge 3 ]]; then
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
if [[ "$mode" == lease-loss || "$mode" == timeout || "$mode" == cancel || "$mode" == disconnect || "$mode" == readonly-writable ]]; then
    [[ "$code" != 0 && ! -e "$run/output/batch.json" ]]
else
    [[ "$code" == 0 && "$(grep -o '"OOMKilled":true' "$run/container-state.json" || true)" == '' ]]
fi

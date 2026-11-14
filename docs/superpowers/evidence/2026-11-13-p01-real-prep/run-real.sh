#!/bin/bash
# Linux shell on host 32 only. Real-execution delivery runner for attempt
# real-p01-20261113-a, bound to accepted task card
# 41bd0ecfb8b9cf6081909f60e27780c40fd5d7bf3019847a77905a4f61fc0b69.
# Protocol adapted from the verified 2026-11-13 p01-task-card run-review.sh
# (same heartbeat, serial lock, resource and reclaim gates), plus:
#   - one-shot attempt registry: O_EXCL registration under the fixed attempt id
#     BEFORE any Stage B container is created; a second start is refused even
#     with a different suffix or Stage A directory;
#   - pinned metadata-only reproduction for Stage A (receipts never copied);
#   - Stage B mounts inputs at their request-bound paths, snapshot dir alone;
#   - supervisor --final = batch publication path (its own); final-sample
#     handshake stays a monitor sibling; worker/supervisor failure unified.
# Modes:
#   refuse-no-authorization <suffix>
#         host-only gate test WITHOUT authorization (expected exit 2)
#   materialize             <suffix>
#         Stage A: gated request assembly; metadata-only, NO snapshot mount
#   real-readonly           <suffix> <mat-suffix> <request-pin> <approval-pin> <roots-pin>
#         Stage B: THE one real candidate; 1800s candidate / 1830s host deadline
# Pins are external operator inputs (reviewed against the Stage A
# controller-pins.txt between stages), never learned from the request here.
set -Eeuo pipefail
image=${1:-}
suffix=${2:-}
runtime_root=${3:-}
mode=${4:-}
revision=${5:-}
mat_suffix=${6:-}
request_pin=${7:-}
approval_pin=${8:-}
roots_pin_arg=${9:-}
EXPECTED_IMAGE=sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a
EXPECTED_REVISION=8fbc8c97fcf1d818caddf6ab556fa82d986643ed
CARD_SHA=41bd0ecfb8b9cf6081909f60e27780c40fd5d7bf3019847a77905a4f61fc0b69
REVIEW_SHA=a7c2c5bdb69a17e8c6038065f16eff378b81f443bdc486a8af1a2b014630c93d
ROOTS_SHA=6235c356fca754a687a2f02998770c9609b20748ade674d0050d86a0a428e07c
ATTEMPT=real-p01-20261113-a
SNAPSHOT_ID=2026-10-07-bootstrap
SNAPSHOT_HOST_ROOT=/opt/mydocker/xiangrugu/data/imports/usedata
EVIDENCE_REL=docs/superpowers/evidence/2026-11-13-p01-real-prep
[[ "$image" == "$EXPECTED_IMAGE" ]] || { echo 'Require the verified 2026-11-13 runtime image ID' >&2; exit 2; }
[[ "$revision" == "$EXPECTED_REVISION" ]] || { echo 'Invalid revision' >&2; exit 2; }
if [[ ! "$suffix" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]]; then
    echo 'Invalid run identity' >&2; exit 2
fi
if [[ "$runtime_root" != /opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a ||
      "$(realpath -e -- "$runtime_root")" != "$runtime_root" || ! -d "$runtime_root" ]]; then
    echo 'Require existing private runtime root' >&2; exit 2
fi
case "$mode" in
    refuse-no-authorization) (( $# == 5 )) || exit 2 ;;
    materialize) (( $# == 5 )) || exit 2 ;;
    real-readonly)
        (( $# == 9 )) || exit 2
        [[ "$mat_suffix" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]] || exit 2
        [[ "$request_pin" =~ ^[0-9a-f]{64}$ && "$approval_pin" =~ ^[0-9a-f]{64}$ ]] || exit 2
        [[ "$roots_pin_arg" == "$ROOTS_SHA" ]] || { echo 'Roots pin mismatch' >&2; exit 2; }
        [[ -f "$runtime_root/$mat_suffix/output/durable/materialization/request.json" &&
           ! -L "$runtime_root/$mat_suffix/output/durable/materialization/request.json" ]] || {
            echo 'Missing Stage A materialization' >&2; exit 2; }
        ;;
    *) exit 2 ;;
esac
source_root=$(realpath -e -- "$(dirname -- "$0")/../../../..")
[[ "$source_root" == "$runtime_root"/source-green* ]] || exit 2
for required in "$EVIDENCE_REL/materialize-real.py" "$EVIDENCE_REL/verify-real.sh" \
    scripts/controller-evidence.sh scripts/controller-heartbeat.sh \
    docs/superpowers/evidence/2026-11-13-request-reader-integration/installed-origin.py \
    metadata/datamgmt/config/roots.yaml returned-output/review/review.json \
    returned-output/preparation/preparation.json task-card.closed.json; do
    [[ -f "$source_root/$required" && ! -L "$source_root/$required" ]] || {
        echo "Missing staged input: $required" >&2; exit 2; }
done
[[ "$(sha256sum -- "$source_root/task-card.closed.json" | cut -d' ' -f1)" == "$CARD_SHA" ]] || exit 2
[[ "$(sha256sum -- "$source_root/returned-output/review/review.json" | cut -d' ' -f1)" == "$REVIEW_SHA" ]] || exit 2
[[ "$(sha256sum -- "$source_root/metadata/datamgmt/config/roots.yaml" | cut -d' ' -f1)" == "$ROOTS_SHA" ]] || exit 2
image_identity=$(timeout 5 docker image inspect --format '{{.Id}} {{index .Config.Labels "org.opencontainers.image.revision"}} {{.Config.User}} {{index .Config.Labels "io.xiangrugu.source.status"}}' "$image")
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
# Shared serial execution lock across all controlled runs on host 32. This
# guarantees serialization only; the attempt registry below guarantees ONCE.
exec 9>/opt/mydocker/xiangrugu/data/var/sqlite-synthetic-batch.lock
flock -n 9 || { echo 'Another controlled batch is active' >&2; exit 2; }
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

if [[ "$mode" == refuse-no-authorization ]]; then
    # Host-side gate test. No container, no materialize call, no writes beyond
    # this run dir. With authorization absent, executing modes must refuse.
    card_sha=$(sha256sum -- "$source_root/task-card.closed.json" | cut -d' ' -f1)
    [[ "$card_sha" == "$CARD_SHA" ]] || exit 2
    authorization_present=false
    [[ ! -e "$runtime_root/authorization.json" ]] || authorization_present=true
    executable_files=$(find "$runtime_root" -type f \( -name request.json -o -name approval.json -o -name scope.json -o -name budget.json \) | wc -l)
    materialize_dir_found=false
    [[ ! -e "$runtime_root/executions" ]] || materialize_dir_found=true
    staged_materialization=$(find "$runtime_root" -type d -name materialization | wc -l)
    registered_attempt=false
    [[ ! -e "$runtime_root/attempt-registration-$ATTEMPT.json" ]] || registered_attempt=true
    real_candidate_container_found=false
    if [[ -n "$(timeout 5 docker ps -a --filter "label=io.xiangrugu.synthetic-run=$ATTEMPT" --format '{{.ID}}')" ]]; then
        real_candidate_container_found=true
    fi
    if [[ -n "$(timeout 5 docker ps -a --format '{{.Names}}' | grep -x "xiangrugu-evidence-$ATTEMPT" || true)" ]]; then
        real_candidate_container_found=true
    fi
    refused=true
    if [[ "$authorization_present" != false || "$executable_files" != 0 ||
          "$materialize_dir_found" != false || "$staged_materialization" != 0 ||
          "$registered_attempt" != false || "$real_candidate_container_found" != false ]]; then
        refused=false
    fi
    printf '{"version":1,"status":"REAL_EXECUTION_REFUSED_NO_AUTHORIZATION","exit_code":2,"attempt_id":"%s","task_card_sha256":"%s","authorization_present":%s,"executable_request_or_approval_files":%s,"materialize_dir_found":%s,"staged_materialization_dirs":%s,"attempt_registered":%s,"real_candidate_container_found":%s,"refused_before_materialize":%s,"source_bytes_read":false,"postgresql_connected":false,"ready_for_import":false}\n' \
        "$ATTEMPT" "$card_sha" "$authorization_present" "$executable_files" "$materialize_dir_found" "$staged_materialization" "$registered_attempt" "$real_candidate_container_found" "$refused" \
        > "$run/refusal-receipt.json"
    service_state > "$run/services-after.txt"
    cmp -s "$run/services-before.txt" "$run/services-after.txt" || { echo 'Final service state differs' >&2; exit 1; }
    [[ "$refused" == true ]] || { echo 'Closed-state invariants violated; see receipt' >&2; exit 1; }
    printf '2\n' > "$run/exit-code.txt"
    # The intentional refusal is the first trigger; finish only records runner_exit.
    controller_first_trigger=true
    exit 2
fi

# Executing modes: the external human authorization must exist and bind the
# accepted card. This gate runs BEFORE any container or materialize call.
[[ -f "$runtime_root/authorization.json" && ! -L "$runtime_root/authorization.json" ]] || {
    echo 'No bound authorization; refusing before materialize' >&2; exit 2; }
python3 - "$runtime_root/authorization.json" "$CARD_SHA" "$ATTEMPT" <<'PY'
import hashlib,json,sys
raw=open(sys.argv[1],'rb').read(); doc=json.loads(raw)
assert doc.get('version')==1 and doc.get('status')=='AUTHORIZED_REAL_P01_SINGLE_ATTEMPT'
assert doc.get('attempt_id')==sys.argv[3] and doc.get('task_card_sha256')==sys.argv[2]
assert doc.get('one_attempt_only') is True and isinstance(doc.get('granted_by'),str) and doc['granted_by']
print(hashlib.sha256(raw).hexdigest())
PY
auth_sha=$(sha256sum -- "$runtime_root/authorization.json" | cut -d' ' -f1)
printf '%s\n' "$auth_sha" > "$run/authorization-sha256.txt"

controller_phase=collector
sample
controller_phase=runner
# Pinned metadata reproduction: ONLY the inputs the product binds by digest,
# exactly at the container paths recorded in the closed documents. Accepted RUN
# RECEIPTS (installed-origin.json, monitor.json, final-sample-request.json,
# limits.json, card-receipt.json, metadata-only-receipt.json) are NEVER copied
# into a fresh run dir — write_json_exclusive outputs would collide (B-23).
# stage-a-inputs.tsv rows are sha256 <TAB> container_path <TAB> staged_path,
# derived offline from the closed selection files + parent readiness bindings +
# review pins and cross-checked against packet-inputs-real.sha256.
# Container layout: /data/var/run = this output dir (rw evidence);
# /metadata = $run/output/metadata mounted READ-ONLY, holding every absolute
# /metadata-bound path the documents record — roots.yaml, selected-certificate,
# parent readiness AND the 14 repository-relative preparation pins staged under
# staged-repo/. The product resolves repo-relative reads as
# <repository_root>/<relative> with repository_root derived from the bound
# roots.yaml path inside _validate_preparation; CWD is irrelevant and stays
# /app. This gate runs BEFORE any container exists, so a mismatch never
# consumes the one-shot attempt registration.
table="$source_root/$EVIDENCE_REL/stage-a-inputs.tsv"
[[ -f "$table" && ! -L "$table" ]] || { echo 'Missing Stage A pin table' >&2; exit 2; }
(( $(grep -cv '^#' "$table") == 28 )) || { echo 'Stage A pin table size' >&2; exit 2; }
while IFS=$'\t' read -r want container_path staged_path; do
    [[ "$want" =~ ^[0-9a-f]{64}$ ]] || { echo 'Bad pin row' >&2; exit 2; }
    case "$container_path" in
        /metadata/*) target="$run/output/metadata${container_path#/metadata}" ;;
        /data/var/run/*) target="$run/output${container_path}" ;;
        /card/*) continue ;;  # dedicated constant-gated bind, verified by the worker itself
        *) echo "Unsupported bound path: $container_path" >&2; exit 2 ;;
    esac
    src="$source_root/$staged_path"
    [[ -f "$src" && ! -L "$src" ]] || { echo "Missing staged input: $staged_path" >&2; exit 2; }
    [[ "$(sha256sum -- "$src" | cut -d' ' -f1)" == "$want" ]] || {
        echo "Pinned input mismatch: $staged_path" >&2; exit 2; }
    mkdir -p -- "$(dirname -- "$target")"
    cp -p -- "$src" "$target"
    [[ "$(sha256sum -- "$target" | cut -d' ' -f1)" == "$want" ]] || {
        echo "Copied input drift: $container_path" >&2; exit 2; }
done < "$table"
chown -R -- 10001:10001 "$run/output"
mkdir -- "$run/output/durable"
mkdir -- "$run/output/durable/executions" "$run/output/durable/executions/$ATTEMPT"
mkdir -- "$run/output/durable/executions/$ATTEMPT/scratch"
chown -R -- 10001:10001 "$run/output/durable"
input_mount=(--mount "type=bind,src=$source_root/docs/superpowers/evidence/2026-11-13-request-reader-integration/installed-origin.py,dst=/installed-origin.py,readonly"
    --mount "type=bind,src=$run/output/metadata,dst=/metadata,readonly"
    --mount "type=bind,src=$source_root/task-card.closed.json,dst=/card/task-card.closed.json,readonly"
    --mount "type=bind,src=$source_root/$EVIDENCE_REL/materialize-real.py,dst=/materialize-real.py,readonly"
    --mount "type=bind,src=$runtime_root/authorization.json,dst=/authorization/authorization.json,readonly")
if [[ "$mode" == materialize ]]; then
    seconds=300
    # Adjudicated argv form (总指挥裁决 2026-11-14): the bind-mounted source
    # copy of installed-origin.py is mode 0644 WITHOUT a shebang, so Popen must
    # not exec it directly (PermissionError -> swallowed supervisor_error).
    # Launch it via the interpreter; installed-origin then execs
    # sys.executable with its own argv[1:], i.e. the real worker command.
    worker=(python /installed-origin.py /materialize-real.py "$image" "$revision")
    supervisor_args=(--lease /control/lease --evidence /data/var/run/monitor.json --seconds "$seconds")
    # Stage A evidence layout: durable outputs live under the evidence root.
    input_mount+=(--mount "type=bind,src=$run/output/durable,dst=/data/var/snapshots")
else
    seconds=1800
    printf '%s\n' "$request_pin" "$approval_pin" "$roots_pin_arg" > "$run/controller-pins-used.txt"
    mat_run="$runtime_root/$mat_suffix"
    # One-shot attempt registration BEFORE any Stage B container exists.
    # O_EXCL on the fixed attempt id: a second start fails even with a new
    # suffix or a different Stage A directory. Creation failure => no launch.
    register() {
        python3 - "$runtime_root/attempt-registration-$ATTEMPT.json" "$request_pin" "$approval_pin" "$roots_pin_arg" "$mat_suffix" "$suffix" "$CARD_SHA" "$auth_sha" "$run" <<'PY'
import json,os,sys,datetime
target=sys.argv[1]
record={'version':1,'attempt_id':'real-p01-20261113-a','task_card_sha256':sys.argv[7],
 'authorization_sha256':sys.argv[8],'request_sha256':sys.argv[2],'approval_sha256':sys.argv[3],
 'roots_sha256':sys.argv[4],'stage_a_run':sys.argv[5],'stage_b_run':sys.argv[6],
 'registered_at':datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
 'one_attempt_only':True,'container_created':False}
try:
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
except FileExistsError:
    msg='ATTEMPT_ALREADY_REGISTERED; this attempt is consumed, refusing to launch'
    print(msg,file=sys.stderr)
    # Persist the re-launch refusal so verify-real.sh can see the one-shot
    # gate fired (exit 3 recorded next to the refused run directory).
    import pathlib
    base=pathlib.Path(sys.argv[9])
    (base/'rerun-refusal.log').write_text(msg+'\nexisting_registration='+target+'\n')
    (base/'rerun-refusal-exit-code.txt').write_text('3\n')
    raise SystemExit(3)
with os.fdopen(fd,'w') as stream: stream.write(json.dumps(record,sort_keys=True,separators=(',',':'))+'\n'); stream.flush(); os.fsync(stream.fileno())
print('ATTEMPT_REGISTERED')
PY
    }
    # Fail-fast closed-state precheck BEFORE registration (adjudication item:
    # no real candidate container may exist for this attempt id).
    if [[ -n "$(timeout 5 docker ps -a --filter "label=io.xiangrugu.synthetic-run=$ATTEMPT" --format '{{.ID}}')" ]]; then
        echo 'Real candidate container already exists for this attempt' >&2; exit 2
    fi
    register
    # Stage B input closure, verified offline by verify-mount-table.py against
    # the REAL materialized request/approval documents (this stage runs AFTER
    # registration so a mismatch consumes nothing — it is pre-create):
    #   /metadata/**                       <- $run/output/metadata        (ro)  roots, certificate, parent readiness; repository_root for repo-relative pins
    #   /data/var/run/preparation|review   <- $run/output/{preparation,review} (rw mount, digest-bound bytes) preparation drafts + review pins
    #   /data/var/snapshots/materialization<- Stage A materialization dir  (ro)  request/approval/scope/budget/descriptor targets
    #   /data/var/snapshots/executions/$ATTEMPT -> batch output + scratch  (rw, fresh, uid 10001)
    #   /data/imports/usedata/$SNAPSHOT_ID <- snapshot version dir alone   (ro)
    # Repository-relative bindings resolve through _validate_preparation's
    # repository_root (= /metadata derived from the bound roots path); the
    # product NEVER depends on the process CWD. --workdir stays /app.
    input_mount+=(--mount "type=bind,src=$run/output/durable,dst=/data/var/snapshots"
        --mount "type=bind,src=$mat_run/output/durable/materialization,dst=/data/var/snapshots/materialization,readonly"
        --mount "type=bind,src=$SNAPSHOT_HOST_ROOT/$SNAPSHOT_ID,dst=/data/imports/usedata/$SNAPSHOT_ID,readonly")
    python3 "$source_root/$EVIDENCE_REL/verify-mount-table.py" \
        --materialization "$mat_run/output/durable/materialization" \
        --request-sha256 "$request_pin" --approval-sha256 "$approval_pin" \
        --roots-sha256 "$roots_pin_arg" --run-output "$run/output" \
        --table "$table" --snapshot-id "$SNAPSHOT_ID"
    # Unified failure path: task_control --failure-evidence == supervisor
    # --worker-failure so the correlation reader sees the SAME receipt bytes.
    failure_path=/data/var/run/failure-report.json
    # Adjudicated Stage B argv (总指挥裁决): interpreter-pinned installed-origin
    # chain, exactly as validated in the 38 rehearsal success case.
    worker=(python /installed-origin.py -m xiangrugu_datamgmt.task_control
        --request /data/var/snapshots/materialization/request.json --request-sha256 "$request_pin"
        --approval-sha256 "$approval_pin" --roots-sha256 "$roots_pin_arg"
        --image-id "$image" --git-revision "$revision" --image-user 10001:10001 --source-status dirty
        --lifecycle-seconds 1800 --failure-evidence "$failure_path"
        --authorized-source-mode project_snapshot)
    # --final = batch publication target (supervisor hardlinks the staged
    # result there after the final-sample handshake). The handshake file
    # itself is always evidence.with_name(final-sample-request.json) — do NOT
    # point --final at it.
    batch_final=/data/var/snapshots/executions/$ATTEMPT/batch.staged.json
    supervisor_args=(--lease /control/lease --evidence /data/var/run/monitor.json --seconds "$seconds"
        --authorized-source-mode project_snapshot --request-sha256 "$request_pin"
        --controller-request-file /data/var/snapshots/materialization/request.json
        --controller-request-sha256 "$request_pin"
        --worker-failure "$failure_path" --worker-request-sha256 "$request_pin"
        --final "$batch_final")
fi
host_seconds=$((seconds+30))
printf '%s\n' "$seconds" "$host_seconds" > "$run/deadlines.txt"
id=$(docker create --name "$name" --label "io.xiangrugu.synthetic-run=$suffix" \
    --cpus 0.5 --memory 768m --memory-swap 768m --pids-limit 128 \
    --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
    --tmpfs /tmp:rw,nosuid,nodev,size=33554432,uid=10001,gid=10001,mode=1777 \
    --tmpfs /data/var/run/scratch:rw,nosuid,nodev,size=67108864,uid=10001,gid=10001,mode=700 \
    --mount "type=bind,src=$run/control,dst=/control,readonly" \
    --mount "type=bind,src=$run/output,dst=/data/var/run" \
    "${input_mount[@]}" --workdir /app \
    --entrypoint python "$image" -m xiangrugu_datamgmt.candidate_supervisor \
    "${supervisor_args[@]}" -- "${worker[@]}")
owned=true
printf '%s\n' "$id" > "$run/container-id.txt"
if [[ "$mode" == real-readonly ]]; then
    # Mark the registration record as having crossed the creation boundary.
    python3 - "$runtime_root/attempt-registration-$ATTEMPT.json" "$id" <<'PY'
import json,os,sys
path=sys.argv[1]; value=json.load(open(path)); assert value['container_created'] is False
value['container_created']=True; value['container_id']=sys.argv[2]
tmp=path+'.next'
with open(tmp,'w') as stream: stream.write(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n'); stream.flush(); os.fsync(stream.fileno())
os.replace(tmp,path)
print('ATTEMPT_LAUNCH_RECORDED')
PY
fi
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
        controller_note trigger operator_cancel
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
if [[ "$mode" == materialize ]]; then
    [[ "$code" == 0 && "$(grep -o '"OOMKilled":true' "$run/container-state.json" || true)" == '' ]] || exit 1
    grep -q 'MATERIALIZE_REAL_REQUEST_OK' "$run/worker.log" || exit 1
    [[ -f "$run/output/durable/materialization/approval.json" &&
       -f "$run/output/durable/materialization/scope.json" &&
       -f "$run/output/durable/materialization/budget.json" &&
       -f "$run/output/durable/materialization/materialize-receipt.json" ]] || exit 1
    grep -q '"status":"REAL_REQUEST_MATERIALIZED_UNDER_AUTHORIZATION"' "$run/output/durable/materialization/materialize-receipt.json" || exit 1
    grep -q "\"task_card_sha256\":\"$CARD_SHA\"" "$run/output/durable/materialization/materialize-receipt.json" || exit 1
    # External pin fixing happens HERE, recorded for operator review before Stage B.
    sha256sum -- "$run/output/durable/materialization/request.json" \
                 "$run/output/durable/materialization/approval.json" \
                 "$run/output/durable/materialization/scope.json" \
                 "$run/output/durable/materialization/budget.json" \
                 "$run/output/durable/materialization/materialize-receipt.json" > "$run/controller-pins.txt"
    [[ -z "$(find "$run/output/durable" -name batch.json -o -name batch.staged.json)" ]] || exit 1
    echo MATERIALIZE_STAGE_A_OK
else
    # Stage B terminal states: success (exit 0, published batch) OR a single
    # bounded failure/timeout/cancel (nonzero, with correlated receipts). Both
    # end the attempt; the registry above already blocks any relaunch.
    [[ "$(grep -o '"OOMKilled":true' "$run/container-state.json" || true)" == '' ]] || exit 1
    if [[ "$code" == 0 ]]; then
        grep -q CONTROLLED_SOURCE_ONLY_TASK_STAGED "$run/worker.log" || exit 1
        echo REAL_READONLY_STAGE_B_OK
    else
        [[ -f "$run/output/failure-report.json" || -f "$run/output/worker-failure.json" ]] || {
            echo 'Nonzero Stage B without failure evidence' >&2; exit 1; }
        # Bounded stop with full evidence: the single attempt is consumed.
        # Propagate the candidate exit code; NEVER relaunch from here.
        echo REAL_READONLY_STAGE_B_STOPPED code="$code"
        controller_first_trigger=true
        exit "$code"
    fi
fi

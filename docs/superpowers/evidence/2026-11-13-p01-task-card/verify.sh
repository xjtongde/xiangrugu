#!/bin/bash
# Linux shell on host 32 only. Read-only native verification of the closed p01
# task-card preparation. No source bytes, no NAS content, no database queries.
# Usage: bash verify.sh RUNTIME_ROOT METADATA_SUFFIX PRODUCT_GATE_SUFFIX REJECT_SUFFIX
# Writes RUNTIME_ROOT/verification.json exclusively; exit 0 only if all checks pass.
set -Eeuo pipefail
runtime_root=${1:-}
metadata_suffix=${2:-}
gate_suffix=${3:-}
reject_suffix=${4:-}
EXPECTED_IMAGE=sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a
EXPECTED_REVISION=8fbc8c97fcf1d818caddf6ab556fa82d986643ed
ATTEMPT=real-p01-20261113-a
[[ "$runtime_root" == /opt/mydocker/xiangrugu/data/var/batch-runner-p01-task-card-20261113 && -d "$runtime_root" ]] || exit 2
for s in "$metadata_suffix" "$gate_suffix" "$reject_suffix"; do
    [[ "$s" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]] || exit 2
done
source_root=$(realpath -e -- "$(dirname -- "$0")/../../../..")
[[ "$source_root" == "$runtime_root"/source-green* ]] || exit 2
verification_file="$runtime_root/verification.json"
(set -o noclobber; : > "$verification_file") 2>/dev/null || { echo 'verification.json already exists' >&2; exit 2; }

ok=true
fail() { ok=false; echo "CHECK FAILED: $1" >&2; }

# 1. Image identity from Docker, not from narrative.
image_identity=$(timeout 5 docker image inspect --format '{{.Id}} {{index .Config.Labels "org.opencontainers.image.revision"}} {{.Config.User}} {{index .Config.Labels "io.xiangrugu.source.status"}}' "$EXPECTED_IMAGE" || echo MISSING)
image_identity_match=false
[[ "$image_identity" == "$EXPECTED_IMAGE $EXPECTED_REVISION 10001:10001 dirty" ]] && image_identity_match=true
[[ "$image_identity_match" == true ]] || fail image_identity

# 2. Per-container-run resource, supervision and cleanup checks.
run_checks() {
    local run="$runtime_root/$1" prefix=$2
    local hc="$run/host-config.json"
    grep -q '"NanoCpus":500000000' "$hc" || fail "$prefix cpus"
    grep -q '"Memory":805306368' "$hc" || fail "$prefix memory"
    grep -q '"MemorySwap":805306368' "$hc" || fail "$prefix memory_swap"
    grep -q '"PidsLimit":128' "$hc" || fail "$prefix pids"
    grep -q '"NetworkMode":"none"' "$hc" || fail "$prefix network"
    grep -q '"ReadonlyRootfs":true' "$hc" || fail "$prefix readonly_rootfs"
    grep -q '"CapDrop":\["ALL"\]' "$hc" || fail "$prefix cap_drop"
    grep -q '"SecurityOpt":\["no-new-privileges' "$hc" || fail "$prefix no_new_privileges"
    grep -q 'wd61workmetadata' "$hc" && fail "$prefix nas_mount"
    local limits="$run/output/limits.json"
    grep -q '"cpu.max":"50000 100000"' "$limits" || fail "$prefix cgroup_cpu"
    grep -q '"memory.max":"805306368"' "$limits" || fail "$prefix cgroup_memory"
    grep -q '"memory.swap.max":"0"' "$limits" || fail "$prefix cgroup_swap"
    grep -q '"pids.max":"128"' "$limits" || fail "$prefix cgroup_pids"
    grep -q '"worker_nice":19' "$limits" || fail "$prefix nice"
    grep -q '"worker_ionice":"idle"' "$limits" || fail "$prefix ionice"
    local monitor="$run/output/monitor.json"
    grep -q '"status":"SYNTHETIC_WORKER_COMPLETED"' "$monitor" || fail "$prefix monitor_status"
    grep -q '"reason":null' "$monitor" || fail "$prefix monitor_reason"
    grep -q '"process_group_gone":true' "$monitor" || fail "$prefix process_group"
    grep -q '"synthetic_only":true' "$monitor" || fail "$prefix synthetic_only"
    grep -q '"ready_for_import":false' "$monitor" || fail "$prefix ready_for_import"
    grep -q '"OOMKilled":true' "$run/container-state.json" && fail "$prefix oom"
    [[ "$(cat "$run/exit-code.txt")" == 0 ]] || fail "$prefix exit_code"
    cmp -s "$run/services-before.txt" "$run/services-after.txt" || fail "$prefix services_changed"
    [[ -f "$run/removal.txt" ]] || fail "$prefix removal_receipt"
    if timeout 5 docker inspect "xiangrugu-evidence-$1" >/dev/null 2>&1; then fail "$prefix container_still_exists"; fi
    [[ -f "$run/output/installed-origin.json" ]] || fail "$prefix installed_origin_missing"
    grep -q '"installed_product_verified":true' "$run/output/installed-origin.json" || fail "$prefix installed_origin_flag"
}
run_checks "$metadata_suffix" metadata
run_checks "$gate_suffix" product_gate

# 3. Installed module digests against the pinned 2026-11-13 build inputs.
installed_modules_match=true
for m in project_partition project_partition_coverage task_control readonly_batch candidate_supervisor batch_execution request_reader; do
    expected=$(grep "  datamgmt/src/xiangrugu_datamgmt/$m.py\$" "$source_root/metadata/build-inputs.sha256" | cut -d' ' -f1 || true)
    actual=$(grep -o "\"$m\":{\"path\":\"[^\"]*\",\"sha256\":\"[0-9a-f]\{64\}\"" "$runtime_root/$metadata_suffix/output/installed-origin.json" | grep -o '[0-9a-f]\{64\}' || true)
    if [[ -z "$expected" || "$actual" != "$expected" ]]; then installed_modules_match=false; fail "module_$m"; fi
done

# 4. Closed review and closed task card.
mout="$runtime_root/$metadata_suffix/output"
review_closed=false
if grep -q '"status":"DRAFT_PROJECT_PARTITION_REVIEW_NOT_EXECUTABLE"' "$mout/review/review.json" &&
   grep -q '"missing":\[\]' "$mout/review/review.json" &&
   grep -q '"source_read_authorized":false' "$mout/review/review.json" &&
   grep -q '"postgresql_authorized":false' "$mout/review/review.json" &&
   grep -q '"contract_frozen":false' "$mout/review/review.json" &&
   grep -q '"ready_for_import":false' "$mout/review/review.json"; then review_closed=true; fi
[[ "$review_closed" == true ]] || fail review_closed
card="$mout/task-card.closed.json"
card_sha=$(sha256sum -- "$card" | cut -d' ' -f1)
card_closed=false
if grep -q '"status":"CLOSED_REAL_PARTITION_TASK_CARD_NOT_EXECUTABLE"' "$card" &&
   grep -q "\"attempt_id\":\"$ATTEMPT\"" "$card" &&
   grep -q "\"image_id\":\"$EXPECTED_IMAGE\"" "$card" &&
   grep -q '"source_read_authorized":false' "$card" &&
   grep -q '"postgresql_authorized":false' "$card" &&
   grep -q '"contract_frozen":false' "$card" &&
   grep -q '"ready_for_import":false' "$card" &&
   grep -q '"expected_count":null' "$card" &&
   grep -q '"expected_sha256":null' "$card"; then card_closed=true; fi
[[ "$card_closed" == true ]] || fail card_closed
review_sha=$(sha256sum -- "$mout/review/review.json" | cut -d' ' -f1)
selection_sha=$(sha256sum -- "$mout/review.selection.json" | cut -d' ' -f1)
metadata_receipt_sha=$(sha256sum -- "$mout/metadata-only-receipt.json" | cut -d' ' -f1)
card_receipt_sha=$(sha256sum -- "$mout/card-receipt.json" | cut -d' ' -f1)
grep -q "\"task_card_sha256\":\"$card_sha\"" "$mout/card-receipt.json" || fail card_receipt_binding

# 5. No-authorization rejection: receipt plus live re-check.
rout="$runtime_root/$reject_suffix"
rejection_ok=false
if grep -q '"status":"REAL_EXECUTION_REFUSED_NO_AUTHORIZATION"' "$rout/rejection-receipt.json" &&
   grep -q '"exit_code":2' "$rout/rejection-receipt.json" &&
   grep -q "\"task_card_sha256\":\"$card_sha\"" "$rout/rejection-receipt.json" &&
   grep -q '"authorization_present":false' "$rout/rejection-receipt.json" &&
   grep -q '"executable_request_or_approval_files":0' "$rout/rejection-receipt.json" &&
   grep -q '"materialize_dir_found":false' "$rout/rejection-receipt.json" &&
   grep -q '"real_candidate_container_found":false' "$rout/rejection-receipt.json" &&
   grep -q '"refused_before_materialize":true' "$rout/rejection-receipt.json"; then rejection_ok=true; fi
[[ "$rejection_ok" == true ]] || fail rejection_receipt
[[ "$(cat "$rout/exit-code.txt")" == 2 ]] || fail rejection_exit_code
authorization_absent=true
[[ ! -e "$runtime_root/authorization" ]] || { authorization_absent=false; fail authorization_present; }
executable_files=$(find "$runtime_root" -type f \( -name request.json -o -name approval.json -o -name scope.json -o -name budget.json \) | wc -l)
[[ "$executable_files" == 0 ]] || fail executable_files_exist
[[ ! -e "$runtime_root/executions" ]] || fail executions_dir_exist
real_candidate_absent=true
if [[ -n "$(timeout 5 docker ps -a --filter "label=io.xiangrugu.synthetic-run=$ATTEMPT" --format '{{.ID}}')" ]]; then
    real_candidate_absent=false; fail real_candidate_container
fi
rejection_sha=$(sha256sum -- "$rout/rejection-receipt.json" | cut -d' ' -f1)

# 6. Product gate receipt.
gout="$runtime_root/$gate_suffix/output"
product_gate_ok=false
if grep -q '"refused":true' "$gout/product-gate-receipt.json" &&
   grep -q '"reason":"real_execution_closed"' "$gout/product-gate-receipt.json" &&
   grep -q '"batch_created":false' "$gout/product-gate-receipt.json" &&
   grep -q '"executable_request_created":false' "$gout/product-gate-receipt.json" &&
   grep -q '"approval_created":false' "$gout/product-gate-receipt.json" &&
   grep -q '"template_closed":true' "$gout/product-gate-receipt.json"; then product_gate_ok=true; fi
[[ "$product_gate_ok" == true ]] || fail product_gate_receipt
gate_receipt_sha=$(sha256sum -- "$gout/product-gate-receipt.json" | cut -d' ' -f1)
no_batch_anywhere=true
[[ -z "$(find "$runtime_root/$metadata_suffix/output" "$runtime_root/$gate_suffix/output" "$runtime_root/$reject_suffix/output" -name batch.json 2>/dev/null)" ]] || { no_batch_anywhere=false; fail batch_json_found; }

# 7. Host and service state (metadata only).
services=$(timeout 5 docker inspect --format '{{.Id}} {{.State.StartedAt}} {{.State.Status}} {{.State.Health.Status}}' pg32 pg32b || true)
services_healthy=false
[[ "$(printf '%s\n' "$services" | grep -c ' running healthy$')" == 2 ]] && services_healthy=true
[[ "$services_healthy" == true ]] || fail services_unhealthy
pg32_started_at=$(printf '%s\n' "$services" | sed -n 1p | awk '{print $2}')
pg32b_started_at=$(printf '%s\n' "$services" | sed -n 2p | awk '{print $2}')
boot_id=$(cat /proc/sys/kernel/random/boot_id)
pswpout=$(awk '/^pswpout /{print $2}' /proc/vmstat)
mem_available_kb=$(awk '/^MemAvailable:/{print $2}' /proc/meminfo)
loadavg_1min=$(awk '{print $1}' /proc/loadavg)
disk_avail_bytes=$(df -B1 --output=avail "$runtime_root" | tail -n 1 | tr -d ' ')
dev_idle=false
[[ "$(timeout 5 docker top xiangrugu-dev -eo pid,ppid,comm | awk 'NR>1 {n++} END {print n+0}')" == 1 ]] && dev_idle=true
[[ "$dev_idle" == true ]] || fail dev_not_idle
runtime_fs=$(findmnt -n -o FSTYPE -T "$runtime_root")
snapshot_root=/opt/mydocker/xiangrugu/data/imports/usedata
snapshot_dir_exists=false
[[ -d "$snapshot_root" ]] && snapshot_dir_exists=true
snapshot_fs=$(findmnt -n -o FSTYPE -T "$snapshot_root" 2>/dev/null || echo absent)
no_nas_filesystem=true
case "$runtime_fs:$snapshot_fs" in *cifs*|*nfs*) no_nas_filesystem=false; fail nas_filesystem ;; esac

status=P01_TASK_CARD_METADATA_VERIFIED_CLOSED
[[ "$ok" == true ]] || status=P01_TASK_CARD_VERIFICATION_FAILED
printf '{"version":1,"status":"%s","as_of":"2026-11-13","attempt_id":"%s","partition_id":"large-p01","image_id":"%s","image_identity":"%s","image_identity_match":%s,"installed_modules_verified":7,"installed_modules_match":%s,"metadata_run":"%s","product_gate_run":"%s","rejection_run":"%s","review_closed":%s,"review_sha256":"%s","selection_sha256":"%s","metadata_only_receipt_sha256":"%s","task_card_sha256":"%s","card_closed":%s,"card_receipt_sha256":"%s","rejection_receipt_sha256":"%s","rejection_ok":%s,"authorization_absent":%s,"executable_request_or_approval_files":%s,"real_candidate_absent":%s,"product_gate_ok":%s,"product_gate_receipt_sha256":"%s","no_batch_anywhere":%s,"removed_candidates":2,"services_healthy":%s,"pg32_started_at":"%s","pg32b_started_at":"%s","boot_id":"%s","host_pswpout":%s,"host_mem_available_kb":%s,"host_loadavg_1min":"%s","host_disk_avail_bytes":%s,"dev_idle":%s,"runtime_fs":"%s","snapshot_dir_exists":%s,"snapshot_fs":"%s","no_nas_filesystem":%s,"real_source_read":false,"source_bytes_read":false,"new_real_expectations":0,"postgresql_connected":false,"contract_frozen":false,"ready_for_import":false,"coverage_complete_tables":68,"coverage_total_tables":78,"task8_complete":false,"real_candidate_started":false,"authorization_consumed":false}\n' \
    "$status" "$ATTEMPT" "$EXPECTED_IMAGE" "$image_identity" "$image_identity_match" \
    "$installed_modules_match" "$metadata_suffix" "$gate_suffix" "$reject_suffix" \
    "$review_closed" "$review_sha" "$selection_sha" "$metadata_receipt_sha" \
    "$card_sha" "$card_closed" "$card_receipt_sha" "$rejection_sha" "$rejection_ok" \
    "$authorization_absent" "$executable_files" "$real_candidate_absent" \
    "$product_gate_ok" "$gate_receipt_sha" "$no_batch_anywhere" "$services_healthy" \
    "$pg32_started_at" "$pg32b_started_at" "$boot_id" "$pswpout" "$mem_available_kb" \
    "$loadavg_1min" "$disk_avail_bytes" "$dev_idle" "$runtime_fs" "$snapshot_dir_exists" \
    "$snapshot_fs" "$no_nas_filesystem" > "$verification_file.incomplete"
mv -T -- "$verification_file.incomplete" "$verification_file"
echo "verification: $status"
[[ "$ok" == true ]]

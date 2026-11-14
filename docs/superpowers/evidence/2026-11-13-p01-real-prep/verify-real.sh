#!/bin/bash
# Linux shell on host 32 only. Read-only native verification of the p01 real
# execution evidence chain (coarse chain + delegation to verify-terminal.py for
# the Stage B terminal state). Publishes verification-real.json exclusively.
# Usage: verify-real.sh <runtime_root> <refuse-suffix> <materialize-suffix> <real-suffix>
set -Eeuo pipefail
runtime_root=${1:?}; refuse_suffix=${2:?}; mat_suffix=${3:?}; real_suffix=${4:?}
[[ "$runtime_root" == /opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a ]] || exit 2
EXPECTED_IMAGE=sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a
CARD_SHA=41bd0ecfb8b9cf6081909f60e27780c40fd5d7bf3019847a77905a4f61fc0b69
REVIEW_SHA=a7c2c5bdb69a17e8c6038065f16eff378b81f443bdc486a8af1a2b014630c93d
ROOTS_SHA=6235c356fca754a687a2f02998770c9609b20748ade674d0050d86a0a428e07c
ATTEMPT=real-p01-20261113-a
J="$runtime_root/$refuse_suffix"; A="$runtime_root/$mat_suffix"; B="$runtime_root/$real_suffix"
verification_file="$runtime_root/verification-real.json"
terminal_file="$runtime_root/verification-terminal.json"
[[ ! -e "$verification_file" ]] || { echo 'verification-real.json already published' >&2; exit 2; }
(set -o noclobber; : > "$verification_file") 2>/dev/null || { echo 'cannot reserve verification file' >&2; exit 2; }
ok=true; fail() { ok=false; echo "FAIL: $*" >&2; }

# image identity
identity=$(timeout 5 docker image inspect --format '{{.Id}} {{index .Config.Labels "org.opencontainers.image.revision"}} {{.Config.User}} {{index .Config.Labels "io.xiangrugu.source.status"}}' "$EXPECTED_IMAGE" || echo MISSING)
[[ "$identity" == "$EXPECTED_IMAGE 8fbc8c97fcf1d818caddf6ab556fa82d986643ed 10001:10001 dirty" ]] || fail image_identity
for run in "$J" "$A" "$B"; do
    [[ "$(cat "$run/image-identity.txt")" == "$identity" ]] || fail "image_identity_$run"
done

# refusal receipt (exit 2, nothing materialized)
[[ "$(cat "$J/exit-code.txt")" == 2 ]] || fail refusal_exit_code
grep -q '"status":"REAL_EXECUTION_REFUSED_NO_AUTHORIZATION"' "$J/refusal-receipt.json" || fail refusal_status
grep -q '"refused_before_materialize":true' "$J/refusal-receipt.json" || fail refusal_gate
grep -q "\"task_card_sha256\":\"$CARD_SHA\"" "$J/refusal-receipt.json" || fail refusal_card_binding
grep -q '"attempt_registered":false' "$J/refusal-receipt.json" || fail refusal_no_registration
[[ ! -e "$runtime_root/executions" ]] || fail executions_dir_present
[[ ! -e "$runtime_root/attempt-registration-$ATTEMPT.json" ]] || {
    # registration may exist ONLY from the authorized Stage B run itself
    [[ -f "$B/container-id.txt" ]] || fail registration_without_stage_b
}
if [[ -f "$runtime_root/attempt-registration-$ATTEMPT.json" ]]; then
    grep -q "\"one_attempt_only\":true" "$runtime_root/attempt-registration-$ATTEMPT.json" || fail registration_one_shot_flag
fi
[[ -z "$(find "$runtime_root" -type f \( -name request.json -o -name approval.json \) -not -path "$A/*" -not -path "$B/*")" ]] || fail stray_executable_files

# one-shot re-launch refusal evidence (operator reruns record a refused start)
relaunch_refused=false
if [[ -f "$B/rerun-refusal-exit-code.txt" ]]; then
    [[ "$(cat "$B/rerun-refusal-exit-code.txt")" == 3 ]] || fail rerun_refusal_exit_code
    grep -q ATTEMPT_ALREADY_REGISTERED "$B/rerun-refusal.log" || fail rerun_refusal_log
    relaunch_refused=true
fi

# Stage A materialization under authorization
[[ "$(cat "$A/exit-code.txt")" == 0 ]] || fail materialize_exit_code
grep -q MATERIALIZE_REAL_REQUEST_OK "$A/worker.log" || fail materialize_worker_log
mat="$A/output/durable/materialization"
for f in request.json approval.json scope.json budget.json materialize-receipt.json; do
    [[ -f "$mat/$f" && ! -L "$mat/$f" ]] || fail "materialize_missing_$f"
done
grep -q '"status":"REAL_REQUEST_MATERIALIZED_UNDER_AUTHORIZATION"' "$mat/materialize-receipt.json" || fail materialize_receipt_status
grep -q "\"task_card_sha256\":\"$CARD_SHA\"" "$mat/materialize-receipt.json" || fail materialize_card_binding
grep -q "\"closed_review_sha256\":\"$REVIEW_SHA\"" "$mat/materialize-receipt.json" || fail materialize_review_binding
auth_now=$(sha256sum -- "$runtime_root/authorization.json" | cut -d' ' -f1)
[[ "$(cat "$A/authorization-sha256.txt")" == "$auth_now" ]] || fail authorization_drift
grep -q '"source_mode":"project_snapshot"' "$mat/request.json" || fail request_mode
grep -q '"lifecycle_seconds":1800' "$mat/request.json" || fail request_lifecycle
grep -q "\"roots_sha256\":\"$ROOTS_SHA\"" "$mat/request.json" || fail request_roots
while read -r sha name; do
    [[ "$(sha256sum -- "$name" | cut -d' ' -f1)" == "$sha" ]] || fail "controller_pin_drift:$name"
done < "$A/controller-pins.txt"

# Stage B single candidate: pins fixation + resource posture (coarse layer)
[[ -f "$B/controller-pins-used.txt" ]] || fail stage_b_pins_recorded
req_pin=$(sed -n 1p "$B/controller-pins-used.txt"); app_pin=$(sed -n 2p "$B/controller-pins-used.txt"); roots_pin=$(sed -n 3p "$B/controller-pins-used.txt")
[[ "$(sha256sum -- "$mat/request.json" | cut -d' ' -f1)" == "$req_pin" ]] || fail stage_b_request_pin_external_fixation
[[ "$(sha256sum -- "$mat/approval.json" | cut -d' ' -f1)" == "$app_pin" ]] || fail stage_b_approval_pin_external_fixation
[[ "$roots_pin" == "$ROOTS_SHA" ]] || fail stage_b_roots_pin
state=$(cat "$B/container-state.json")
if echo "$state" | grep -q '"OOMKilled":true'; then fail stage_b_oom; fi
hc=$(cat "$B/host-config.json")
echo "$hc" | grep -q '"NanoCpus":500000000' || fail stage_b_cpus
echo "$hc" | grep -q '"Memory":805306368' || fail stage_b_memory
echo "$hc" | grep -q '"MemorySwap":805306368' || fail stage_b_swap
echo "$hc" | grep -q '"PidsLimit":128' || fail stage_b_pids
echo "$hc" | grep -q '"NetworkMode":"none"' || fail stage_b_network
echo "$hc" | grep -q '"ReadonlyRootfs":true' || fail stage_b_readonly_root
echo "$hc" | grep -q '"CapDrop":\["ALL"\]' || fail stage_b_capdrop
echo "$hc" | grep -q '"SecurityOpt":\["no-new-privileges' || fail stage_b_no_new_privileges
if echo "$hc" | grep -q 'wd61workmetadata'; then fail stage_b_nas_mount; fi
grep -q '"cpu.max":"50000 100000"' "$B/output/limits.json" || fail stage_b_cgroup_cpu
grep -q '"memory.swap.max":"0"' "$B/output/limits.json" || fail stage_b_cgroup_swap
grep -q '"worker_nice":19' "$B/output/limits.json" || fail stage_b_nice
grep -q '"worker_ionice":"idle"' "$B/output/limits.json" || fail stage_b_ionice

# Deep terminal-state verification (monitor handshake, batch fields, failure
# correlation, twin publication, registry) — replaces shallow checks. Its JSON
# is published next to this report so reviewers see every individual check.
python3 "$(dirname "${BASH_SOURCE[0]}")/verify-terminal.py" "$B" "$A" > "$terminal_file.incomplete"
mv -T -- "$terminal_file.incomplete" "$terminal_file"
terminal_status=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$terminal_file")
outcome=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["outcome"])' "$terminal_file")
real_source_read=$(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print("true" if d["real_source_read"] else "false")' "$terminal_file")
code=$(cat "$B/exit-code.txt")
[[ "$terminal_status" == P01_TERMINAL_STATE_VERIFIED ]] || fail terminal_state
[[ "$outcome" == staged || "$outcome" == stopped ]] || fail terminal_outcome
# the publication file IS named batch.staged.json (hardlinked from its twin);
# only a legacy-named batch.json must never exist anywhere.
if [[ "$outcome" == staged ]]; then
    staged="$B/output/durable/executions/$ATTEMPT/batch.staged.json"
    [[ -f "$staged" ]] || fail batch_publication_missing
    cmp -s "$staged" "$B/output/durable/executions/$ATTEMPT/.batch.staged.json.incomplete" || fail batch_twin_drift
fi
batch_any=$(find "$runtime_root" -name 'batch.json' | wc -l)
[[ "$batch_any" == 0 ]] || fail legacy_batch_name_published

# recovery: both containers removed by exact name
for pair in "$A:xiangrugu-evidence-$mat_suffix" "$B:xiangrugu-evidence-$real_suffix"; do
    run=${pair%%:*}; nm=${pair#*:}
    grep -qx "$nm" "$run/removal.txt" || fail "removal_$nm"
    [[ -z "$(timeout 5 docker ps -a --format '{{.Names}}' | grep -x "$nm" || true)" ]] || fail "container_present_$nm"
done
# services stable & healthy across every run; boot id consistent
boot=$(cat /proc/sys/kernel/random/boot_id)
for run in "$J" "$A" "$B"; do
    cmp -s "$run/services-before.txt" "$run/services-after.txt" || fail "services_drift_$run"
    [[ "$(grep -c ' running healthy$' "$run/services-after.txt")" == 2 ]] || fail "services_unhealthy_$run"
    [[ "$(cat "$run/boot-id.txt")" == "$boot" ]] || fail "boot_id_$run"
done
pswpout=$(awk '/^pswpout /{print $2}' /proc/vmstat)
[[ "$pswpout" == 0 ]] || fail swap_activity
loadavg=$(awk '{print $1}' /proc/loadavg)
memavail=$(awk '/^MemAvailable:/{print $2}' /proc/meminfo)
diskavail=$(df -B1 --output=avail "$runtime_root" | tail -n1 | tr -d ' ')
dev_idle=$(timeout 5 docker top xiangrugu-dev -eo pid,ppid,comm | awk 'NR>1{n++} END{print n+0}')
[[ "$dev_idle" == 1 ]] || fail dev_not_idle
runtime_fs=$(findmnt -n -o FSTYPE --target "$runtime_root")
snapshot_fs=$(findmnt -n -o FSTYPE --target /opt/mydocker/xiangrugu/data/imports/usedata)
nas_fs=$(findmnt -rn -o FSTYPE | grep -cE 'cifs|nfs' || true)
[[ "$nas_fs" == 0 ]] || fail nas_filesystem_present
# boundaries
final_status=P01_REAL_READONLY_VERIFICATION_FAILED
[[ "$ok" == true ]] && final_status="P01_REAL_${outcome^^}_VERIFIED"
printf '{"version":1,"status":"%s","outcome":"%s","as_of":"2026-11-13","attempt_id":"%s","task_card_sha256":"%s","closed_review_sha256":"%s","image_identity":"%s","authorization_sha256":"%s","stage_a_run":"%s","stage_b_run":"%s","stage_b_exit_code":%s,"external_pins":{"request_sha256":"%s","approval_sha256":"%s","roots_sha256":"%s"},"terminal_verification":"%s","terminal_checks_all_passed":%s,"relaunch_refusal_evidenced":%s,"removed_candidates":2,"host_pswpout":%s,"host_mem_available_kb":%s,"host_loadavg_1min":"%s","host_disk_avail_bytes":%s,"dev_idle":%s,"runtime_fs":"%s","snapshot_fs":"%s","no_nas_filesystem":%s,"real_source_read":%s,"postgresql_connected":false,"contract_frozen":false,"ready_for_import":false,"new_real_expectations":0,"coverage_complete_tables":68,"coverage_total_tables":78,"task8_complete":false}\n' \
    "$final_status" "$outcome" "$ATTEMPT" "$CARD_SHA" "$REVIEW_SHA" "$identity" "$auth_now" \
    "$mat_suffix" "$real_suffix" "$code" "$req_pin" "$app_pin" "$roots_pin" \
    "$terminal_file" "$([[ "$terminal_status" == P01_TERMINAL_STATE_VERIFIED ]] && echo true || echo false)" \
    "$([[ "$relaunch_refused" == true ]] && echo true || echo false)" \
    "$pswpout" "$memavail" "$loadavg" "$diskavail" "$([[ "$dev_idle" == 1 ]] && echo true || echo false)" \
    "$runtime_fs" "$snapshot_fs" "$([[ "$nas_fs" == 0 ]] && echo true || echo false)" \
    "$real_source_read" > "$verification_file.incomplete"
mv -T -- "$verification_file.incomplete" "$verification_file"
echo "verification: $final_status outcome=$outcome real_source_read=$real_source_read"
[[ "$ok" == true ]]

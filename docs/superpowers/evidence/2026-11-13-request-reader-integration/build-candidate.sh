set -euo pipefail
cd "$(dirname -- "$0")/../../../.."
[[ "$(pwd -P)" == /opt/mydocker/xiangrugu/data/var/batch-runner-request-reader-20261113/source-green* ]] || exit 2
manual=/opt/mydocker/xiangrugu/data/var/batch-runner-request-reader-20261113/build
exec 9>/opt/mydocker/xiangrugu/data/var/sqlite-synthetic-batch.lock
flock -n 9
sha256sum -c docs/superpowers/evidence/2026-11-13-request-reader-integration/build-inputs.sha256 > "$manual/build-inputs-check.txt"
# Synchronization activates the existing watcher; wait without changing it.
quiet=0
for attempt in $(seq 1 30); do
 top=$(timeout 5 docker top xiangrugu-dev -eo pid,ppid,comm)
 printf '%s\n%s\n' "$(date -Is)" "$top" >> "$manual/devwatch-quiescence.txt"
 count=$(printf '%s\n' "$top" | awk 'NR>1 {n++} END {print n+0}')
 if [ "$count" = 1 ]; then quiet=$((quiet+1)); else quiet=0; fi
 if [ "$quiet" -ge 2 ]; then break; fi
 sleep 3
done
[ "$quiet" -ge 2 ] || { echo devwatch_busy; exit 1; }
baseline=$(timeout 5 docker inspect --format '{{.Id}} {{.State.StartedAt}} {{.State.Status}} {{.State.Health.Status}}' pg32 pg32b)
printf '%s\n' "$baseline" > "$manual/services-before.txt"
build_date=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf '%s\n' "$build_date" > "$manual/build-date.txt"
pid=
finish() {
 code=$?
 trap - EXIT HUP INT TERM
 if [ -n "$pid" ]; then
  kill -TERM -- "-$pid" 2>/dev/null || true
  sleep 1
  kill -KILL -- "-$pid" 2>/dev/null || true
  confirmed=false
  for attempt in 1 2 3 4 5; do
   if ! ps -eo pgid=,stat= | awk -v group="$pid" '$1==group && $2 !~ /^Z/ {found=1} END {exit !found}'; then
    confirmed=true
    break
   fi
   sleep 1
  done
  if ! "$confirmed"; then echo 'cancel_unconfirmed' >&2; exit 1; fi
  wait "$pid" 2>/dev/null || true
 fi
 exit "$code"
}
trap finish EXIT
trap 'exit 1' HUP INT TERM
sample() {
 current=$(awk '/^pswpout / {print $2}' /proc/vmstat)
 available=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
 load=$(awk '{print $1}' /proc/loadavg)
 io=$(awk '/^some / {split($2,a,"=");print a[2]}' /proc/pressure/io)
 memory=$(awk '/^some / {split($2,a,"=");print a[2]}' /proc/pressure/memory)
 disk=$(df -B1 --output=avail "$manual" | tail -n 1 | tr -d ' ')
 services=$(timeout 5 docker inspect --format '{{.Id}} {{.State.StartedAt}} {{.State.Status}} {{.State.Health.Status}}' pg32 pg32b)
 printf '%s target=%s pswpout=%s available_kib=%s load=%s io=%s memory=%s disk=%s\n' "$(date -Is)" "$target" "$current" "$available" "$load" "$io" "$memory" "$disk" >> "$manual/build-host-samples.txt"
 for unit in docker.service containerd.service; do
  cg=$(systemctl show "$unit" --property=ControlGroup --value)
  printf '%s %s ' "$(date -Is)" "$unit" >> "$manual/build-cgroup-samples.txt"
  paste -sd ' ' "/sys/fs/cgroup$cg/memory.current" "/sys/fs/cgroup$cg/memory.swap.current" >> "$manual/build-cgroup-samples.txt"
 done
 [ "$services" = "$baseline" ] && [ "$(printf '%s\n' "$services" | grep -c ' running healthy$')" = 2 ]
}
for target in test runtime; do
 tag="xiangrugu:$target-request-reader-20261113-a"
 if docker image inspect "$tag" >/dev/null 2>&1; then echo 'Candidate tag exists; refuse overwrite'; exit 2; fi
 sample
 [ "$available" -ge 2097152 ] && [ "$disk" -ge 17179869184 ]
 awk -v l="$load" -v i="$io" -v m="$memory" 'BEGIN {exit !(l<2 && i<10 && m<1)}'
 previous=$current
 declare -A streak=([swap_pressure]=0 [memory_pressure]=0 [load_pressure]=0 [io_pressure]=0 [memory_stall]=0)
 setsid docker buildx build --load --progress plain --target "$target" -t "$tag" \
   --resource memory=768m --resource memory-swap=768m \
   --resource cpu-quota=50000 --resource cpu-period=100000 \
   --iidfile "$manual/$target-image.id" \
   --build-arg "BUILD_DATE=$build_date" \
   --build-arg VCS_REF=8fbc8c97fcf1d818caddf6ab556fa82d986643ed \
   --build-arg SOURCE_STATUS=dirty --build-arg VERSION=0.1.0 . > "$manual/build-$target.log" 2>&1 &
 pid=$!
 started=$SECONDS
 reason=
 while kill -0 "$pid" 2>/dev/null; do
  if ! sample; then reason=service_unhealthy; fi
  for key in swap_pressure memory_pressure load_pressure io_pressure memory_stall; do
   case "$key" in
    swap_pressure) if [ "$current" -gt "$previous" ]; then bad=1; else bad=0; fi ;;
    memory_pressure) if [ "$available" -lt 1572864 ]; then bad=1; else bad=0; fi ;;
    load_pressure) bad=$(awk -v n="$load" 'BEGIN {print (n>=3 ? 1 : 0)}') ;;
    io_pressure) bad=$(awk -v n="$io" 'BEGIN {print (n>=10 ? 1 : 0)}') ;;
    memory_stall) bad=$(awk -v n="$memory" 'BEGIN {print (n>=1 ? 1 : 0)}') ;;
   esac
   if [ "$bad" = 1 ]; then streak[$key]=$(( ${streak[$key]}+1 )); else streak[$key]=0; fi
   if [ "${streak[$key]}" -ge 2 ]; then reason=$key; fi
  done
  if [ "$current" -lt "$previous" ]; then reason=monitor_invalid; fi
  previous=$current
  if [ "$disk" -lt 8589934592 ]; then reason=disk_floor; fi
  if [ $((SECONDS-started)) -ge 600 ]; then reason=build_timeout; fi
  if [ -n "$reason" ]; then
   printf '%s\n' "$reason" > "$manual/build-stop.txt"
   echo "build_stopped=$reason"
   exit 1
  fi
  sleep 5
 done
 set +e
 wait "$pid"
 code=$?
 set -e
 pid=
 printf '%s\n' "$code" > "$manual/build-$target.exit"
 tail -n 3 "$manual/build-$target.log"
 [ "$code" = 0 ]
 cat "$manual/$target-image.id"
done
timeout 5 docker inspect --format '{{.Id}} {{.State.StartedAt}} {{.State.Status}} {{.State.Health.Status}}' pg32 pg32b > "$manual/services-after.txt"

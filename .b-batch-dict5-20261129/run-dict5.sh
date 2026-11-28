#!/bin/bash
# 隔离用例入口（A=成功 / B=中途失败回滚）。只连显式传入的隔离实例地址。
set +x
CASE="${1:-A}"; IP="$2"
[ -n "$IP" ] || { echo "usage: $0 <A|B> <iso_ip>"; exit 64; }
case "$CASE" in A|B) ;; *) echo "case must be A or B"; exit 64;; esac
HV=/opt/mydocker/xiangrugu/data/var
IMG=xiangrugu@sha256:2ba6c23602bc1e176607ab8d56fa53f0110b6a33ac2fff25f205837626350d03
NET=xrg-iso-a02-d5
test -r "$HV/b-batch/dict5/.pw" || { echo "PW_FILE_MISSING"; exit 1; }
echo "--- path assertion before run ---"
docker run --rm --network none -v "$HV/b-batch":/data-var-bb:ro --entrypoint sh "$IMG" -c '
  for f in contract-five-tables.json YEAR_RANGE_CODES.payload.tsv MEASURE_CODES.payload.tsv \
           PARENTAL_STATUS_CODES.payload.tsv SOCIAL_INSTITUTION_TYPES.payload.tsv \
           OCCASION_CODES.payload.tsv; do
    [ -r "/data-var-bb/dict5/$f" ] || { echo "MISSING $f"; exit 1; }
  done; echo PATHS_OK' </dev/null || exit 1
docker run --rm -i --network "$NET" -v "$HV/b-batch":/data-var-bb:rw \
  -v "$HV/b-batch/dict5/load-dict5.py":/entry.py:ro \
  --entrypoint sh "$IMG" -c "cp /entry.py /e.py; python3 -u /e.py $CASE $IP; RC=\$?; rm -f /data-var-bb/dict5/.pw; exit \$RC" </dev/null
RC=$?; echo "ISO_ENTRY_RC=$RC"; exit "$RC"

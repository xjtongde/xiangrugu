#!/bin/bash
# 隔离用例入口（A=成功 / B=中途失败回滚）—— 十张 CBDB 字典表。
# 只连显式传入的隔离实例地址；本脚本不面向生产库。
set +x
CASE="${1:-A}"; IP="$2"
[ -n "$IP" ] || { echo "usage: $0 <A|B> <iso_ip>"; exit 64; }
case "$CASE" in A|B) ;; *) echo "case must be A or B"; exit 64;; esac
HV=/opt/mydocker/xiangrugu/data/var
IMG=xiangrugu@sha256:2ba6c23602bc1e176607ab8d56fa53f0110b6a33ac2fff25f205837626350d03
NET=xrg-iso-a02-d10
D=$HV/b-batch/dict10
test -r "$D/.pw" || { echo "PW_FILE_MISSING"; exit 1; }

echo "--- path assertion before run ---"
docker run --rm --network none -v "$D":/dd:ro --entrypoint sh "$IMG" -c '
  for f in contract-ten-tables.json \
           COUNTRY_CODES.payload.tsv LITERARYGENRE_CODES.payload.tsv \
           TEXT_ROLE_CODES.payload.tsv APPOINTMENT_TYPES.payload.tsv \
           STATUS_TYPES.payload.tsv ALTNAME_CODES.payload.tsv \
           BIOG_ADDR_CODES.payload.tsv BIOG_INST_CODES.payload.tsv \
           ENTRY_TYPES.payload.tsv INDEXYEAR_TYPE_CODES.payload.tsv; do
    [ -r "/dd/$f" ] || { echo "MISSING $f"; exit 1; }
  done; echo PATHS_OK' </dev/null || exit 1

docker run --rm -i --network "$NET" -v "$D":/data-var-bb:rw \
  --entrypoint sh "$IMG" -c \
  "cp /data-var-bb/load-dict10.py /e.py; python3 -u /e.py $CASE $IP; RC=\$?; rm -f /data-var-bb/.pw; exit \$RC" </dev/null
RC=$?; echo "ISO_ENTRY_RC=$RC"; exit "$RC"

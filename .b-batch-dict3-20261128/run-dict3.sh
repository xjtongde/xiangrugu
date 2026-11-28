#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# 固定三表装载入口（隔离实例）—— CBDB 字典表 EXTANT / POSSESSION_ACT / ASSUME_OFFICE
# 用法: ./run-dict3.sh <A|B> <iso_host_ip>
#   A = 成功路径（三表同事务提交，提交前校验 4/4/6）
#   B = 回滚路径（写入 >=1 张后注入真实数据库错误，整体回滚）
# ══════════════════════════════════════════════════════════════════════════════
# 生产库 pg32b:5433/xiangrugu **不由本脚本触碰**：本入口只接受显式传入的隔离实例地址，
# 且装载前会核对 dbname/port/role/标记 + 三目标不存在。正式导入等 Codex 放行。
set +x
CASE="${1:-A}"
IP="$2"
[ -n "$IP" ] || { echo "usage: $0 <A|B> <iso_host_ip>"; exit 64; }
case "$CASE" in A|B) ;; *) echo "case must be A or B"; exit 64;; esac

HV=/opt/mydocker/xiangrugu/data/var
IMG=xiangrugu@sha256:2ba6c23602bc1e176607ab8d56fa53f0110b6a33ac2fff25f205837626350d03

# 口令只经文件进容器内读取：不上命令行、不入日志。
test -r "$HV/b-batch/dict3/.pw" || { echo "PW_FILE_MISSING"; exit 1; }

docker run --rm -i \
  --network xrg-iso-a02-dt \
  -v "$HV/b-batch":/data-var-bb:rw \
  -v "$HV/b-batch/dict3/load-dict3.py":/load-dict3.py:ro \
  --entrypoint sh "$IMG" -c '
    set +x
    cp /load-dict3.py /ld.py
    python3 -u /ld.py '"$CASE"' '"$IP"'
    RC=$?
    rm -f /data-var-bb/dict3/.pw
    exit $RC' </dev/null
RC=$?
echo "ENTRY_RC=$RC"
exit "$RC"

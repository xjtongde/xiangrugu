#!/bin/sh
# 实际执行的隔离装载命令（无占位符）｜钉扎代码 a5d12b1｜替身 xrg-v-iso4
# 本脚本只含正向/回滚三例；N1 lookalike 与生产方向负向实跑的命令见文件末尾注释。
export PYTHONPATH=/tmp/xrg-deps:/opt/code/xrg/datamgmt/src
export XNG_LOAD_PASSWORD=loaderonly
run() {
  python3 -m xiangrugu_datamgmt.cbdb_social_addr_runner --phase phase1-isolated \
    --code-root /opt/code/xrg --code-commit a5d12b13ad87b74fea5e8e7b2fb8a2c901bbad9e \
    --contract /data/var/in/frozen-contract.json --approval-table /data/var/in/approval-table.json \
    --approval-text /data/var/in/approval-text-verbatim.txt \
    --approval-text-sha256 4d250c8e08ea8136e29e35aa436812f11b5eec59a100847f130c11f39b7e2946 \
    --scope /data/var/in/isolated-scope.json --expected /data/var/in/$2 \
    --payload /data/var/work/payload.bin --scratch /data/var/scratch \
    --connect-host 127.0.0.1 --connect-port 5432 --load-role xrg_loader \
    --evidence-out /data/var/work/ev-$1.json
  echo "$1 EXIT=$?"
}
q() { PGPASSWORD=loaderonly psql -X -tA -h 127.0.0.1 -U xrg_loader -d xiangrugu_iso -c "$1"; }
echo '=== P1 ==='; run P1_positive isolated-expected.json
echo -n 'rows='; q "select count(*) from cbdb.cbdb__social_u5f_institution_u5f_addr"
echo '=== N7 ==='; q 'DROP TABLE IF EXISTS cbdb.cbdb__social_u5f_institution_u5f_addr' >/dev/null 2>&1
run N7_rollback isolated-expected-rollback.json
echo -n 'to_regclass='; q "select coalesce(to_regclass('cbdb.cbdb__social_u5f_institution_u5f_addr')::text,'TABLE_ABSENT')"
echo '=== P3 ==='; run P3_final isolated-expected.json
echo -n 'rows='; q "select count(*) from cbdb.cbdb__social_u5f_institution_u5f_addr"

# ---------------------------------------------------------------- 负向实跑
# 下面两组是 n1-n2-resolution.json 中 live_replay / production_direction_live
# 的实际命令形态（把 run() 的 --expected 换成正向件即可，负向在预检阶段即被拒，
# 不会走到装载）。保留在此便于复算：
#
# for h in xrg-pg32b xrg-prod-proxy my-trial-pg standin.example.com; do
#   <同 run() 的命令，--connect-host "$h" --connect-port 5432 -->
# done
#   -> 四个 host 均 exit=4 isolated_mode_host_not_a_standin，无 session 键
#
# for c in "pg32b 5432" "pg32b 5433"; do
#   set -- $c
#   <同 run() 的命令，--connect-host "$1" --connect-port "$2" -->
# done
#   -> 均 exit=4 isolated_mode_targets_production_endpoint，无 session 键

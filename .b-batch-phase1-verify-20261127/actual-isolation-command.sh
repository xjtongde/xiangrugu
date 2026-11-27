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

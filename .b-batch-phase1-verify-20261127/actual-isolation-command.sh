#!/bin/sh
# 实际执行的隔离装载命令（无占位符）
# 代码提交 de3517f2a0d575a4b0d1c30be138a25961b9ae4b
export PYTHONPATH=/tmp/xrg-deps:/opt/code/xrg/datamgmt/src
export XNG_LOAD_PASSWORD=loaderonly
python3 -m xiangrugu_datamgmt.cbdb_social_addr_runner --phase phase1-isolated \
  --code-root /opt/code/xrg --code-commit de3517f2a0d575a4b0d1c30be138a25961b9ae4b \
  --contract /data/var/in/frozen-contract.json \
  --approval-table /data/var/in/approval-table.json \
  --approval-text /data/var/in/approval-text-verbatim.txt \
  --approval-text-sha256 4d250c8e08ea8136e29e35aa436812f11b5eec59a100847f130c11f39b7e2946 \
  --scope /data/var/in/isolated-scope.json \
  --expected /data/var/in/isolated-expected.json \
  --payload /data/var/work/payload.bin --scratch /data/var/scratch \
  --connect-host 127.0.0.1 --connect-port 5432 --load-role xrg_loader \
  --evidence-out /data/var/work/ev-P1_positive.json

#!/bin/bash
# 正式入口包装：端点写死在 load-dict3-formal.py 内，此处不提供任何 host/dbname/port 参数。
set +x
HV=/opt/mydocker/xiangrugu/data/var
IMG=xiangrugu@sha256:2ba6c23602bc1e176607ab8d56fa53f0110b6a33ac2fff25f205837626350d03
MODE="${1:-preflight}"      # preflight | load   —— 仅此一个位置参数，无注入开关
case "$MODE" in
  preflight) FLAG="--preflight-only" ;;
  load)      FLAG="" ;;
  *) echo "usage: $0 [preflight|load]"; exit 64 ;;
esac
test -r /run/secrets/xrg_loader_password || { echo "SECRET_NOT_PRESENT"; exit 1; }
docker run --rm -i --network host --add-host pg32b:127.0.0.1 \
  -v "$HV":/data/var:ro \
  -v /run/secrets:/secrets:ro \
  -v "$HV/b-batch/dict3/load-dict3-formal.py":/entry.py:ro \
  --entrypoint sh "$IMG" -c "cp /entry.py /e.py; python3 -u /e.py $FLAG" </dev/null
RC=$?
echo "FORMAL_ENTRY_RC=$RC"
exit "$RC"

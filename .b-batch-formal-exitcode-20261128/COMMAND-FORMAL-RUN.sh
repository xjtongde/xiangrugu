# ══════════════════════════════════════════════════════════════════════
# 本盒实测用的完整命令（无占位符，可直接执行）
# 与 .b-batch-real-runner-binding-20261127/COMMAND-FORMAL.txt@c291fce 同形，
# 仅把目录换成全新干净的 code3/work3。
#
# ⚠ 关键：所有「执行命令」的 docker exec **不带 -i** 且显式 </dev/null。
#   `docker exec -i` 会把容器 stdin 接到脚本自身 stdin；整份命令经 heredoc/
#   bash -s 喂入时会吞掉未读正文 —— 表现为永久挂起且无报错（本盒实测发现）。
#   只有用 tar/cat 经 stdin 传数据的步骤才需要 -i。
#
# ⚠ 退出码一律 RC=$? 紧跟被测命令取，不用管道（cmd | tail 会把 tail 的状态当结论）。
# ══════════════════════════════════════════════════════════════════════
PIN=a5d12b13ad87b74fea5e8e7b2fb8a2c901bbad9e
CODE_ROOT=/data/var/b-batch/code3/xrg-batch
WORK=/data/var/b-batch/work3
PAYLOAD=/data/var/b-batch/payload.bin

# ── 步骤 0a：在交付方 clone 上导出 ──
git archive --format=tar --prefix=xrg-batch/ "$PIN" | gzip > xrg-batch.tgz
git rev-parse "$PIN" > PIN.txt

# ── 步骤 0b：送入容器并解包到干净目录（此处 -i 是必需的：数据走 stdin）──
ssh 32 'docker exec -i xiangrugu-dev sh -c \
  "rm -rf /data/var/b-batch/code3 && mkdir -p /data/var/b-batch/code3 \
   && tar xzf - -C /data/var/b-batch/code3"' < xrg-batch.tgz
ssh 32 'docker exec -i xiangrugu-dev sh -c \
  "cat > /data/var/b-batch/code3/xrg-batch/PIN_COMMIT"' < PIN.txt

# 安装模块清单：经临时文件中转 + docker cp，并核对是常规文件
# （docker cp /dev/stdin 会写出指向 /proc/self/fd/0 的坏符号链接且返回 0）
scp PIN_MODULES.json 32:/tmp/
ssh 32 'docker cp /tmp/PIN_MODULES.json xiangrugu-dev:'"$CODE_ROOT"'/PIN_MODULES.json'
ssh 32 'docker exec xiangrugu-dev sh -c \
  "test -f '"$CODE_ROOT"'/PIN_MODULES.json && ! test -L '"$CODE_ROOT"'/PIN_MODULES.json && echo REGULAR_FILE_OK"'

# ── 步骤 1：容器内只读预检（实际载荷）──
ssh 32 'bash -s' <<REMOTE
docker exec -w "$WORK" -e PYTHONPATH="$CODE_ROOT/datamgmt/src" xiangrugu-dev \
  python3 -c "import xiangrugu_datamgmt as m;print(m.__file__)" </dev/null > /tmp/probe.out
RC=$?
if [ "$RC" -ne 0 ] || ! grep -q "^$CODE_ROOT/datamgmt/src/" /tmp/probe.out; then
  echo "RUNTIME_NOT_FROM_EXPORT_TREE rc=$RC"; exit 1
fi
echo "PROBE_RC=$RC module=$(cat /tmp/probe.out)"

docker exec -w "$WORK" -e PYTHONPATH="$CODE_ROOT/datamgmt/src" xiangrugu-dev \
  python3 .b-batch-real-runner-binding-20261127/preflight.py --phase phase2-production \
  --scope ".b-batch-real-runner-binding-20261127/formal-scope.json" \
  --expected ".b-batch-real-runner-binding-20261127/formal-expected.json" \
  --approval-text ".b-batch-real-load-20261127/approval-text-verbatim.txt" \
  --approval-table "datamgmt/contracts/releases/2026-10-06-bootstrap/b-approval-table-v2.json" \
  --payload "$PAYLOAD" --code-root "$CODE_ROOT" --code-commit "$PIN" \
  --evidence-out /data/var/b-batch/preflight-formal-code3.json </dev/null
RC=$?
echo "PREFLIGHT_EXIT=$RC"
[ "$RC" -eq 0 ] || { echo "ABORT_BEFORE_LOAD: preflight rc=$RC"; exit "$RC"; }
REMOTE

# ── 步骤 2：正式装载（真实 runner；本盒按边界要求**未执行**）──
# 结构必须与下面这段一致：捕获 RC、非 0 短路、末尾 exit "$RC" 原样传出。
# export XNG_LOAD_PASSWORD="$(cat /run/secrets/xrg_loader_password)"
# docker exec -w "$WORK" -e PYTHONPATH="$CODE_ROOT/datamgmt/src" \
#   -e XNG_LOAD_PASSWORD xiangrugu-dev \
#   python3 -m xiangrugu_datamgmt.cbdb_social_addr_runner ... </dev/null
# RC=$?; echo "LOAD_EXIT=$RC"; exit "$RC"

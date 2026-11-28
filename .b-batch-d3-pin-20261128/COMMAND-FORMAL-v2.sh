#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# B 批正式单表装载 —— 交付命令 v2（修正装载入口）
# 运行时 PIN   : 9f786106bc00336f8e99c97c35035a72d3fe9383   （含 D3 修复）
# 候选镜像     : xiangrugu@sha256:2ba6c23602bc1e176607ab8d56fa53f0110b6a33ac2fff25f205837626350d03
# ══════════════════════════════════════════════════════════════════════════════
#
# 【为什么要改】上一盒实测：原 COMMAND-FORMAL.txt 步骤 2 用
#     docker exec … xiangrugu-dev python3 -m …cbdb_social_addr_runner
# 而 **xiangrugu-dev 容器里没有 psql**（`which psql` → NO_PSQL_IN_DEV）。
# runner 靠 subprocess.Popen(["psql", …]) 驱动会话，于是那条命令在它自己指定的容器里
# **永远跑不起来**，直接崩在 loader L354：FileNotFoundError: 'psql'，退出码 1。
# 这与门禁逻辑无关，是交付命令自身的缺陷。
#
# 有 psql(18.7 PGDG) 的是候选镜像本身，所以入口改为 `docker run` 该镜像。
# 注意：镜像里 site-packages 也 pip install 了一份包；必须用 PYTHONPATH 指向
# code root 的 src，并核 digest，否则会误跑另一份码（见下方第 0 步）。
set +x

# ── 路径基准（务必区分命名空间）────────────────────────────────────────────
# 宿主 32 上的 /data/var 与容器内 /data/var 不是同一个对象：容器 /data/var 是
# /opt/mydocker/xiangrugu/data/var 的 bind mount。**挂载源必须到 data/var 这一层**，
# 不能写成 -v $HB:/data/var —— 那样容器里的 b-batch 会平移到 /data/var 根下，
# 于是 /data/var/b-batch/code7 不存在，PYTHONPATH 静默失效、退回镜像 site-packages 那份码。
# （本盒实测踩过：探针因此断言失败，正好证明第 0 步这道检查是必要的。）
HV=/opt/mydocker/xiangrugu/data/var                  # 宿主命名空间（挂载源）
HB=$HV/b-batch                                       # 宿主侧工作目录
CR=/data/var/b-batch/code7                           # 容器命名空间（同一棵树）
PIN=9f786106bc00336f8e99c97c35035a72d3fe9383
IMG=xiangrugu@sha256:2ba6c23602bc1e176607ab8d56fa53f0110b6a33ac2fff25f205837626350d03
PAYLOAD=$HB/payload.bin
BINDIR=/data/var/b-batch                             # scratch 必须在 /data/var 下

test -r /run/secrets/xrg_loader_password \
  || { echo "SECRET_NOT_PRESENT_ON_HOST_32: /run/secrets/xrg_loader_password"; exit 1; }

# ── 0) 先证"要跑的码确实是 PIN 那份"，再谈装载 ────────────────────────────
# 期望 loader 摘要（来自同提交的 PIN_MODULES.json）：
#   802088c0bb0ea260af5b308c1da273b0ac9723679c82d888bdd96b58de6b0f47
docker run --rm --network none \
  -v "$HV":/data/var:ro \
  -e PYTHONPATH="$CR/datamgmt/src" \
  --entrypoint python3 "$IMG" -c "
import hashlib, pathlib, sys
import xiangrugu_datamgmt.cbdb_social_addr_loader as L
p = pathlib.Path(L.__file__)
want = open('$CR/PIN_MODULES.json').read()
print('resolved      =', p)
print('digest        =', hashlib.sha256(p.read_bytes()).hexdigest())
assert str(p).startswith('/data/var/'), 'PYTHONPATH 未生效：解析到镜像 site-packages'
assert 'ddl = ddl_for(target, create_schema=create_schema)' in p.read_text(), 'D3 修复不在'
print('OK: 运行的是 code root 里的 PIN 版本，且含 D3 修复')
" </dev/null || { echo "CODE_PROBE_FAILED"; exit 1; }

# ── 1) 预检（批准件 8be2202b…，勿用 a5d12b1 树里的 63f2738a…）─────────────
docker run --rm -i --network host --add-host pg32b:127.0.0.1 \
  -v "$HV":/data/var:rw \
  -w "$CR" -e PYTHONPATH="$CR/datamgmt/src" \
  --entrypoint sh "$IMG" -c "
    python3 .b-batch-real-runner-binding-20261127/preflight.py \
      --phase phase2-production --code-root '$CR' --code-commit '$PIN' \
      --approval-text '.b-batch-real-load-20261127/approval-text-verbatim.txt' \
      --approval-table 'datamgmt/contracts/releases/2026-10-06-bootstrap/b-approval-table-v2.json' \
      --scope '.b-batch-real-runner-binding-20261127/formal-scope.json' \
      --expected '.b-batch-real-runner-binding-20261127/formal-expected.runcopy.json' \
      --payload '/data/var/b-batch/payload.bin' </dev/null
    echo PREFLIGHT_RC=\$?" </dev/null
# 预期 {"outcome": "PASSED", "checks": 17}，PREFLIGHT_RC=0；非 0 则停，不得进入装载。

# ── 2) 正式装载（一次机会；失败立即停报，不重跑、不覆盖、不删表）──────────
# 口令只经容器内读 secret 文件进环境变量：绝不上命令行、绝不入日志/Git。
# 网络构造用 --network host + --add-host pg32b:127.0.0.1：
#   pg32b:5433 这个端点只在宿主网络命名空间存在（容器网内只有 5432）。
#   这不削弱 Gate A —— 门禁校验的是服务端事实（SHOW port / inet_server_addr() /
#   标记值），不是客户端 DNS 怎么解析。
docker run --rm -i --network host --add-host pg32b:127.0.0.1 \
  -v "$HV":/data/var:rw \
  -v /run/secrets:/secrets:ro \
  -w "$CR" -e PYTHONPATH="$CR/datamgmt/src" \
  --entrypoint sh "$IMG" -c '
    set +x
    export XNG_LOAD_PASSWORD="$(cat /secrets/xrg_loader_password)"
    python3 -m xiangrugu_datamgmt.cbdb_social_addr_runner \
      --phase phase2-production \
      --code-root   '"'$CR'"' \
      --code-commit '"'$PIN'"' \
      --contract    "datamgmt/contracts/releases/2026-10-06-bootstrap/b-single-table-frozen-candidate.json" \
      --approval-table "datamgmt/contracts/releases/2026-10-06-bootstrap/b-approval-table-v2.json" \
      --approval-text  ".b-batch-real-load-20261127/approval-text-verbatim.txt" \
      --approval-text-sha256 4d250c8e08ea8136e29e35aa436812f11b5eec59a100847f130c11f39b7e2946 \
      --scope       ".b-batch-real-runner-binding-20261127/formal-scope.json" \
      --expected    ".b-batch-real-runner-binding-20261127/formal-expected.runcopy.json" \
      --payload     "/data/var/b-batch/payload.bin" \
      --scratch     "'"$BINDIR"'" \
      --evidence-out "/data/var/b-batch/evidence-formal-d3.json" </dev/null
    RC=$?; unset XNG_LOAD_PASSWORD; echo "INNER_EXIT=$RC"; exit $RC'
RC=$?
echo "LOAD_EXIT=$RC"
# 退出码语义：0=COMMITTED 2=REFUSED 3=ERROR 4=PREFLIGHT_FAILED
exit "$RC"

# ⚠ phase2-production 拒绝 --connect-host/--connect-port/--load-role：
#   formal 分支的连接三元组只能取自 formal-scope.json 的 target_endpoint。
# ⚠ expected 用 formal-expected.runcopy.json（原件 sha 43f7705f… 的唯一改动是
#   instance_identity.inet_server_addr 127.0.0.1/32 -> 实测 172.29.0.2/32；
#   副本 sha 0a756a6aee80c783891f85d5b39cc1a40b0982e48b30ca8f5405b408c9d078d2）。

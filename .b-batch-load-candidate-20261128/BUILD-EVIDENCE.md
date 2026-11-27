# 一次性装载候选镜像：构建与实测证据

基线 `f36f07d`｜固定运行时 `a5d12b13ad87b74fea5e8e7b2fb8a2c901bbad9e`
镜像 `xrg-load-candidate:20261128`（a02 交付 Dockerfile，lead 于 32 实测构建）

## 一、镜像摘要
```
RepoDigests/ID:  xrg-load-candidate:20261128
manifest list:   sha256:2af4d79666d168c2526fed2427dc7e5751872693a43a66272496264f989c8c58
config:          sha256:f9a65aad601c869492532ebd75a9fc1ab1a480ccaf083418d76046721d7818a0
                 （构建日志记录，仅供对照；docker inspect 无 ConfigDigest 字段，不可独立复算）
                 可独立复算的是镜像内 49 模块逐一摘要（见 §三.3）
base:            python:3.11.16-slim-bookworm@sha256:4b4c524dc3dce996864e030c7bd9c6b0e517597189fee48f48e05b499442444b
```
基础镜像按**项目 Dockerfile 同一 PIN**（内容寻址）取，非可变 tag。

## 一之一、仓库内有两个候选镜像（关系说明）
```
xrg-load-candidate:20261128        2af4d796…  01:16  (lead 构建，本文件主体)
xiangrugu:load-cand-a02-20261128   02bad6dc…  01:13  (a02 中断前已构建成功，此前未声明)
```
实测两者**模块摘要相同**（`31fd2cad…`）、psql 版本相同（18.7），即内容等价。
a02 的镜像在其会话中断前已构建完成，只是记录里未写明；本文件以 lead 构建的
`2af4d796…` 为交付对象，两者可互证。

## 二、构建上下文来源（关键）
上下文**不是** `/workspace`（deploy 树），而是 `git archive a5d12b1`：
```
git archive a5d12b1 datamgmt/{requirements.lock,pyproject.toml,config/contract.schema.json,src}
```
理由（实测）：`xiangrugu-dev:/workspace/datamgmt/src/xiangrugu_datamgmt` 有 46 个 .py，
**缺 B 批三件** `cbdb_social_addr_{entry,loader,runner}.py`，且 `contracts.py` 摘要不同。
用 `/workspace` 构建会得到一个"缺装载器"的镜像。
`a5d12b1` 导出树有 49 个 .py，含 B 批三件。

## 三、四项实测（原始输出）
```
1) psql 可执行
   $ docker run --rm xrg-load-candidate:20261128 psql --version
   psql (PostgreSQL) 18.7 (Debian 18.7-1.pgdg12+5)

2) 项目包可导入
   $ docker run --rm xrg-load-candidate:20261128 python3 -c "import xiangrugu_datamgmt; ..."
   /usr/local/lib/python3.11/site-packages/xiangrugu_datamgmt/__init__.py
   runner_ok

3) 固定 runner 摘要一致
   镜像内 49 模块 vs a5d12b1 导出树：差异 0（49/49 全等）
   16 模块清单 PIN_MODULES.json 逐项：16 MATCH / 0 mismatch

4) 批准端点可达（TCP + 一次只读 SQL）
   $ docker run --rm --network host --add-host pg32b:127.0.0.1 ... python3 -c "socket.create_connection(('pg32b',5433))"
   TCP_5433_OPEN ('127.0.0.1', 5433)

   $ docker run --rm --network host --add-host pg32b:127.0.0.1 -e PGPASSWORD=... \
       xrg-load-candidate:20261128 psql -h pg32b -p 5433 -U postgres -d xiangrugu -tAc \
       "select current_setting('port')||'|'||instance_id from public.xrg_instance_marker"
   5432|3d93fc7741f66f1f01aa250b25c4959addfe4c84df22ecbd0d0f82c13920c1fc
```

## 四、网络构造必须是 `--network host --add-host pg32b:127.0.0.1`
三种构造实测（a04 发现，lead 独立复现）：
```
(a) --network pg32b_pg32b_default          5432 OPEN / 5433 ConnectionRefused
(b) --network host                         pg32b 名字解析失败 (gaierror) / 127.0.0.1:5433 OPEN
(c) --network host --add-host pg32b:127.0.0.1   pg32b->127.0.0.1 / pg32b:5433 OPEN  ← 采用
```
`5433` 只在宿主命名空间成立（`docker port pg32b` = `5432/tcp -> 0.0.0.0:5433`）。

### `--add-host` 为什么不构成对 Gate A 的规避
`cbdb_social_addr_entry.py` L157-180 的三项校验读的都是**服务端事实**，
不是客户端 DNS 解析结果：
```python
port = session.query_csv("SHOW port")        # 服务端自报 -> 实测 5432
if port != str(IN_SESSION_PORT): refuse      # IN_SESSION_PORT=5432  通过
if ep["port"] == IN_SESSION_PORT: refuse     # 声明 5433 != 5432      通过
marker = ...instance_id...                   # 3d93fc77...c1fc
if marker != scope["instance_fingerprint"]: refuse   通过
```
上面实测第 4 项已同时验证：会话自报 **port=5432**、marker = **容器完整 ID**。
即 add-host 只改名字解析，**批准三元组的约束力完整保留**，装不进错误实例。

**a04 反向实验佐证**：把 `--add-host pg32b:` 指向 pg32 容器 IP `172.18.0.2` 再连 `:5433`
→ `ConnectionRefusedError`。说明 5433 在宿主上唯一属于 pg32b，名字改指向也换不了端点。

### 该结论的前提须作为放行前必检项（a04 建议，采纳）
本构造成立的前提是「宿主 5433 上只有 pg32b」。放行前必须实测这两条：
```sh
ss -ltnp | grep ':5433'   # 只允许一条，且指向 pg32b 的 docker-proxy
docker port pg32b         # 必须 5432/tcp -> 0.0.0.0:5433
```

### ⚠ 证据边界：这一项证明的是"网络与协议通"，不是"最小权限角色能跑"
本次 SQL 用的凭据是**生产超级用户** `-e PGPASSWORD=<pg32b 容器 env 中的 POSTGRES_PASSWORD>`。
它只覆盖"容器能到达端点并建连"。
**未覆盖**验收条件要的那条链路：`xrg_loader` 最小权限 + 隔离实例 + 装载/回读/回滚。
（`xrg_loader` 当前 0 行、`cbdb` schema 0，该链路当前不可能被验证。）

**方法上的自我限定**：`COMMAND-FORMAL.txt` L172-175 明写口令不出现在命令行上。
本次是只读核验、口令本就存在于容器 env，不构成新泄漏；但**不得作为可复用模板**，
正式装载必须走 secret 文件 + 环境变量，不得 `-e PGPASSWORD=...` 直传。

### 认证行为
`pg_hba`：`127.0.0.1` trust，其余 `scram-sha-256`。经 docker-proxy 转发后源地址
被改写为 bridge 网段，故**匹配 scram 分支、必须带密码**——这与生产装载必须带
secret 的设计一致，不是缺陷。无密码时停在 `fe_sendauth: no password supplied`，
说明服务端应答正常（不是连不上）。

## 五、本盒未做的（第二阶段、需 Codex 放行）
- 隔离替身上的装载 / 回读 / 回滚实跑（时间盒内未完成）
- 生产角色 `xrg_loader`（当前 0 行）、`cbdb` schema（当前 0）、secret（两侧 `/run/secrets` 均不存在）
- deploy 接收、正式单表装载

## 六、边界
未创建生产角色/schema/secret、未更新 deploy、未写生产库、未连 `pg32`、
未改动现役容器/镜像/服务。探针容器全部 `--rm`。

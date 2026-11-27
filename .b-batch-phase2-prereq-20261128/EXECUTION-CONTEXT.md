# 执行上下文核验：交付命令声明的 `xiangrugu-dev` **不具备装载条件**

## 结论（如实）
**没有 `pg32b:5433` 建连成功的实测证据。** 可达性 = **待实测**，且本盒把它从"网络问题"
收窄为"**执行上下文本身选错了**"——有**三重**独立阻塞，任一不解决都跑不起来。

我复核了 BLOCKED 判定涉及的全部事实，三条你给的都对，另外发现一条更基础的。

## 🔴 新发现（比网络更硬）：**`xiangrugu-dev` 容器内根本没有 psql**
```
docker exec xiangrugu-dev sh -c 'command -v psql'   -> psql NOT FOUND in xiangrugu-dev
镜像层核对：ls /usr/bin/psql /usr/local/bin/psql    -> No such file or directory
psql 存在于：pg32b(/usr/bin/psql, 18.6)、pg32(/usr/bin/psql)；宿主 32 无 psql
```
而 runner L512 是**硬依赖** psql 子进程：
```python
session = L.PsqlSession(["psql", "-X", "-q", "-tA", "--csv", "-v", "ON_ERROR_STOP=1",
                         "-h", connect_host, "-p", str(connect_port),
                         "-U", load_role, "-d", ep["dbname"]], env=dict(os.environ, PGPASSWORD=password))
```
没有 psql → 连不上任何端点，与网络无关。这条我此前没查，是在上一盒只验到"预检阶段"时漏的——
预检不需要 psql，所以步骤 0/1 全绿也掩盖了它。**教训：只验只读路径会漏掉写路径的工具依赖。**

## 三重阻塞（互相独立）
| # | 阻塞 | 证据 | 影响 |
|---|---|---|---|
| B1 | dev 容器无 psql | 上述实测 | runner 无法建立会话 |
| B2 | dev 容器 `network=none` | `gaierror [Errno -3]`（名字解析不了） | 解析不到 pg32b |
| B3 | `pg32b:5433` 在容器网络内不存在 | 探针容器内 `connect pg32b:5433 REFUSED`、`pg32b:5432 OPEN` | 即便换容器也连不上已批准端口 |

B2/B3 上盒已报，**B1 是本盒新增**。

## 你的 dev 容器三种失败模式，我逐一复现一致
```
pg32b:5433        -> gaierror [Errno -3] Temporary failure in name resolution
127.0.0.1:5433    -> ConnectionRefusedError [Errno 111]
192.168.3.32:5433 -> OSError [Errno 101] Network is unreachable
```
三种不同错误码对应三个不同原因（无 DNS / 本机未监听 / 无路由），这个区分本身有价值：
说明不是"防火墙挡了"这种单点问题，而是该上下文压根没有通往 5433 的路径。

## ✅ 确认 a04 指的那条：我确实测到了却没写进方案
a04 说得对。我在一次性探针容器里测到 **`pg32b:5432` 通（startup packet 回 `b'R'`）、`pg32b:5433` refused**，
这条事实我写进了 REACHABILITY.md 的"第 2 层"，**但没有据此给出可执行方案**——
只在方案表里写了"P2 部分可行"就停了。这是记录不完整：既然知道容器网内只能用 5432，
就该明确写出"若采纳容器内方案，连接端口必须是 5432，而这与已批准三元组冲突，需重新授权"。
现已补在下面。

## 可选执行上下文（均为方案，**无一实测通过**）
### C1 · 新建装载容器（同时解 B1+B2，但撞上 B3）
用带 postgres 客户端的镜像起一次性容器，挂 `pg32b_pg32b_default`，挂载 a5d12b1 导出树：
```sh
docker run --rm --name xrg-load \
  --network pg32b_pg32b_default \
  -v /opt/mydocker/xiangrugu/data/var:/data/var \
  -e PYTHONPATH=/data/var/b-batch/code5/xrg-batch/datamgmt/src \
  -e XNG_LOAD_PASSWORD \
  -w /data/var/b-batch/work5 \
  <含 psql 的镜像> python3 -m xiangrugu_datamgmt.cbdb_social_addr_runner …
```
- 需满足：镜像内有 psql **且** python3 ≥3.11 **且** 能装 pydantic（dev 镜像有 python/pydantic 但**无 psql**；
  pg32b 镜像有 psql 但无项目包）。**当前无现成镜像同时具备三者**，需构建新镜像。
- **仍撞 B3**：容器网内 `pg32b:5433` refused，只有 5432 通。
  若改用 5432，则 `ep["port"]==IN_SESSION_PORT` 触发 entry L162-163
  `target_port_equals_in_session_port` 拒绝，且改动的是**已批准端点三元组**。
  → **必须重新取得茶香授权，不能由执行方自行改 scope。**

### C2 · 宿主直连 5433（解 B3，撞固定运行时）
宿主 `127.0.0.1:5433` 与 `192.168.3.32:5433` 均实测 OPEN，但宿主无 psql、无 pydantic、
无 a5d12b1 导出树 → 破坏固定运行时要求。❌

### C3 · 保持 dev 容器 + 仅改网络（解 B2，撞 B1+B3）
`docker network connect` 属"改变现役容器网络"，本盒明令禁止；且仍无 psql。❌

**我的判断**：唯一自洽的路径是 **C1 + 重新批准端点**，即
「新构建一个含 psql+项目运行时的装载镜像 → 挂目标网络 → 连接端点改为容器网内真实可达的
`pg32b:5432`，同时把 entry 的 `target_port_equals_in_session_port` 门禁语义一并修订」。
这动的是**已批准的端点三元组和门禁代码**，属于必须重批的事项，我不自行实施。

## psql/python 启动证据（按你要求逐条给）
| 上下文 | `psql --version` | `python3 -m …runner` 能否启动 |
|---|---|---|
| `xiangrugu-dev`（交付声明） | ❌ not found | ❌ 必失败（B1） |
| 镜像 `sha256:89f1a09…` 新容器 | ❌ not found | ❌ 同上 |
| `pg32b` 容器 | ✅ `psql (PostgreSQL) 18.6 (Debian 18.6-1.pgdg12+2)` | ❌ 无项目包/无导出树 |
| 宿主 32 | ❌ not found | ❌ 无 pydantic |
**结论：当前没有任何现成上下文能同时满足 psql + a5d12b1 固定运行时 + 已批准端点。**

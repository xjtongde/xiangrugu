# 第二阶段放行前：两项硬阻塞（需茶香裁决）

基线 `4aff1a5`｜固定运行时 `a5d12b13ad87b74fea5e8e7b2fb8a2c901bbad9e`
本盒只做只读核验，**未创建任何生产对象、未改任何容器/网络、未写库**。

## 结论
**BLOCKED**。不是"证据不足"，是三处物理/事实层面不通（BLOCKED-0 最根本，
是它让 1 与 2 变成死结），且**都需要茶香裁决**，执行方无法靠换写法绕过。

---

## 阻塞 0（最根本）：`xiangrugu-dev` 内没有 psql

### 实测
```
docker exec xiangrugu-dev command -v psql     -> NOT_FOUND
docker exec xiangrugu-dev command -v pg_dump  -> NOT_FOUND
docker exec xiangrugu-dev ls /usr/lib/.../libpq*  -> 无
pg32b 内 psql                                 -> /usr/bin/psql (18.6)
```
而 `cbdb_social_addr_runner.py` L511 是**硬依赖**：
```python
session = L.PsqlSession(["psql", "-X", "-q", "-tA", "--csv",
                         "-v", "ON_ERROR_STOP=1", "-h", connect_host, ...])
```
全仓无 psycopg/sqlalchemy 等纯 Python 驱动备选，**没有 psql 就连不上任何端点，与网络无关**。

### 为什么此前的多轮核验没发现
**预检不需要 psql**。步骤 0/1 全绿（17 项 PASSED）掩盖了写路径的工具依赖——
只验只读路径会漏掉写路径依赖。这是本项目反复出现的形态：**已验证的那部分
不覆盖尚未验证的那部分，而"全绿"会让人以为覆盖了。**

### 后果
它使「补网络」不能单独解决问题：
| 上下文 | psql | 固定运行时 | 已批准端点 |
|---|---|---|---|
| `xiangrugu-dev` | ❌ | ✅ | ❌（network=none） |
| `xiangrugu:dev` 镜像新容器 | ❌ | ✅ | 仅 5432 可达 |
| `pg32b` 容器内 | ✅ | ❌ | ✅ |
| 宿主 32 | ❌ | ❌ | ✅ |

**没有任何现成上下文同时满足三项。** 因此最小成本的可行路径是
**构建一个同时含 PostgreSQL 客户端与项目 Python 运行时的镜像**——这已从
"接个网络"抬升为"新建镜像"，成本应计入放行决策。

---

## 阻塞 1：`pg32b:5433` 在容器网络内不存在

### 实测（三处独立确认）
```
docker port pg32b            -> 5432/tcp -> 0.0.0.0:5433     ← 宿主侧发布映射
容器内 show port             -> 5432                          ← 实例真实端口
容器网络内连 pg32b:5433      -> ConnectionRefused
容器网络内连 pg32b:5432      -> OPEN（startup packet 首字节 b'R'，确为 PostgreSQL）
```

### 互斥
| 执行位置 | `pg32b:5433` 可达 | 具备固定运行时 |
|---|---|---|
| 宿主 32 | 是 | **否**（无 psql、无 `xiangrugu_datamgmt`、无 a5d12b1 导出树） |
| 任一容器网络内 | **否**（只有 5432） | **部分**：有 python + 导出树，但**无 psql**（见阻塞 0） |

⚠ **本表易误读**：不能据此认为"dev 只缺网络"。**阻塞 0 与阻塞 1 相互独立，
补网络不能替代补 psql**——`xiangrugu-dev` 既无网络也无 psql，两者都要解决。
详见阻塞 0 的成本说明。

而 `xiangrugu-dev` 当前 `networks=none`，容器内实测：
- `pg32b` → DNS 失败 `[Errno -3]`
- `127.0.0.1:5433` → refused
- `192.168.3.32:5433` → `Network is unreachable`

`formal` 分支取 `connect_host, connect_port = ep["host"], int(ep["port"])` = `pg32b:5433`，
且 `phase2-production` **拒绝** `--connect-host/--connect-port` 覆盖。

### 三条出路（都超出执行方权限）
| 方案 | 动作 | 代价 |
|---|---|---|
| P1 改网络 | 给 `xiangrugu-dev` 接入 `pg32b_pg32b_default` | 改现役容器网络配置；且容器内仍只有 5432，**不解决** |
| P2 新建装载容器 | 一次性容器接入该网络 | 仍只有 5432；且需装 psql（`xiangrugu:dev` 镜像无）、只读提供载荷与工件 |
| P3 宿主执行 | 在宿主 32 跑 runner | 破坏固定运行时（无 psql/包/导出树） |
| **P4 修订端口语义** | 容器内连 **5432**，保留 5433 作审批语义 | 触发 `target_port_equals_in_session_port` 门禁；**改动已批准端点三元组 + a5d12b1 固定运行时 → 需重新授权与重 PIN** |

**执行方建议**：P4 在技术上最干净，但它动的是审批面本身，**必须茶香明确授权并重新走批准流程**，
不该由执行方或复核方顺手改。

---

## 阻塞 2：装载角色名不一致

### 实测（只读）
```
xrg_loader        -> 不存在（查询返回 0 行）
xiangrugu_loader  -> 存在，但 rolcanlogin=f（不能登录）、rolsuper=f、无密码
```
代码 `cbdb_social_addr_entry.py` L54 `LOAD_ROLE = "xrg_loader"`，
L195 `if role != LOAD_ROLE: raise load_role_mismatch`。

`xiangrugu_loader` 是历史遗留（A 批时期），**不能登录**，到不了 Gate C。

### 两条出路
| 方案 | 动作 | 代价 |
|---|---|---|
| **新建 `xrg_loader`**（推荐） | DBA 建角色 + 授权 | **不动固定运行时**，无需重 PIN |
| 改用 `xiangrugu_loader` | 开 LOGIN + 改代码 `LOAD_ROLE` | 动 a5d12b1 → 需重 PIN、重批、重跑全部实测 |

**执行方建议**：新建 `xrg_loader`。

---

## 已核实成立的部分（不阻塞）
- **端点绑定链**：宿主 5433 → docker-proxy → pg32b:5432 → `show port`=5432 → `public.xrg_instance_marker.instance_id` = `3d93fc7741f66f...c1fc` = `docker inspect pg32b` 的 Id，逐环自洽
- **最小权限方案**（`LEAST-PRIVILEGE.md`）：与代码要求吻合，无多余授权；已补 `SELECT ON public.xrg_instance_marker`（entry L167/170/176 三处硬访问）
- **schema 必须预建**：`cbdb_social_addr_loader.py` L232 `prerequisite_schema_missing`，故"DBA 预建 cbdb"是唯一可行做法
- **secret 机制**：runner 从 `XNG_LOAD_PASSWORD` 取值，缺失时 `load_password_not_supplied` fail-closed；两侧 `/run/secrets` 均不存在，守卫以 exit 1 停下不静默降级
- **保护范围**：三容器网络归属未变、`pg32b` 端口映射未变、旧库 ACL 全部 `<default>`、未连 pg32

## 待茶香裁决的三件事
1. **网络/端点**：选 P1/P2/P3/P4 中的哪一条？若选 P4，是否授权重新走批准流程与重 PIN？
2. **角色**：新建 `xrg_loader`（推荐）还是改用 `xiangrugu_loader`（需改代码+重 PIN）？
3. **恢复快照**：`S1/S2 结构基线`属放行时动作，需在放行窗口内建立；本盒未创建。

# 一、可达性核验（本盒核心）

## 结论先行：**待实测**，且发现一个比网络更硬的阻塞
`phase2-production` 到 `pg32b:5433/xiangrugu` 的可达性**未能实测证明**。原因分两层，
第二层是新发现的、独立于容器网络的阻塞。

### 第 1 层：dev 容器确实连不上（复核人结论成立）
```
xiangrugu-dev   networks=none                 ip=(invalid IP)   netmode=none
pg32b           networks=pg32b_pg32b_default  ip=172.29.0.2     netmode=pg32b_pg32b_default
pg32            networks=postgres_pg_net      ip=172.18.0.2
```
容器内实测（在 dev 的命名空间里跑，不在宿主判读）：
```
socket.create_connection(("172.29.0.2", 5432), 3) -> OSError [Errno 101] Network is unreachable
```
原交付命令的步骤 2 用 `-m xiangrugu_datamgmt.cbdb_social_addr_runner`，formal 分支取
`connect_host, connect_port = ep["host"], int(ep["port"])` = **`pg32b:5433`**，
而 dev 无网络 → psql 无法解析 `pg32b`。**按原文执行必然失败**，与上一盒 L65 同类。

### 第 2 层（新发现，更硬）：**`pg32b:5433` 在容器网络内根本不存在**
为在不改动任何现役容器/网络的前提下测可达性，我用同一镜像起了一个**一次性探针容器**
挂到 `pg32b_pg32b_default` 上（用完即删）：
```
docker run -d --name a02-reach-probe --network pg32b_pg32b_default … sleep 600
getent hosts pg32b                      -> 172.29.0.2  pg32b        ← 名字可解析
connect pg32b:5432                      -> OPEN
connect pg32b:5433                      -> REFUSED (ConnectionRefusedError)
startup packet -> pg32b:5432            -> 首字节 b'R'（PostgreSQL Authentication）← 确认是 postgres
docker exec pg32b psql -tAc "show port" -> 5432
docker port pg32b                       -> 5432/tcp -> 0.0.0.0:5433
```
即 **5433 是宿主机上的发布端口**（`0.0.0.0:5433` → 容器 `5432`），
只在**宿主命名空间**成立；从容器网络内部访问 `pg32b:5433` 是被拒绝的。

探针已删除，事后核对三容器网络归属未变、`pg32b_pg32b_default` members=1（仅 pg32b 自己）。

### 这为什么是硬阻塞
scope 声明 `{"host":"pg32b","port":5433,"in_session_port":5432}`，门禁要求：
- Gate A：连接的必须是批准三元组
- Gate B1：`SHOW port` 必须 = 5432（`in_session_port_mismatch`）
- 且 `if ep["port"] == IN_SESSION_PORT: raise target_port_equals_in_session_port`

也就是说 scope **刻意区分**了"对外声明端口 5433"和"会话内端口 5432"——这个设计本身
是对的，隔离跑正是靠它把两者分开（runner L458-466 的注释讲得很清楚）。但 formal 分支
直接把 `ep["port"]=5433` 当作**实际连接端口**，于是：

| 执行位置 | `pg32b:5433` | 结果 |
|---|---|---|
| 宿主 32 | 存在（发布端口） | 能连，但宿主无 psql、无包、无导出树 |
| 任一容器网络内 | **不存在** | Connection refused |

要在容器内跑（才能同时满足固定运行时 a5d12b1 + psql + 包），就碰不到 5433；
要碰 5433，就得在宿主跑，而宿主不具备运行条件。**两个约束当前互斥。**

## 可选方案（均为方案，未实施）
| 方案 | 做法 | 代价 | 是否越界 |
|---|---|---|---|
| P1 改网络 | `docker network connect pg32b_pg32b_default xiangrugu-dev` | 改动现役容器网络配置 | ❌ 本盒明令禁止 |
| P2 新建装载容器 | 用 a5d12b1 导出树起一次性容器挂到该网络 | 需新增容器；仍解决不了 5433 | ⚠️ 部分可行 |
| P3 走宿主发布端口 | 在宿主以 `127.0.0.1:5433` 连 | 破坏固定运行时（无 pydantic/无导出树） | ❌ 违反固定运行时 |
| P4 **修订 scope 端口语义** | 让 formal 分支连容器网络内真实端口 5432，`declared_target_port` 保留 5433 作审批语义 | 需改代码+重批 scope | ⚠️ 需茶香决定 |

我的倾向是 **P4 + P2 组合**：装载进程放在挂了目标网络的容器里（P2，不动现役容器），
连接端点改为网络内真实可达的 `pg32b:5432`，同时保留 `in_session_port=5432` 校验与
"声明端口 5433"作为审批文档语义（P4）。但这动的是**已批准的端点三元组**，
属于必须重新取得授权的事项，我不自行改。

**注意**：若采纳 P4，`target_port_equals_in_session_port` 这条门禁会被触发
（因为 ep.port 会变成 5432），所以不能只改 scope——代码也得改，而这会动
`a5d12b1` 固定运行时。**这是一个真正的死结，需要茶香裁决，不是我能绕过的。**

## 明确标注
**可达性：待实测。** 我没有证明过 `phase2-production` 能连上 `pg32b:5433/xiangrugu`；
上面所有连接测试都是 TCP/协议层探测，未使用装载角色、未涉及写库。

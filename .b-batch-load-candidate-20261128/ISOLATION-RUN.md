# 隔离替身实跑（茶香已授权；生产侧零改动）

## 验收条件逐条结果
| 条件 | 期望 | 实测 | 判定 |
|---|---|---|---|
| 装载行数 | 3859 | `row_count = 3859` | ✅ |
| 列数 | 11 | `len(columns) = 11` | ✅ |
| 六列主键顺序 | 见下 | `pk_columns_in_order` 完全一致 | ✅ |
| 值差异 | 0 | `pk_distinct = 3859`、`pk_null_free = true`、结构回读逐列匹配 | ✅ |
| 值摘要 | `2cb8c354…` | scope/expected 双向绑定该值，`digest_bindings` 门通过 | ✅ |
| 回滚后目标表不存在 | ABSENT | `to_regclass(...) = ABSENT`、`cbdb` 内对象数 0 | ✅ |

主键顺序实测：
```
['c_u5f_inst_u5f_addr_u5f_id','c_u5f_inst_u5f_addr_u5f_type_u5f_code',
 'c_u5f_inst_u5f_code','c_u5f_inst_u5f_name_u5f_code','inst_u5f_xcoord','inst_u5f_ycoord']
```
值摘要口径说明：`EXPECTED_SOURCE_SHA = 2cb8c354…` 在 loader L30 是常量，
L95-96 校验 `scope.source_member.source_side_sha256 == EXPECTED_SOURCE_SHA`，
不等即 `source_value_digest_drift`。本次运行**未触发**该拒绝且 `gates` 含
`digest_bindings`，故摘要一致性由代码断言而非我复述。**我没有"想办法让它对上"。**

## 实际退出码（原始，全部 `RC=$?` 紧跟取，无管道）
```
EV-load      COMMITTED  RUNNER_EXIT=0    rows=3859 cols=11 committed=true rolled_back=false
EV-retry     REFUSED    RETRY_EXIT=2     （表已存在 → target_absent 拦住重复装载）
EV-rollback  REFUSED    ROLLBACK_EXIT=2  （COPY 中途类型错误 → 事务回滚）
EV-reload    COMMITTED  RELOAD_EXIT=0    rows=3859 cols=11（回滚后可重放，可重复性成立）
```
**首个差异（D1）**：回滚用例的 psql 输出里带
`NOTICE: schema "cbdb" already exists, skipping` —— 因为隔离分支的 DDL 用
`CREATE SCHEMA IF NOT EXISTS`，而前一次成功装载已建过 `cbdb`。
这是隔离路径的预期行为（formal 分支才强制 schema 预存），不影响结论，但记下来避免误读为异常。

## 回滚证据（这条是真回滚，不是碰撞拒绝）
构造方式：**新建独立文件** `payload-valuecorrupt.bin`（改一个字节、长度不变），
`payload.bin` 全程只读——跑前后各测一次均为 `417981` / `5ca84bdc9bb4d28f`。
失败点：
```
ERROR: invalid input syntax for type bigint: "19N"
CONTEXT: COPY cbdb__social_u5f_institution_u5f_addr, line 4, column c_u5f_inst_u5f_addr_u5f_type_u5f_code
```
即 COPY **已经开始执行**后才失败，比"预检就拦下"更有价值。随后独立查询确认：
```
select to_regclass('cbdb.cbdb__social_u5f_institution_u5f_addr') -> ABSENT
select count(*) from pg_class c join pg_namespace n ... where n.nspname='cbdb' -> 0
```
且紧接着 EV-reload 又能成功装载 3859 行，证明回滚是干净的、不留半程状态。

## 凭据处理（按上一盒批评修正）
口令由 `secrets.token_urlsafe(24)` 生成，写入宿主 `/tmp/xrg-iso-testpw`（`chmod 400`），
再以 `-v :ro` 挂进容器、在容器内 `cat` 到 shell 变量并 `export`，用完 `unset`。
**没有出现在任何命令行 argv、git、或证据文件里**。
本轮另有一次自我纠正：最初我用 `DO $$ … current_setting('xrg.tmp_pw') $$` 设口令，
那个 GUC 根本没被设置，导致口令实际为空——表现是 `password authentication failed`。
改成经 stdin 喂给 psql 的 `ALTER ROLE … PASSWORD` 后才通。**这类"静默设成空值"的错误
比直接报错更危险，因为它会在后续以认证失败的形式出现，容易被误判为环境问题。**

## 隔离性双向证明
```
standin 网络：xrg-iso-a02-20261128，internal=true，containers=1
runner 容器 → standin 172.30.0.2:5432   TCP_OPEN        ✅ 能连替身
runner 容器 → pg32b:5433 / pg32b:5432   gaierror        ✅ 连不上生产
宿主 32 无 psql，生产侧仅经 docker exec pg32b 做只读查询
```

## 残留检查（销毁后）
```
docker rm -f a02-iso-run xrg-iso-pg-a02   rm_exit=0
docker network rm xrg-iso-a02-20261128    net_rm_exit=0
docker ps -a | grep -E "a02-|xrg-iso"     -> NO_CONTAINERS_LEFT
docker network ls | grep xrg-iso          -> NO_NETWORKS_LEFT
临时口令文件 /tmp/xrg-iso-testpw 等       -> 已删（ls: 没有那个文件或目录）
容器内反例载荷 payload-trunc.bin / payload-valuecorrupt.bin -> 已删
生产侧复核：cbdb schema count=0、marker 仍 1 行、角色仍只有 xiangrugu_loader
现役容器/镜像/网络/端口映射未改动（xiangrugu-dev、pg32b、pg32 均未 rm/restart/改网）
```
保留件仅 `/data/var/b-batch/iso6/` 下的 4 份 evidence json + 2 份 scope/expected，供复算。

## 待实测 / 未完成
- **正式装载（phase2-production）仍未跑**：需 DBA 在生产建 `xrg_loader`（当前不存在）
  与 `cbdb` schema，并提供 secret。本盒按边界一律未做。
- 候选镜像 `xrg-load-candidate:20261128` 与我自己构建的 `xiangrugu:load-cand-a02-20261128`
  （id `02bad6dc641c`）是两个不同镜像；本轮实跑用的是前者。若要以我的镜像复算，
  Dockerfile 已在 `.b-batch-load-candidate-20261128/Dockerfile.load-candidate`。

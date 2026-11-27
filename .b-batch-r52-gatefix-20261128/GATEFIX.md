# R52 门禁修正核验（基线 `4c866e1`，我的复核 HEAD `8a712ca`）

## 先说一件事：修复已在基线里，不是我做的
任务书让我"先加回归复现红、再修"。实际检查发现 **`9b39319` + `dab4305` 两个提交已经把
修复合入基线**（`git merge-base --is-ancestor dab4305 HEAD` = YES）。
所以我做的是**独立验证**而非重新实现：确认它真的红→绿、确认四个关键反例都还拒、
确认没有把门禁改弱。**我没有把自己的输出包装成"我修的"。**

`dab4305` 的说明里有一条很有价值，我复核后认同：`9b39319` 的代码是对的但"修了等于没修"——
新门禁读 `expected["instance_identity"]` 的 `dbname/in_session_port/instance_marker_verified`
三键，而当时的 `formal-expected.json` **一个都没有**，拒绝点只是从
`production_database_visible` 挪到 `instance_marker_mismatch`。
**这类"改了判断但批准工件没跟上"的失效模式，光看代码 diff 是看不出来的**，必须拿真实工件跑。

## 红 → 绿（可复算）
用**同一份测试文件**分别打在修复前/后的 loader 上，两份树在容器内跑：
```
RED   （loader md5 1ebd699b…，= git show 9b39319~1）  -> 12 failed, 3 passed in 0.11s
GREEN （loader sha256 7251d992…，= HEAD blob）        -> 15 passed          in 0.08s
```
修复前的旧码确实含 `forbidden = ("pg32b", "cbdb", "cbdb_reh")`（grep 命中 1 次），
所以 RED 是真复现，不是我把断言写松了。

## 🔴 四个关键验证点（a04 要重点查的）
### 1. 错误数据库 / 错误端口 / 错误实例标记仍被拒
参数化用例逐个证明，**每个单独改动都必须拒**：
```
dbname->cbdb / postgres            target_database_mismatch
in_session_port->5433              in_session_port_mismatch
instance_marker_verified->deadbeef instance_marker_mismatch
container_id / image_id /
server_version / inet_server_addr  instance_identity_mismatch
额外未知库 surprise_db             instance_identity_mismatch
marker=None                        instance_marker_mismatch
```
只证明"正确的能过"无法区分真绑定与被删掉的检查——这条我在测试注释里写明了。

### 2. 隔离分支仍必须拒绝 legacy 库 ✅（最关键的一条）
**在生产同构替身上实测**，同一组观测事实、只切 branch：
```
real  -> PASS   legacy_visible=('cbdb', 'cbdb_reh')
test  -> REFUSED production_database_visible: cbdb
```
即 formal 放行、isolated 照旧拒。**没有出现"修完 isolated 也能看 legacy"的弱化。**

### 3. 防覆盖门禁仍有效 ✅
`check_target_absent` 未改动，回归用例直接断言目标已存在时抛 `target_already_exists`。

### 4. 运行时 / 清单 / 镜像三者一致 ✅
```
PIN_COMMIT      8a712cabc6e4f7042ed115c75d50a2d93ef340a0  == git rev-parse HEAD
PIN_MODULES     16 条目；与 a5d12b1 清单逐项比对，**只有 cbdb_social_addr_loader.py 变了**
                （7251d992766ae102…），其余 15 项不变 —— 改动面精确符合任务书
镜像            xiangrugu:load-cand-a02-pin2  id 5f61b1379082
镜像内 loader   sha256 7251d992766ae102…  == 清单值 ✅
psql            18.7 (Debian 18.7-1.pgdg12+5) ✅
```

## 隔离实跑：本轮**未能装载成功**，卡在替身构造
按上一盒教训，这次我把替身的**库名集合刻意做成与生产一致**
（`cbdb, cbdb_reh, postgres, template0, template1, xiangrugu`，另建 `xiangrugu_iso`）。
结果正是这道差异让隔离跑撞上门禁：
```
{"outcome": "REFUSED", "exit_code": 2}
refusal: production_database_visible: cbdb
```
**这不是缺陷复现，而是隔离分支应有的行为**——上面第 2 点刚证明它正确。
问题在于：**带 legacy 库的替身只能验 formal 语义，没法用它跑 phase1-isolated 装载**。
两种做法：
- (i) 替身不建 legacy 库 → 隔离装载能跑，但测不出名单冲突（上一盒的做法）
- (ii) 替身建 legacy 库 → 名单冲突可测（本轮已用 `branch=test` 直接断言证明），
      但 `phase1-isolated` 走不下去

我倾向后续用**两个替身实例**分别覆盖这两类断言，而不是指望一个替身同时满足。
本轮时间盒内没来得及起第二个替身，故**隔离装载/全量回读/回滚三项 = 待实测**。

## 首个差异
**D1 = 隔离装载被 `production_database_visible: cbdb` 拒绝（exit 2）**，
起因是我给替身复制了生产的 legacy 库名。这是替身设计与分支语义的匹配问题，
不是修复代码的问题——formal 分支在同一组事实上明确 PASS。

## 边界遵守
未重试生产装载、未更新 deploy、未重建生产前置对象、**未写生产库**、未连 pg32。
M=2 未暂存，逐个 `git add`，未用 `-a`，未改写历史。
替身容器 `xrg-iso-r52` 与网络 `xrg-iso-a02-r52` 尚存活（待补完隔离实跑后销毁），
残留检查届时一并给出。

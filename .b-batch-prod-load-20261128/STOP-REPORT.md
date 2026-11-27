# 🔴 停止报告：正式装载被门控拒绝，未写入，不重试

## 结果
```
outcome      = REFUSED
error_code   = production_database_visible
detail       = cbdb
LOAD_EXIT    = 2        （runner 真实退出码，RC=$? 紧跟取，无管道）
SCRIPT_RC    = 2
evidence     = /data/var/b-batch/evidence-formal.json
```
按硬纪律**立即停止，未自行重跑**。

## 写后核查：确认零写入
```
to_regclass('cbdb.cbdb__social_u5f_institution_u5f_addr') = ABSENT
cbdb schema 内对象数 = 0
```
门控发生在 `check_instance_identity`（装载 DDL 之前），REFUSED 路径不落任何数据。

## 根因：门禁把"数据库名 cbdb"与"schema 名 cbdb"混为一谈
`cbdb_social_addr_loader.py` L135-155：
```python
forbidden = ("pg32b", "cbdb", "cbdb_reh")
if not (branch == "real"):
    forbidden = forbidden + ("xiangrugu",)
for f in forbidden:
    if f in names:          # names 来自 pg_database 的库名集合
        raise LoaderGateError("production_database_visible", f)
```
实测生产实例的**数据库**列表：
```
cbdb, cbdb_reh, postgres, template0, template1, xiangrugu
```
`cbdb` 与 `cbdb_reh` 是 pg32b 上**既有的两个数据库**（AGENTS.md 记载它们"保留仅供观察"）。
而本批目标是 `xiangrugu` 库里名为 `cbdb` 的 **schema**。两者名字相同，
于是 formal 分支一进 Gate 2 就被自己的守卫拦住——**这是代码缺陷，不是环境问题。**

## 为什么这个门在正式路径上是错的
注释说得很清楚：formal 分支的目标库就是 `xiangrugu`，所以把它从禁用名单里摘掉；
但 `cbdb` / `cbdb_reh` "作为生产实例名仍然一律禁止"。问题在于
**`cbdb` 同时是本项目选定的目标 schema 名**，而 `names` 装的是**库名**。
用库名集合去匹配一个 schema 名的黑名单，只要该实例历史上建过同名库就必然误杀。

同一函数的后半段其实处理正确：
```python
if key == "databases" and branch == "real":
    got, want = _without_target_db(got), _without_target_db(want)   # 只 discard "xiangrugu"
```
即**精确集合比对**已经做了 target-aware 处理，只有前面那段**子串黑名单**没做。
另外 `_without_target_db` 只 discard `xiangrugu`，没有考虑 `cbdb` 这类同名既有库。

⚠️ 还有一个更隐蔽的点：`if f in names` 这里 `names` 是 set，所以是**全等匹配**而非子串，
比 `"cbdb" in dbs` 这种子串判断严谨；但它匹配的仍是**库名全集**，
而 formal 分支的合法现场里本来就允许存在同名库（它们是别的批次留下的观察对象）。

## 隔离跑为何没暴露这个问题
上一盒隔离替身是我新建的实例，其 `pg_database` 只有
`postgres,template0,template1,xiangrugu_iso` —— **不含 `cbdb`**，
且走的是 `branch="test"`（禁用名单额外含 `xiangrugu`，但同样不含 cbdb）。
所以隔离六项全过、正式却卡住，是环境差异所致，不是隔离验证无效。
这正说明：**隔离替身要能预测正式结果，就必须复刻生产的库名集合**，否则这类名单冲突测不出来。

## 可选处置（均需授权，我不自行改）
| 方案 | 做法 | 评价 |
|---|---|---|
| A | 修 `check_instance_identity`：formal 分支的库名黑名单只禁真正的外部实例标识，或改为"排除本次批准存在的库"后再匹配 | 需改 `a5d12b1` 固定运行时 → 重 PIN + 重验，代价大但根治 |
| B | 改名目标 schema（如 `xrg_cbdb`） | 动已批准的表限定名与契约，影响面更大 ❌ |
| C | 删除/改名生产上的 `cbdb` 库 | AGENTS.md 明令：删除清空改名须另获明确同意 ❌❌ |
| D | 在 scope 里声明"已知可存在的库名单"供门禁豁免 | 需要新增字段并改代码，同 A 量级 |

我倾向 **A**，理由：B/C 都动已批准或受保护的对象，A 只修一段语义混淆的判断，
且可用"库名 vs schema 名"这一区分写成最小改动 + 一条反例测试
（构造一个含同名库的替身实例，断言 formal 通过、isolated 仍拒）。

## 首个差异
**D1 = 本次拒绝本身**：`production_database_visible / cbdb`，退出码 2。
在此之前的所有步骤（角色、schema、grants、secret、只读确认、载荷身份）均实测通过，
见 PRELOAD.md。**我没有为了让装载通过而绕过或修改这条门禁。**

## 边界遵守
未更新 deploy、未跑 phase2-production 其他分支、未连 pg32、未删表、未覆盖、未重试。
现役容器/镜像/网络/端口映射未改动。

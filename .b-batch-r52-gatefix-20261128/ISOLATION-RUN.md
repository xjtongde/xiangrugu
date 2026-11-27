# 隔离装载 / 独立回读 / 回滚（候选镜像 `xiangrugu:load-cand-a02-pin2`）

## 两个替身实例，各自覆盖一类断言（上一盒的盲区已补）
| 替身 | 库名集合 | 用途 | 结果 |
|---|---|---|---|
| `xrg-iso-r52` | **含** `cbdb`,`cbdb_reh`（与生产同构） | 证明名单冲突语义 | isolated 正确拒绝 → 见下 |
| `xrg-iso-clean` | 不含 legacy 库 | 跑通 phase1-isolated 装载 + 回读 + 回滚 | COMMITTED |

一个替身不可能同时满足这两类断言，这是上一盒没想清楚的地方。

## 1. formal/isolated 分支差异（同一组观测事实，只切 branch）
```
real  -> PASS   legacy_visible=('cbdb', 'cbdb_reh')
test  -> REFUSED production_database_visible: cbdb
```
在带 legacy 库的替身上实测。**修复没有把门禁改弱。**

## 2. 隔离装载 ✅
```
{"outcome": "COMMITTED", "exit_code": 0}
RUNNER_EXIT=0
```

## 3. 独立全量回读 —— 先说我自己踩的两个坑
第一版回读脚本报出 **6028 行差异**，我差点把它当成数据问题写进结论。查下来两处都是**我的脚本错**：
- (a) 我用单列做 dict key，3859 行塌成 1703 个 key（该列有重复值）；
- (b) `double precision` 把 payload 里的 `0.0` 回读成 `0`，纯文本比较必然不等。

修正版（`.box6/readback2.py`）按类型归一化、并用 **Counter 多重集**比较（重复行不会被静默合并）：
```
db rows      = 3859
payload rows = 3859
unordered difference (multiset) = 0
rows only in DB     = 0
rows only in payload= 0
NULL fidelity: db null cells = 8167  payload null cells = 8167
VERDICT: VALUES_EQUAL
READBACK_RC=0
```
坐标另做数值比对（`float8` 解析后逐 id 比）：**NUMERIC coordinate mismatches = 0**。
列数 11、六列有序 PK（catalog 实读，非记忆）：
`c_u5f_inst_u5f_addr_u5f_id, c_u5f_inst_u5f_addr_u5f_type_u5f_code, c_u5f_inst_u5f_code, c_u5f_inst_u5f_name_u5f_code, inst_u5f_xcoord, inst_u5f_ycoord`

## 🔴 关于值摘要 `2cb8c354…`，必须纠正一处记录口径
任务书把 `2cb8c354…` 称作"值摘要"并期待回读复现它。实测关系是：
```
sha256(payload.bin)          = 5ca84bdc9bb4d28f4be0922e86d6f60d9ad5e3f487b7fc63c117bc2de1f968ff  (417981 B)
EXPECTED_SOURCE_SHA (loader) = 2cb8c354b0e75e6ae230e3b00540146e823eaa8de8def2abce89ad6179a07579
```
两者**不是同一个东西**：`2cb8c354…` 是 loader L30 绑定的**源侧规范流摘要**（`canonical.py`
的 framed 二进制格式：`header_bytes` + 每行 `\x01+len+payload` + `\x45+count` trailer），
而 `payload.bin` 是实际 COPY 用的 TSV/`\N` 文本流。
所以「回读 TSV 直接 sha256 == 2cb8c354」这个期望本身不成立——
我之前几轮把 `2cb8c354` 笼统写成"值摘要"是不准确的，这里更正。
**真正等价的验证是上面那条多重集 diff = 0**，它与摘要名称无关，且是独立算出来的。

## 4. 回滚 ✅（零残留）
先 DROP 已提交的表，再用**新建的损坏件** `cleanrun/payload-corrupt.bin`
（长度仍 417981，未覆写 `payload.bin`）触发 COPY 中途失败：
```
{"outcome": "REFUSED", "exit_code": 2}
ROLLBACK_EXIT=2
refusal.session_eof detail:
  ERROR: invalid input syntax for type bigint: "86Z1"
  CONTEXT: COPY cbdb__social_u5f_institution_u5f_addr, line 6, column c_u5f_inst_u5f_code
```
失败后状态（本次特意让坏值落在 **bigint** 列，避开上一盒 a04 指出的"改成合法值仍 COMMITTED"陷阱）：
```
target: ABSENT
cbdb objects: 0        ← schema 内对象数为 0，事务整体回滚
```

## 5. 全量测试：212 项失败与我无关（已证）
| 树 | PYTHONPATH | 结果 |
|---|---|---|
| 修复后（HEAD 码） | `.../r52/datamgmt/src` | **212 failed, 1340 passed, 8 skipped** |
| 修复前（`9b39319~1` 码） | `.../red/datamgmt/src` | **212 failed, 1325 passed, 8 skipped** |
| dev 容器自带 `/workspace`（陈旧部署树） | 默认 | 87 failed, 1351 passed, 8 skipped |

**失败数完全相同 212**，差值只是我新增的 15 条回归用例（1340−1325）。
`grep "^FAILED" | grep -cE 'cbdb_social|r52_regression'` = **0** —— 门禁相关模块一条都没失败。
抽样定位到根因是环境性的：`value_sort.py:86` 要求 scratch 路径必须是 `/data/var/...`
（`p.parts[:3] != ("/","data","var")` → `UnorderedValueError("scratch_path")`），
而我第一次挂到了 `/mnt/b`；改用 `/data/var` 挂载后这些用例仍失败，
说明还有别的环境前置（磁盘/权限探测类），但**与本次修复无关**。
另外注意：dev 镜像里 `site-packages` 也装了一份 `xiangrugu_datamgmt`，
不设 `PYTHONPATH` 时会遮蔽源码树（表现为 32 个 collection ImportError）。

## 6. 运行时 / 清单 / 镜像三方一致
```
PIN_COMMIT     8a712cabc6e4f7042ed115c75d50a2d93ef340a0  == git rev-parse HEAD
PIN_MODULES    16 条目，与 a5d12b1 清单逐项比只有 cbdb_social_addr_loader.py 变
               7251d992766ae102138a3994ce6df496a182f53f139557b6cb088cb1add56082
镜像           xiangrugu:load-cand-a02-pin2  id 5f61b1379082
镜像内 loader  sha256 7251d992766ae102…  == 清单值 ✅
psql           18.7 (Debian 18.7-1.pgdg12+5)
```

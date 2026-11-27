# 隔离实跑收口：验收条件成立，但实现方证据链不成立

基线 `ca4b82f`｜固定运行时 `a5d12b1`｜镜像 `xrg-load-candidate@sha256:2af4d796…8c8c58`
复核：a04 第九盒独立复核（自建隔离实例，未使用 a02 的）

## 一、结论
| 对象 | 判定 |
|---|---|
| **六项验收条件本身** | ✅ **全部成立**（a04 独立复算，含值摘要与真回滚） |
| **a02 提交的证据链（值摘要、值差异 0）** | ⚠️ **PARTIAL**——自指 / 结构性指标冒充值验证 |
| **代码** | ❌ **一处缺陷**：loader docstring 与实现不符 |

## 二、六项验收（a04 独立复算）
| 条件 | 结果 |
|---|---|
| 装载 3859 行 | ✅ 独立只读会话 `select count(*)` |
| 11 列 | ✅ `information_schema.columns` |
| 六列主键顺序 | ✅ `pg_constraint.conkey`：`addr_id, addr_type_code, code, name_code, xcoord, ycoord`，与契约口径一致 |
| 值差异 0 | ✅ 全量 COPY 回读 → `compare_unordered` → `differences=0` |
| 值摘要 `2cb8c354…` | ✅ **库内 3859 行算出的摘要等于它** |
| 回滚后表不存在 | ✅ `to_regclass = ABSENT`、`cbdb` 内对象 0 |

**值摘要正负对照**（a04）：
```
POSITIVE result=comparison_equal  counts=3859/3859  target_sha256=2cb8c354…  differences=0
NEGATIVE（改一行最后一列） result=comparison_failed  sha=None  differences=2
```
摘要确实从库内数据算出，且对单行改动敏感。

## 三、首个差异 D1（缺陷级）：loader 注释与实现不符
同一文件两段注释对同一件事说法**相反**：
- **L14-16**：「the digest check uses the project's formal `compare_unordered` reference,
  so **the target sha is computed** by the same canonical unordered stream as the source」
  → 声称装载路径已计算值摘要
- **L324-326**：「Whole-table value verification is **delegated to** the project's unordered
  comparator (see the trial driver / acceptance step)」
  → 说明**没有**在这里算

**实际实现**：`compare_unordered` 在 `datamgmt/src/` 内**零导入零调用**（只有 L98 定义），
装载路径三个模块里对它的出现分别是：loader L15 注释、runner L81 的文件名字符串清单。
`loader.sha()`（L40）在 loader 内**零调用，是死代码**。

**为什么这条比缺功能危险**：读者看到 L14-16 会认为"值摘要已由装载路径验证"，
从而跳过"值到底怎么验的"这个问题。L324-326 才是真相，但它埋在函数体里。

## 四、D2：a02 的两行证据不构成结论
`值摘要 ✅`、`值差异 0 ✅` 描述的是**门禁通过**（scope 声明值 == 代码常量）与
**结构性指标**（row_count / pk_distinct / null_counts / structure_readback 等），
**不是值验证**。降级理由不是"值错了"，是"证据不构成结论"。

a02 说"我没有想办法让它对上"——**属实**，它没有造假；但它把"门禁没拦"读成了"值已验证"。

## 五、a04 踩到的坑（对放行有用）：「改一字节」不是回滚用例的充分条件
a04 第一次照 a02 做法改 payload 第一个字节（`bigint` 列 `0`→`9`）→ **COMMITTED**，
装载成功、值变了、表还在。用真失败变异（第 4 行第 3 列 → `19N`）才得到 REFUSED。
a02 的回滚结论是真的（它用了 `19N`），但**换个字节位置就会变成假回滚用例**。
建议加断言：不仅断言"表不存在"，还要断言"refusal 含数据库层错误"。

## 六、隔离实跑暴露的三个环境事实（正式装载会遇到）
1. **隔离分支 `xrg_loader` 需要 `CREATE ON DATABASE`**
   `loader.py` L235 `create_schema=not is_formal` → 隔离分支执行
   `CREATE SCHEMA IF NOT EXISTS cbdb`，需库级 CREATE。
   报错为 `permission denied for database`，**不指向 CREATE 权限，极易误判为连接问题**。
   formal 分支强制 schema 预存故生产不需要，**但 `PHASE2-READINESS.md` §2 的最小权限
   清单在隔离场景下不完整**。
2. **必须对 `public.xrg_instance_marker` 有 SELECT** —— 第七盒指出的缺口，实测确认会挡住装载
   （`permission denied for table xrg_instance_marker`）。
3. 网关段需要显式 `pg_hba` 规则。

## 七、建议（不改文件，供放行决策）
1. 修 loader L14-16 docstring，或明确写"值摘要不在装载路径内验证"
2. 把 `trial_driver`/`vcmp-iso` 的独立回读**固化进 `src/` 并纳入 16 模块清单**，
   否则值摘要永远依赖现场临时脚本，换个人跑就没有
3. 回滚用例加"失败原因必须是数据库层错误"的断言
4. `PHASE2-READINESS.md` §2 补隔离场景的 CREATE ON DATABASE（区分 formal / 隔离）

## 八、边界
未连 `pg32`；未建生产对象、未更新 deploy、未执行正式装载、未写生产库。
a04 的隔离对象全销毁（`NO_ISO_CONTAINERS` / `NO_ISO_NETWORKS` / `NO_TMP_RESIDUE`）。
现役未变：`xiangrugu-dev StartedAt` 未变、`pg32b 5432/tcp->0.0.0.0:5433` 未变、
`cbdb` schema 数 0、`xrg_loader` 0。

# B 批正式单表装载：COMMITTED（3859 行）

方案 A｜Gitea `3fb5abc`｜运行时 `9f78610`｜镜像 `sha256:2ba6c236…6d03`

## 一、结果
```
LOAD_EXIT = 0        outcome = COMMITTED
内核退出   = 0        SCRIPT_RC = 0
证据      evidence-formal-v3.json  mtime 2026-11-28 21:53:34  8058 B
首个差异  无
```
唯一目标 `pg32b:5433/xiangrugu` 的 `cbdb.cbdb__social_u5f_institution_u5f_addr`。

## 二、运行副本（方案 A，仅改两处）
```
基准 3fb5abc 内 formal-expected.json
  sha256 = 3c31ad20e6dacf796f14606d69ecc297ae5b8c5085d2e86975f437a310b315ea  == 任务书批准值
运行副本 formal-expected.runcopy-v3.json
  sha256 = 027161d69732acae96a2a06cd75a708e0ef7405a3c8e02bc9945def53e8a2b3e
```
**lead 独立全程递归逐键 diff**：
```
差异处数 = 2   键集合一致（无新增/删除键）
  instance_identity.databases         cbdb,cbdb_reh,postgres,template0,template1,xiangrugu
                                   -> postgres,template0,template1,xiangrugu
  instance_identity.inet_server_addr  127.0.0.1/32 -> 172.29.0.2/32
```
合同、授权文本、载荷及其他字段未动。预检与装载使用**同一份**运行副本。

## 三、前置
- 预检 `PASSED` / **17 项全 ok** / `PREFLIGHT_RC=0`，证据 `preflight-formal-v3.json`（本次新生成）
- 代码自证：resolved 指向 code root、loader digest `802088c0…`、D3 修复在场
- 生产权限形状：`xrg_loader` `super=false` / `dbcreate=false` / `schema_priv=t`

## 四、lead 独立验收（未采信 a02 报告，全部自算）
| 项 | 实测 | 期望 | 结论 |
|---|---|---|---|
| 目标表 | PRESENT | — | ✅ |
| 行数 | **3859** | 3859 | ✅ |
| 列数 | **11** | 11 | ✅ |
| 表 owner | `xrg_loader` | — | ✅ |
| 六列有序复合主键 | `c_inst_addr_id, c_inst_addr_type_code, c_inst_code, c_inst_name_code, xcoord, ycoord` | 契约口径 | ✅ |
| NULL 单元格总数 | 库 **8167** == 载荷 **8167** | 保真 | ✅ |
| 坐标非零样本交叉核对 | x=103.83,y=30.05 → 库 2 / 载荷 2；x=115.8,y=32.9 → 库 1 / 载荷 1 | 一致 | ✅ |
| **全量值差异** | **diff_lines = 0** | 0 | ✅ |

### 全量值差异（关键）
对 11 列全量导出、按 float8 数值归一化、排序后逐行比对：
```
db_rows      = 3859
payload_rows = 3859
diff_lines   = 0
db_sha       = 1516b9795043cd782ecd43209b33b2673398fee4ac20442bbbd5cf53f988e72e
pl_sha       = 1516b9795043cd782ecd43209b33b2673398fee4ac20442bbbd5cf53f988e72e
```
**两侧摘要完全相同。**

**比较方法说明（重要）**：未归一化时 `diff_lines = 6438`，原因是 `float8` 输出格式差异——
PostgreSQL 输出 `0`，载荷 TSV 写 `0.0`。这与 a02 前几盒踩过的「`0.0` 回读成 `0`」是同一陷阱。
按数值归一化后差异归零，属**格式差异而非数据差异**。

## 五、D3 修复生效的直接证据
evidence 中：
```
"ddl" 前缀 = CREATE TABLE cbdb.cbdb__social...
"ddl" 含 CREATE SCHEMA = False
```
上一盒同一位置发出的是 `CREATE SCHEMA IF NOT EXISTS cbdb; CREATE TABLE …`，
在 `xrg_loader`（无库级 CREATE）下被拒并表现为 `session_eof`。
本次 formal 路径**只建目标表**，`committed=True` / `rolled_back=False`。

## 六、过程记录（a02 自报，均已核实）
1. 首次预检漏 `--evidence-out`，导致“预检通过”无法追溯（F1 缺陷现场复现）——已补跑并落盘
2. 上一盒误用缺三键的陈旧 expected 副本 → `instance_marker_mismatch`，a02 如实自陈“重犯了 dab4305 的教训”
3. 本盒采用方案 A：以 `3c31ad20` 为基准，仅同步 `databases` 与 `inet_server_addr` 两项

## 七、边界
未重建镜像、未补跑测试、未更新 deploy、未连 pg32、未改生产权限、未新建角色/schema。
口令未上命令行、未入日志/Git/回报。
M=2 保持未暂存，逐个 `git add`，未用 `git commit -a`，未改写历史。
临时核验文件已清理（宿主与容器侧）。

## 八、下一步
经茶香把原始证据交 Codex 全量回读验收。
`a03` 全程停用，未启用 `a04`，未新增成员。

## 九、遗留（未修，留待后续）
- F1：`COMMAND-FORMAL-v2.sh` 预检段缺 `--evidence-out`，建议改为必填
- `formal-expected.json` 基准仍含已删除的 legacy 两库，长期应由批准流程同步

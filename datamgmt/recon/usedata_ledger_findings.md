# usedata 盘点草案审阅说明

> 状态：待裁定｜as_of 2026-10-06

唯一依据是 `usedata` 源件。现有 `cbdb` 未参与盘点，也不得用于裁定。

## 已有证据

- `inventory_members.tsv`：成员级枚举；
- `ledger_final.tsv`：源对象、拟定目标和去重标记的工作草案；文件名中的 `final` 是历史命名，不代表合同已批准；
- `ledger_final_summary.json`：草案汇总；
- `collisions_mirrors.json`：同名镜像与字节比较；
- `xls_sheets.json`、`tgaz_objects.json`：部分容器内部结构；
- 其他 `*_baseline.*`、`*_summary.*`：盘点期机器证据。

盘点已覆盖多类文件和容器内部对象，但“能枚举”不等于“能完整导入和验证”。数量以机器文件为准，本说明不复制维护。

## 尚未裁定

1. 跨载体同名数据组：是全部导入并区分载体，还是经证据确认后将部分标为 `MIRROR`；
2. `v4_chgis_dbase.mdb` 的非同字节副本：不能按同名自动取一；
3. `Thumbs.db` 等非业务成员：应显式标为 `NON_TABULAR`，不能静默忽略；
4. 草案当前使用 `public/chgis/harv`，而现行方案建议 `cbdb/chgis/harv/audit`，生成正式合同前必须完成确定映射；
5. 每项的 `IMPORT/MIRROR/NON_TABULAR/BLOCKED` 状态、理由和证据尚未形成完整的 `sources.yaml`。

## 通过条件

本草案只有在全部成员均有唯一处置、冲突逐项裁定、目标命名冻结并经用户审阅后，才能生成 `config/sources.yaml` 并成为阶段 0 的正式导入合同。在此之前不得称为“最终底账”或据此启动全量导入。

# 历史误提交更正记录（2026-11-21）

范围：提交 `84386df` 中误随 `scp -r` 入仓的 MDB 提取二进制。本文件为机器可核更正记录，不改写历史（R-10）。

## 逐条实测（`git ls-tree -r -l 84386df | grep '\.mdb$'`）

路径前缀 `.mdb-sql-block4-20261120/`

| blob sha | 字节数 | 路径 |
|---|---|---|
| `1f90a2cbca263d6f665cca2b7c8c8e9ca79c3a7a` | 46,702,592 | `mdb/v2_zzkz6u/chgis_v2_database.mdb` |
| `7c6ce4263f148cfdc1e525f62f888c1f4d8a92b2` | 52,195,328 | `mdb/v3_himive/v3_chgis_database.mdb` |
| `14d21fc95fcea8df9aba63cd2ba4acd96630c85f` | 65,896,448 | `mdb/v4_access_zip/v4_chgis_dbase.mdb` |
| `5e1dcac08b46cc3927cbd5f7265633cc4b762477` | 65,896,448 | `mdb/v4_direct/v4_chgis_dbase.mdb` |
| `14d21fc95fcea8df9aba63cd2ba4acd96630c85f` | 65,896,448 | `mdb/v4_shapefiles_zip/v4_chgis_dbase.mdb` |

- 条目合计：**5 条 / 296,587,264 字节**
- 唯一 blob：**4 个**（`v4_access_zip` 与 `v4_shapefiles_zip` 共享 blob `14d21fc9…`；`v4_direct` 为独立 blob `5e1dcac0…`）

## 重算命令

```bash
git ls-tree -r -l 84386df | grep '\.mdb$'
git ls-tree -r -l 84386df | grep '\.mdb$' | awk '{s+=$4} END {print s, NR}'
git ls-tree -r -l 84386df | grep '\.mdb$' | awk '{print $3}' | sort -u | wc -l
```

## 当前状态

- `git ls-files '*.mdb'` = **0**（纠偏提交 `bb9b2e5` 已从工作树/索引移除 5 枚二进制，保留 98 个文本证据件）
- `.mdb-sql-block4-20261120/.gitignore` 含 `*.mdb`，防复发

## 旧回报口径保留声明

- `bb9b2e5` 提交信息中的「~295MB」与 `cd595db` 提交信息中的「296652508B」均为当时回报原文，**保留不改写**。
- 以本记录的实测值 **296,587,264 字节 / 5 条目 / 4 唯一 blob** 为准。

## 处置

历史对象仍存在于祖先提交 `84386df` 的对象库中，不重写历史（依据 R-10）。是否清理（如 gc/替代交付分支重建等）留茶香裁定。

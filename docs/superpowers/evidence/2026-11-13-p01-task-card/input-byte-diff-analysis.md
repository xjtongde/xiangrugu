# input-byte-diff-analysis.md —— 6 份 staging 输入文件的字节差异与来源

> 状态：收据已回（提交 `5cd428af`），归因已按实测更新；实测原始哈希值未随包返回，见下节区分｜as_of 2026-11-13

## 结论摘要

25 份 staging 输入中，**恰好 6 份**不在 `.gitattributes` 的 `-text` 保护区内。代跑实测（Windows 控制端报告）：隔离导出的初始副本中这 6 份为 CRLF 字节，哈希与大小同下表模拟值一致；从 38（DSH 工作区）取 LF 原件替换后，25/25 全部匹配权威清单并在 32 复核通过。其余 19 份（contracts/**、evidence/** 及证据树内的 controller LF 副本）受 `-text` 保护，字节不变。

## 6 份文件清单（LF 权威 vs 模拟 CRLF）

LF 列＝仓库基线 `8fbc8c9`（交接 `2fde319`）的权威字节，与 `packet-inputs.sha256` 逐项一致；CRLF 列＝对 LF 字节做 `\n → \r\n` 的**模拟**结果（每行 +1 字节），用于与 Windows 侧实测哈希比对以确认差异成因。本表不含任何真实源数据。

| 仓库路径 | LF SHA-256（权威） | LF 字节 | 行数 | 模拟 CRLF SHA-256 | CRLF 字节 |
|---|---|---|---|---|---|
| `datamgmt/config/roots.yaml` | `6235c356fca754a687a2f02998770c9609b20748ade674d0050d86a0a428e07c` | 13237 | 186 | `6458aa7f9f85d1bc4fa727402abb412c1b929ba3851e69546733f448e7f55db6` | 13423 |
| `datamgmt/src/xiangrugu_datamgmt/task_preparation.py` | `624bd1962bd1d0bd3cb91b77eff0b1667beda79a8c62160ddf180414eb4039bf` | 14107 | 228 | `3d08419706d928cd4cbba04da117e739ab8843cb8385a8759ec675f0ca3b7080` | 14335 |
| `datamgmt/src/xiangrugu_datamgmt/readonly_batch.py` | `79474939c0c88a778baac59ae4f68a46adf3899eb335e087562175a064802145` | 19265 | 333 | `7dc97a85edb092bcc58028ea53da53c114f4af659045709ca60bff1d8c595349` | 19598 |
| `datamgmt/src/xiangrugu_datamgmt/project_partition.py` | `af043f5e492f89808b909db69ec1611ae85c3f983996561162ce5f72446e2a5f` | 20414 | 310 | `8f34539ebf45a5e1de190f91bc58dbf45ffeb43cf04d40ebf7099d14bd3382e2` | 20724 |
| `datamgmt/src/xiangrugu_datamgmt/project_partition_coverage.py` | `f5a4e88eb381884b535f16a61c8f07018d8f7076d069f1ec50f288a5891f2ca8` | 14195 | 197 | `aa8e65233ef66d9418417ed4c7733c56db38359d18474e124a13852a8b2956e3` | 14392 |
| `datamgmt/tests/unit/test_large_artificial_batch.py` | `a50467b1169f6275a1a8ac1c00dd53b9a34a38645b37e21221565f2519b6e146` | 7476 | 129 | `d411118202c7513503bd240f64b3652f650c0e130139556465e113dbc2d5f088` | 7605 |

## 来源与机制（实测与推断分开记账）

1. **提交字节（已验证）**：6 份文件在 Git 中均为 LF（本工作区已逐字节核验，pin 全吻合）。
2. **保护缺口（已验证）**：`.gitattributes` 仅声明 `datamgmt/contracts/** -text`、`docs/superpowers/evidence/** -text`、`datamgmt/tests/fixtures/*.json -text`；`datamgmt/config/`、`datamgmt/src/`、`datamgmt/tests/unit/` 不在其内。
3. **转换点（实测报告＋推断，须区分）**：
   - **实测（代跑方报告，收据 README 第 7 行与 proxy-notes.txt）**：初始副本经 **git archive 在隔离环境导出**，其中 6 份呈 CRLF 字节，哈希/大小与 DSH 模拟值一致。包内**未附**这 6 份的实测原始哈希值，匹配结论为代跑方报告，DSH 以独立计算的模拟值作参照。
   - **推断（未证实，不作结论）**：早先假设的"Windows 常规检出 `core.autocrlf=true` 转换"**未被证据支持**——实际流程是隔离导出，转换发生在该导出/隔离环节；其内部机制（导出工具或隔离环境的行尾处理）包内无证据，不推断。
4. **拦截点（设计如此，本轮未触发 stager 拒绝）**：`stage-review.ps1` 先对 `packet-inputs.sha256` 逐文件校验再传输；本轮代跑在隔离目录内先行比对发现差异，取原件修正后才进入正式 staging。
5. **处置（实测报告＋在包证据）**：从 38（DSH 工作区）复制 6 份 LF 原件替换隔离副本，对既有 25 文件清单复核全匹配；最终 `packet-check.txt`（在包）25/25 通过（32 locale zh_CN，输出"成功"）。**未做 stager 侧归一化**——字节精确纪律保持。
6. **长期改进（未实施，另待授权）**：把这 6 份所在路径纳入 `-text`，或在 stager 增加 CRLF 诊断输出；记入改进账前需用户授权。

## 回填结果（收据 5cd428af）

- [x] 6 份差异文件与 CRLF 成因：代跑方报告实测哈希/大小匹配模拟值（原始值未随包返回，模拟值见上表，DSH 独立计算）。
- [x] 修正后远端复核：`returned/packet-check.txt` 25/25 通过，路径集合与权威清单逐项一致（acceptance-check 第 11 组）。
- [x] 实测与 CRLF 模拟一致，无真实漂移迹象；若后续取得实测原始值，与上表模拟列比对即可闭环。

## 关联修复

同日修复 `invoke-review.ps1` 的 `SourceCopy` 校验正则：默认值 `source-green-v1` 被旧正则 `(-v(?:[2-9]|[1-9][0-9]+))?` 拒绝（v1 不在 v2–v99 内）。新正则 `(-v(?:[1-9]|[1-9][0-9]+))?` 接受 v1–v99（v100+ 与历史 11-09 模式语义一致），非法形式仍拒绝。已用 14 组用例静态验证。该脚本不参与 staging 字节门，仅影响传输调用。**代跑实测（proxy-notes.txt）：该缺陷在 Windows 侧真实发生，代跑方在其 Windows 专用副本上接受 v1；上传包与 Linux 运行器未改动。** DSH 工作副本的修复与代跑侧处置一致。

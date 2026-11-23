# 核销器原清单绑定补正 · lead 预核（15 分钟盒）

- 起表 15:52:46 UTC，硬停 16:07:46 UTC。基线 0da4f0f382c698071c26982c46244447f5c52187（M=2 完好）。
- 现版缺口：run_writeoff 仅核 manifest.sha==contract.inventory_sha256（经 reader），未锁定已审原清单 fb5e6b33——替代清单携同三条 issue+合同绑替代可误签发（a03 R37b 合成全覆 ready True 实证该路径）。
- 补正：ORIGINAL_INVENTORY_SHA256 常量+审批门后双核（清单摘要/合同绑定）；结果增 run_evidence 全文（可取回重算）。
- 测试：原合成正例改拒绝用例；新增合同绑替代摘要拒绝；正例增重算断言。rollup 不动。

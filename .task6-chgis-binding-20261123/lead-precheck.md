# Task 6 CHGIS 第 4 行固定路径例外实施 · lead 预核（2026-11-22/23，30 分钟盒）

- 起表 19:15:14 UTC，硬停 19:45:14 UTC。基线 99ff362c95d2e06bf0f48ad2c4f899a3e8bca620（M=2 完好、暂存空）。
- 茶香授权隔离实现+测试；范围仅本条路径例外所需合同类型/Schema/运行核验/测试；正式冻结/落盘/服务/写库另行授权。

## 真实 inventory 三面（lead 19:15 UTC 直核）
- harvard/chgis/SHA256SUMS.txt 断言 6 条：**line4 matched=False**，raw_name China_Periods_ReignDates.zip，target harvard/chgis/China_Periods_ReignDates.zip，sha 7452ae6c…；其余 5 行 matched=True。
- **声明路径 harvard/chgis/China_Periods_ReignDates.zip entries=0（缺席）**。
- 外层目标 chgis-v6/China_Periods_ReignDates.zip chain[]：**file/155774/7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e 唯一**（preview resolved 过滤 not archive_chain；内层 25 成员带链不计）。

## 固定身份（派工锁定）
源账 harvard/chgis/SHA256SUMS.txt / 551B / 694c101f04e636012e752c87958c8065c8e6926633c8b542e89978d8f8451a60；line4 verbatim「7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e  China_Periods_ReignDates.zip」（双空格）；declared_target harvard/chgis/China_Periods_ReignDates.zip；resolved_target chgis-v6/China_Periods_ReignDates.zip / 155774B / 7452ae6c…。

## 复用面（lead 读源码）
- checksum_candidates.py PathBindingCandidate L41-53{kind exact_path_binding, line, raw_name, declared_target, resolved_target, expected_sha256, expected_size}；preview 分支 L122-144：binding line 存在/_record 解析/声明==(expected_sha256,raw_name,declared_target)/strict assertion 恰一且 matched=False 且 (raw_name,target,expected_sha256) 等/**声明路径不得存在 entries**/resolved 恰一 file 且 (size,sha)==(expected_size,digest)。
- contracts.py ContractException.code Literal["checksum_nul"]（L149）→本盒扩 "checksum_path_binding"（一行，授权范围内）；contract_schema() L196=model_json_schema；config/contract.schema.json 须再生==runtime（test_contracts L125-128 核）。
- disposition.py closed 计数行扩 or path_exception_closed。

## 本盒交付控制
- contracts.py 一行枚举+schema 再生；checksum_reader.py PATH_BINDING_WHITELIST+run_fixed_path_binding_exception+path_exception_closed；disposition 一行；fixture sha256sums-chgis.b64（551B provenance）；测试正例+反例≥6+四态回归（NUL 单独/CHGIS 单独/并存/任一失配）。
- 证据保留原声明+显式绑定+双方完整身份；审批/清单绑定/外层三元组/expected 四核同 NUL 补正模式。
- rollup 不动；五块零改写；M=2 不触；源件只读；a02 失败 lead 即接管。
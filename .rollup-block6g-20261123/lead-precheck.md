# 第 6/6 块续盒六（校验账运行门实施准备）· lead 预核（2026-11-22/23，20 分钟盒）

- 起表 18:15:03 UTC，硬停 18:35:03 UTC。基线 527532564c95420e3bb0d9731aaf6a58518fb2a4（M=2 完好、暂存空）。
- 仅草案修正+实施方案；运行代码实施/测试执行另行授权；复用已有只读证据。

## 两例外完整身份（lead 18:15 UTC historical-blockers.json 直取）
- **NUL**：carrier SHA256SUMS-b2；raw_sha256 900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb；size 22071；valid_lines 172（171 harvard-full DVN 外层+1 chgis-v6）；nul_count 126；offset [21945,22070] 单连续段；roots_yaml_format_anomaly verbatim 在账（源件不修/解析器须检测写证据/仅固定摘要可由冻结合同批准兼容解析）。
- **CHGIS line4**：源账 harvard/chgis/SHA256SUMS.txt；sha 694c101f04e636012e752c87958c8065c8e6926633c8b542e89978d8f8451a60；size 551；line4_verbatim「7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e  China_Periods_ReignDates.zip」；目标 chgis-v6/China_Periods_ReignDates.zip sha 7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e size 155774；layout_cause README-b2 明载（随附账走 harvard/chgis/，数据 zip 收 chgis-v6/）；32 流式重算==声明值。

## 镜像投影文案修正要点（派工）
- 相同字节**只限制 IMPORT 主件至多一个**（primary_bytes 字典仅登记 IMPORT，disposition.py L81-85）；NON_TABULAR/BLOCKED/MIRROR 不受此限。
- **mirror_evidence_sha256（镜像相等性证据摘要）与 expected.sha256（源件摘要）是独立字段**（contracts.py L103-104）；文案不得混同。

## 首批空间 2 补齐基准（lead 已知）
- SID 9b4496c93de442c447b58adf9be56303ab5fd4897d68bbf0bad99069d12d44dc（Ca1884route_przh_1251）/ e601ce1a7667c8286abce0d09c5b81d3dc809265ed219dd6e4e1dd3c5cfc9ace（utf8）；.shp 主件 1884route.zip ord[6]/[14] 同 sha 109d74b1e5cefcd1…/1752B；6 组件 cpg/dbf/prj/qpj/shp/shx；候选名 chgis.ca1884route_przh_1251 / chgis.ca1884route_przh_utf8（naming-draft）；expected_count/expected_sha256 MISSING；装载器 GAP。

## 本盒交付控制
- 草案修正：exceptions-candidates 完整身份分字段+projection 镜像文案；新件 run-gate-implementation-plan（≥6 验收用例+入口/测试边界）；first-batch spatial2 补齐+text5 同口径；SUMMARY/TODO。
- 运行门白名单仅两条固定 raw_sha256（非泛化）；incomplete_inventory 对其余未知异常拦截保留。
- 归属 8004+1311+1293 零漂移；五块+模型源码零改写；M=2 不触；manifest↔SUMMARY 绑定双跑收敛（上盒教训）。
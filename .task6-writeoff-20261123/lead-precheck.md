# 三条固定清点 issue 核销实施 · lead 预核（30 分钟盒）

- 起表 15:32:27 UTC，硬停 16:02:27 UTC。基线 912a8835ca2acd9dddae35a078e5fd8cbddd4b43（M=2 完好）。
- 茶香授权隔离候选实现+测试；受控接收/正式审批冻结/落盘/写库另行授权。
- 三 issue 完整身份（R36 在账）：checksum_line line=173 / checksum_nul count=126 @SHA256SUMS-b2；checksum_missing line=4 @harvard/chgis/SHA256SUMS.txt；chain()/ords()/blocking True。
- 两更正定位（lead 直核）：rgp acceptance_cases C7/C8 input 短摘要 900d98c6/694c101f（非全 64）→更正全 64；fbd 两 Ca1884route approved_scope 无 SRID 状态→补「SRID 已批」（load-blockers items[4]「spatial 899 提案 + SRID 政策未决（approved 2 除外）」即此二件，naming-draft approved_spatial_special lane SID 9b4496c9/e601ce1a 对位）。
- 设计：writeoff.py 派生评估器（身份+次数核/重跑两例外/正常 evaluate/仅派生核销 incomplete/原清单不动/其余门照常）；跨合同混用结构性不可能（证据每次再生绑当次合同）。

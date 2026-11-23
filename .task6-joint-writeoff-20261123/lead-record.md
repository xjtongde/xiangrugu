# 两条例外联验与清点核销方案 · lead 记录（30 分钟盒）

- 起表 14:54:20 UTC，硬停 15:24:20 UTC。基线 e7a132cbe6e7fdc0ddd0e4e48131f761c420c3ab（M=2 完好）。
- 范围仅隔离只读联验+方案交付；零源码改动；核销实施/转正/冻结/落盘另行授权。
- a02 起始即失败（零产物）→lead 接管（披露）。
- lead 预核（14:54 UTC）：原 inventory 三 issue 逐字直读（checksum_line line=173 / checksum_nul count=126 / checksum_missing line=4）；首批七 gaps_itemized 三条逐字。
- 实施链（14:56–14:58 UTC）：
  1. 联验包：src+测试助手+两 fixture+inventory+schema+两证据文件 tar→32→容器 /tmp/jw（stdin 管道）。
  2. drive.py 容器实跑 DRIVE_EXIT=0 stderr 0B：line173 字节证（prefix 172 换行/末换行@21944/tail 126 全 NUL/split[172]==tail True）；两例外并存合同（921e1469…）+真实 inventory evaluate→[incomplete_inventory, unmatched_member] ready false complete false；五留门反例（缺 NUL raw/缺 CHGIS raw/摘要变化/未审批→exception_not_implemented 保持；新增阻断项→incomplete_inventory 恒门 ready false）。
  3. joint-comparison.json 取回落盘（机器对照表：原清单 sha+三 issue 逐字+两证据文件 sha nul 2fa2400c/chgis fe8c392b+逐 issue 对应条件+byte_proof+joint+gates）。
  4. writeoff-plan.json（PLAN_NOT_IMPLEMENTED）：原清单逐字节保留；writeoff_result 三元组绑定+证据再生要求（现证据绑 fixture 合同，正式核销须正式合同下重跑）；三可结项精确身份+conditions；正常入口 evaluate+exception_run_inputs→核销评估器扩展另行授权；五条阻断规则；恒门/伪影/新增阻断 nuance。a03 一期残差精确身份（chgis-v6/China_Periods_ReignDates.zip）+双观测面注记采纳补入。
  5. first-batch-seven-gaps.json：7 对象逐件（5 文本+2 空间；name_status/loader GAP 照录/canonical MISSING/approval_gaps）+gaps_itemized 逐字。
  6. promotion-preconditions.md：8 步顺序依赖清单。
- a03 R36 一期全 PASS：三 issue 逐字独立核；NUL 双闭字节级独立证（32 实物直读 raw[21944:21946]==\n\x00）；CHGIS 闭③；恒门/伪影区分（残差精确身份）；留门 G0-G4 自写驱动全 ready false；原清单/源件/fixture 原样核；零源码改动确证（src/config/tests/rollup diff 空）。二期交叉核进行中（硬停 15:16）。
- 边界：rollup 19 件不动；五块零改写；M=2 未触；源件只读；32 deploy 未接收本提交（前置清单第 1 步）。

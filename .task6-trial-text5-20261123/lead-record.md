# 五件文本隔离装载与全量回读 · lead 记录（30 分钟盒）

- 起表 17:31:09 UTC，硬停 18:01:09。基线 d466562（M=2 完好）。茶香明确授权。a02 起始即失败→lead 接管（披露）。
- 隔离边界（先补）：仅 32 已验证项目快照读件；复用本地 postgres:18-bookworm，**实际镜像 Id sha256:882236b897e39051d2368c5ccc6cda944904723506b2dfc97f2a8f5bc9afa382==RepoDigest 记录在证据**；容器 xiangrugu-trial-text5-20261123-173109 **本次唯一身份**，--network none 无宿主端口；清理仅本次容器（用后 docker rm -f 留证）；pg32b 容器运行未触。
- 接收方案**三锚统一**：代码锚=审批包锚=接收前实际回退锚=同一完整版本锚（本盒记录 d466562；接收时以经核对当时分支头为准，三者不得分别取不同提交）；R1 全量 checkout 统一锚。
- 实施链：
  1. 逐件试装前五核：源 sha（d21bd9f6/b720bff1/23b23f6f/cdc6d3e5/58ef3cb4）+schema sha（73d25971/70bdb375/492a32cd/19287ad3/15a333ed）+行数（2957/40199/1033/29/3389）+XRGVALUE-v1 流 sha+stream_bytes 全 PASS 才写入；失配该件停报留证门在码（本轮无失配）。
  2. 读法复用已批：m008002 utf-8-sig/bom sig/backslash true；m008003 utf-8-sig/bom/backslash false；m008004/m006642 utf-8/false/false；m004812 utf-8/false/true（快照路径重跑）。csv 通用解析（delimiter \t/quotechar "/doublequote/escapechar 按 backslash_escape/utf-8-sig 剥 BOM/strict）。
  3. 实例身份写入前核 True（18.4/PGDATA 18/docker/postmaster 17:34:07 全新/inet null/库清单仅 trial+模板）。
  4. 五表显式临时名：harv.trial_m008002/m008003/m008004/m004812_20261123 + chgis.trial_m006642_20261123（候选生产名未批）；DDL+COPY exit 0/0 ×5。
  5. 全量回读：2957/40199/1033/29/3389；列名类型列序 nullable 逐项全合；null 行 0×5（空串保留）；rownum [1,N] 全序；**重复按实际值列（排除唯一 __src_rownum）：m008003 63 组/74 多余行，余四件 0/0**；库值重建流 sha 逐件==已批（475ea1d8/dcbedb5a/d233ed9c/b3f6ceb6/3bad44a0）+bytes 全合；**合计 47607==totals ✓**。
  6. T5_EXIT=0 stderr 0B status TRIAL_TEXT5_PASS first_difference None。
  7. 审批表增 trial_text5_result 单列（separate_from_formal_approval；distinction 试装通过≠正式合同接入≠生产装载授权）；approval-table 0adf781dd1c725d1/生成器 f8c1dc941426edec 双跑全等；方案五件试装单列节。
  8. 回归：五套 141 passed REG_EXIT=0 stderr 0B（src 零改写，驱动器在证据目录）。
- a03 R42 一期（五件期望基线独立锁定：rows×列数自洽/合计 47607/空值语义锚定+回读方案就绪）PASS；R42b 二期独立逐表回读（自写 t5stream.py/t5dup.sh/t5meta.sh，jsonb_build_array→base64 无损通道，零复用 lead 码）STREAM_EXIT=0/DUP_EXIT=0/META_EXIT=0：五表 rows/fields/bytes/dup（63/74==lead）/rownum/流 sha×5/schema_sha×5 全 PASS；列规格 5/5（含 55 列 slug 长名截断位对位）；is_nullable YES 计数 0×5；镜像 Id 逐字等/NetworkMode none/Ports 空/库清单隔离；三锚 6/6 token；trial_text5_result verbatim；范围核 rollup+src diff 空/M=2。诊断披露：a03 中途三次 STREAM_EXIT=1 系其驱动传参面（容器无 python3/scp 别名/嵌套 ssh 转义），改通道后一次通过，非交付缺陷。
- 边界：pg32/pg32b/deploy/正式落盘不在本轮；rollup 19 件不动；原 inventory/五块不动；M=2 未触。
- 三态区分：**试装通过**（本盒）≠**正式合同接入**（expected_count/expected_sha256 待冻结接入）≠**生产装载授权**（另批）。
- 首个剩余缺口：promotion 步骤 1「32 受控接收转正」；m008003 63 组实际值重复须由装载侧行数含重复计数口径承接（a03 gap 文）。

## 补正：cleanup 时机与 scope 语义（a03 R42b 候选不一致处置）
- a03 观察：交报时容器仍 Up，与 cleanup_scope「only this run's container」可观察差异。
- 澄清：**cleanup_scope 为范围语义**（清理对象仅限本次创建的容器，绝不波及他容器）；**保留策略为时机语义**——容器保留至 a03 独立回读复核完成，随后即刻销毁。a03 交报时 Up 系复核窗口保留，属预期。
- 执行留证：17:37:22 UTC docker rm -f xiangrugu-trial-text5-20261123-173109（TRIAL_CONTAINER_REMOVED）；pg32b 容器运行未触（grep -c=1）；证据增 cleanup_execution 节点（policy/removed_at/command）。R41 单表容器已于前盒销毁。非数据面问题，五表全 PASS 结论不变。

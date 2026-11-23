# 首批七对象受控接收预检报告（30 分钟盒）

- 起表 18:03:31 UTC，硬停 18:33:31。基线 df5a7c513cc9912efcb4322c405c1a9af0a913ee。lead 收口，a03 独立复核。本盒复用试装证据；源件只读；**不替换 deploy/不改服务/不冻结合同/不写库**。

## 1. deploy 接收前状态（32 只读核对）
- **现役 Git 提交：UNKNOWN**——/opt/mydocker/xiangrugu/deploy 非 Git 仓库（无 .git，git rev-parse 致命错误）；无 version/REVISION 标记文件。按派单记为未知，不推断。
- 可公开版本标记：**内容 sha256 清单 62737bd0c16ac23f1c9ba4fd92e73abadb6a6eace014494f605f29e6aa00396f**（7719 文件/87798110 字节；清单全文 deploy-content-manifest.txt，host 与本地取回双 sha 一致）；关键文件 AGENTS.md 2043155a…/docker-compose.yml 67212d28…/Dockerfile 51a1df8e…（前 16 位展示）；mtime 2026-10-06..10-15（+0800），内容代际早于当前交付分支。
- **现役镜像**：xiangrugu-dev 容器镜像 xiangrugu:dev **Id sha256:89f1a0978cb817871d50d6468f3dec19e3ea1e67d5bc73457a62fd10b5b8732d**；deploy→/workspace **ro 挂载**（容器不写 deploy）；data/persistent、data/var 独立 rw 绑定不在 deploy 保护范围。
- **保护与恢复范围**：deploy 全部 7719 文件（datamgmt/demo/docs/scripts/根文件）。
- **恢复点判定**：Git 锚不可证→**以内容快照为可验证恢复点**（R0 tar+全量清单；恢复校验=sha256sum -c+文件数+字节和+tar 完整性）。可形成→预检通过；若接收时漂移或快照不可形成→受控接收停在预检。
- 方案已修正：**来件完整提交（df5a7c5…）与接收前实际恢复点（deploy 内容快照 62737bd0…）分列**；备份/恢复校验/停手条件五条在文（controlled-reception-plan.md）。

## 2. 七项待批表（pending-approval-seven-20261123.json，sha 23e44d12bbd6dd50…）
- 逐项：SID/正式候选全名/精确字段映射（value_columns 全列 column_key/target_name/pg_type/nullable+指针）/期望行数/属性摘要（期望==试装回读全 match）；空间两项另列几何摘要+SRID 4326+2D Point+**两份 DBF 各自来源身份**（0b4b86cb…/eb9dfed2…+cpg）+**原始坐标保留**（hex EWKB 无十进制转换/逐点字节 match）。
- **文本实际重复保留**：m008003 **63 组/74 多余行**（值列键排除唯一 __src_rownum；expected_count 40199 含重复口径）；余四件 0/0；空间 attr 0/xy 0。
- 行数合计：文本 47607 + 空间 118。三账 ledgers 全 false；PENDING_APPROVAL。
- **现行合同表达能力逐项核**（contracts.py ObjectTarget/ColumnEncoding/DispositionRule/ReleaseContract）：
  - 可表达：rule_id/selector/源 raw sha+size/disposition/format_family/逐列 codec/targets（object_name/schema/table≤63 正则/expected_count/expected_sha256）/review/frozen/两类 checksum 例外。**七件候选全名均合 table 正则（41/63/63/63/63/21/21）——表名不构成缺口**。
  - **首个仍无法表达位置：m008002（首批首件）精确字段映射**——ObjectTarget 仅 count/sha，ColumnEncoding 仅 codec；value_columns 55 列（column_key→target_name/pg_type/nullable/序）无结构承载。
  - 后续无法表达：派生 __src_rownum、numeric 宽度标度、重复口径账、空间几何期望（SRID/维数/类型/XRGGEOM-v1 sha）。
  - 接入路径：合同结构扩展须另行设计批准；**本盒不冻结合同不改 schema**。

## 3. 判定与边界
- **预检判定：PASS（预检完成）**——可验证恢复点可形成（内容快照）；UNKNOWN Git 提交如实记录；七项证据齐备且与试装摘要全等；首个合同表达缺口已定位。
- **受控接收本身仍停在预检**：正式接收/冻结/落盘/写库另批；表名/冻结/装载三账未批。
- 交付面：仅预检报告（本目录）+接收方案修正+待批表；rollup/src/原 inventory/五块零改写；M=2 未触；deploy 未替换；服务未改。
- 证据：deploy-state.json（e9712e6a887d2745…）/deploy-content-manifest.txt（62737bd0…）/pending-approval-seven-20261123.json（23e44d12bbd6dd50…）/build_precheck.py（46f944ef201aea7b…，双跑字节全等）。
- a03 独立复核：回退依据（非 Git 自证+清单抽核+恢复点可验证性）+七项证据+合同表达独立核；按 PASS/PARTIAL/BLOCKED 回报。
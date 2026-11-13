# progress.md —— p01 新任务卡准备与代跑进度

## 2026-11-13 准备（DSH，本地编辑工作区）

- 从 Gitea 交接分支 `codex/xiangrugu-handoff-20261113`（`2fde319cb7e00d9cc6efb807aae3de44c55a6465`）建立工作分支 `dsh/p01-taskcard-20261113`；main 与交接分支未动。按本次授权不提交、不推送。
- 已读 HANDOFF.md、AGENTS.md、rules.md、docs/index.md、datamgmt/README.md、11-13 接入证据与 11-09 真实停点、11-09 任务卡及其准备/运行脚本、task_preparation/task_partition/project_partition/task_control/candidate_supervisor 产品门。
- 本地 pin 核验（只读）：父级 review `edf31997…` 的 14 项绑定全部与工作树吻合；roots `6235c356…`、证书 `58cb2e50…`（232 成员＝189 文件/43 目录，manifest `03174f42…`）吻合；7 个安装模块源文件与 11-13 构建输入（135 项）逐项吻合；11-13 verification.json pin `8c121fd0…`。
- 逻辑摘要预算推导核对：2508987728（189 文件尺寸和）＋2×586485760（批前后双摘要）＝3681959248，与 11-09 卡片一致。
- 新 attempt 命名 `real-p01-20261113-a`；新 runtime `sha256:8f8995689096…`（tag runtime-request-reader-20261113-a，revision 8fbc8c9 dirty，10001:10001）。
- 交付：prepare-closed-review.py（含任务卡确定性组装）、product-gate-probe.py、run-review.sh（metadata/product-gate/reject-no-authorization）、verify.sh、stage-review.ps1、invoke-review.ps1、controller LF 副本、25 文件权威清单、README、RUNBOOK。bash -n 与 py_compile 静态检查通过。
- 32 访问裁决：本机（38）与已授权跳板无法认证到 32；用户裁决由 Windows/Codex 侧代跑，DSH 不直连 32。

## 2026-11-13 第二轮（DSH，验收准备）

- 用户指令：接收并复核 32 代跑收据、完成任务卡验收、修复启动脚本默认值缺陷、记录 6 份输入文件字节差异及来源，完成后停在授权前。
- **收据状态：未到达。** 已查工作区、/tmp、home、DSH 附件存储、本会话存储、Gitea 远端分支/标签；本机仍无法认证到 32。验收核对（任务卡/review SHA-256、镜像身份、资源、两道拒绝、候选回收）待收据到达后执行，不预填结论。
- **已修复** `invoke-review.ps1`：`SourceCopy` 默认 `source-green-v1` 被旧正则 `(-v(?:[2-9]|[1-9][0-9]+))?` 拒绝；改为 `(-v(?:[1-9]|[1-9][0-9]+))?`，14 组用例静态验证通过（v1 接受，v0/v01/非法形式仍拒绝；v100+ 与历史 11-09 模式语义一致）。
- **已记录** `input-byte-diff-analysis.md`：25 份 staging 输入中恰好 6 份不在 `-text` 保护区（roots.yaml、task_preparation.py、readonly_batch.py、project_partition.py、project_partition_coverage.py、test_large_artificial_batch.py）；LF 权威哈希与模拟 CRLF 哈希/字节数逐件固定，来源＝Windows autocrlf 检出转换，拦截点＝stager 字节门。Windows 实测哈希待收据回填。
- 覆盖包与 overlay.sha256 已随修复重建；packet-inputs.sha256 不变（invoke 脚本不参与 staging）。

## 2026-11-13 第三轮（DSH，验收完成）

- 收据经 Gitea 分支 `codex/p01-card-receipts-20261113` 提交 `5cd428af8d615b30e399c40c980edc5870c94709` 到达；父提交＝交接 `2fde319`，仅新增 3 文件；提取字节与提交树逐项一致。
- 外层 SHA `5adc58c1dcdb877d362481de5ad0eb8826be262e3e875ac269549e668ec2be7d` 通过；内层 `p01-card-receipts.tar.gz` 摘要通过；76 条目解包于收据目录 `returned/`。
- DSH 独立验收 **137/137 通过**（acceptance-check.py/json）：任务卡 `41bd0ecf…`、关闭 review `a7c2c5bd…` 重算与交叉绑定一致；镜像身份、资源（HostConfig＋cgroup）、两道拒绝（退出 2 / real_execution_closed）、候选回收（2/2 精确名）、服务/宿主健康、7 模块、staging 25/25、传输 0/0/2、全部边界保持。
- 6 份输入字节差异归因按实测更新：初始副本为隔离 git archive 导出（非普通检出），实测匹配 CRLF 模拟值（代跑方报告，原始值未随包）；从 38 取原件后 25/25 通过。checkout autocrlf 假设标记为未证实推断。
- 环境事实记录：32 locale zh_CN；.incomplete 为产品保留硬链接副本；SSH .log 空属设计。

## 代跑（Windows/Codex，已完成，据回收据）

- [x] 步骤 0 基线＋overlay 校验
- [x] 步骤 1 staging（25 文件，packet-check.txt 25/25 成功；6 份 CRLF 差异取 38 原件修正）
- [x] 步骤 2 metadata 运行（退出 0，任务卡生成）
- [x] 步骤 3 product-gate 运行（退出 0，real_execution_closed）
- [x] 步骤 4 reject-no-authorization 运行（退出 2，refused_before_materialize）
- [x] 步骤 5 verify.sh（P01_TASK_CARD_METADATA_VERIFIED_CLOSED）
- [x] 步骤 6 收据回传（Gitea 提交 5cd428af）

## 回填（DSH，已完成）

- [x] 任务卡 SHA-256、关闭 review 摘要、verification.json 结论回填 README
- [x] 验收结论汇总交总指挥（本轮最终报告）；停在真实读取授权前
## 2026-11-13 第四轮（DSH，执行交付准备）

- 总指挥复核通过关闭任务卡验收；本轮按指示准备 real-p01-20261113-a 执行交付，停在真实读取授权前。
- 新证据目录 `docs/superpowers/evidence/2026-11-13-p01-real-prep/`：两段式（Stage A 组装＝纯元数据无快照挂载；Stage B＝唯一真实候选 1800/1830/1880s），卡片资源与范围逐项绑定；授权门双层（宿主＋容器内 worker），缺 authorization.json 时在 materialize 前拒绝。
- 输入采用收据回传的已验收字节原样复现（45 项 packet-inputs-real.sha256），不重新生成；三 pin 经 controller-pins.txt 外部固定后由命令行传入 Stage B。
- ACCESS-32.md 提交三种登录方案供茶香裁决（推荐：38→32 root 专用受限密钥，from="192.168.3.38"，一行撤销）；当前实测本机对 32 无认证通道。
- 本地静态核验：bash -n×2、ast.parse、manifest 关键 pin 断言、脚本顺序/模板 canonical/字段覆盖交叉检查全部通过；未创建远端运行根、未启动任何容器。

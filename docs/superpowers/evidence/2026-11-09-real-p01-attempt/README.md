# p01 新 runtime 一次真实尝试：1800秒超时停止

2026-11-09最终状态：本次具名授权已用，唯一真实attempt `real-p01-20261109-c`在1800.257557707秒以timeout停止，没有完整批、没有新增源侧值期望；真实覆盖仍68/78、Task8未完成。已收尾，不重试、不换attempt或下一表，不提高预算。

## 授权、身份和终态

用户在[任务卡](../2026-11-09-p01-read-review/README.md)明确确认问题后回复“继续”，authorization.json绑定卡片SHA256 `91908bdbc02341b45f3379dc0e00af70c0a3b321231c1706753df58429ffdebd`。仅允许POSTED_TO_ADDR_DATA原8列、固定快照2026-10-07-bootstrap的232成员及全文件摘要复核、SQLite批前后两次摘要；禁止NAS、其他业务表值、PG、冻结、导入、发布及自动重试。

实际runtime为`sha256:55b3f27687ea32e397d49a6fdfa010a6a862c4b6c99c471d4ef68c3fe2030696`，包含保持逐次检查的正式读取器；6个实际安装模块来源与133构建输入清单一致，无源码覆盖。HEAD仍8fbc8c97fcf1d818caddf6ab556fa82d986643ed，脏成果保留，无Git提交/推送/切分支或服务/镜像别名改变。

- 唯一真实候选ID：`eb6fd0d308bb9a8276d3ed96a491923709801763acf011fae03b4d7cb1384e93`。
- 监督：SOURCE_ONLY_WORKER_STOPPED，reason=timeout，max_seconds=1800，worker_exit_code=1，process_group_gone=true。
- worker随后：sqlite/cancelled，stage=object_read_sort，object_index=1，completed_objects=0，失败报告摘要及request关联核验通过。
- 宿主runner_error在约1807秒收到非零退出后留痕，是后续观察，不是最初触发原因。没有invalid_heartbeat事件。
- 没有batch.json，scratch连子目录均为空；两个metadata及一个真实候选共3个，均按完整ID确认不存在。未运行-Publish。

未形成完整批，因此不能宣称本次全快照/双摘要验收完成，也不能将临时文件变化、历史465284行或阶段名当作本次成功计数。人工80k单次18%改善没有使本次真实表在原1800秒内完成；两次真实运行都触及截止，不能据此计算真实提速百分比，也未测出真实校验/排序子阶段的耗时分布。

## 原始请求与资源

Windows原生独立核对对象/预算、完整父绑定及镜像/源身份后固定：

- request：`5940970c3333a062cb5c7300244b97dd06ad0c1e95cb04aa1167acaf5530d410`。
- approval：`eeca0c0c80a6929231b408845fb4b40741fb20bf36aad386855568bc64581653`。
- roots：`6235c356fca754a687a2f02998770c9609b20748ade674d0050d86a0a428e07c`。

审批内部request摘要依既有协议剔除approval_file/approval_sha256；控制端摘要绑定完整原始文件，两者用途不同。首次本地选择误将两者直接比较而拒绝，尚未启动候选；select-request.ps1按既有协议修正并保留全部实际三pin，未降低产品校验。

0.5CPU/768MiB/memory-swap=memory/cgroup swap0，单worker、nice19/ionice idle、pids128、network none、只读根/源及1800/1830/1880秒保持。规范流256MiB、应用临时1GiB、chunk2MiB/4096行/fan-in16/最多1024文件均未提高。没有文件系统硬配额或硬IO带宽隔离。

监督峰值130527232字节（约124.5MiB，包含cgroup记账）；docker stats运行时约55MiB不能代替该峰值。容器交换及宿主pswpout始终0、OOMKilled=false，健康采样均通过，IO PSI avg10最高0.68、内存PSI最高0。停止由截止触发，无资源压力停止证据。

主机boot_id为6c2e67e4-0993-4283-a460-46a288a5decf，两PG同ID、StartedAt在2026-11-09T12:12:17Z附近，候选前后字节一致且healthy；收尾devwatch PID2301两次空闲。固定项目快照在roots指定路径，本轮findmnt为/dev/sda1 ext4 /，不是NAS；不把历史设备名称当源身份依据。

## 元数据失败留痕与证据

首次metadata约1.608秒在安装来源收据写入时FileExistsError：人工包装的/data/var/run路径在本任务为只读审阅目录，并已有同名收据。未调用materialize、未生成execution、未挂真实快照。此为我方B-23，不归于源数据。

仅将本轮docs包装收据改为独立可写/data/var/snapshots/run，保留v1脚本/manifest/原归档及失败目录；Windows同步新source-green-v18，独立metadata-2约3.215秒成功。卡片、真实attempt、镜像、范围和预算不变，没有第二次真实读取。活动源码/输入未改，deploy及常驻服务不动；无产品改动或新全套回归。11月8日1339开发/1316安装通过23跳过是已验证历史构建证据，不说成本轮新测试。

59个普通metadata/log/控制原件以hard-dereference归档，不含源SQLite、真实成员内容或排序值流。result-evidence-v1.tar.gz SHA256为`49b2f55c7893a61ebb38c5948640f396b5fd3aefdb2a88f90c4cb2e19615fb6f`，证据清单摘要为`083dbf70d9392f859e6a40edcd6afd6e9cfdda29cb51862b46d467c0cacaa144`，见collection.sha256。

[verify-result.ps1](verify-result.ps1)核验全部原件摘要、授权/卡片/原始三pin、对象和预算、实际安装模块/挂载/资源、监督与失败关联、PG前后基线和3候选回收，结果见[verification.json](verification.json)及[final-state.txt](final-state.txt)。授权前的关闭控制归档、无授权拒绝收据及摘要保留，不倒写历史。

本次停止在证据收尾。后续应在人工数据上验证足量吞吐和具体耗时，再决定性能方案；不得把小样本改善作为继续真实重试的充分依据，不放宽资源预算或省略摘要。下一次真实读取仍须新任务卡和明确授权；任何数据库写入前仍须通知并确认pg32b旧数据处置。

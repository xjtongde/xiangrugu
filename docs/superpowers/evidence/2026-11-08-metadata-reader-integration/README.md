# 保持逐次检查的元数据读取：正式集成与人工候选验证

2026-11-08，本轮实现及人工验证完成。真实覆盖仍为68/78，剩10表235列；Task8未完成，未冻结、未导入、未连接数据库。11月8日既有真实p01尝试已超时结束，本轮没有真实源读取，不授权重试。

## 产品变化与身份

`batch_execution.read_metadata`保留每次整条父链的`Path.is_symlink`检查、叶子stat、重新打开及有界读字节，只缓存最多32条纯词法Path元组，并合并同次类型/大小的重复stat。缺件/ENOTDIR/权限与符号链接保守拒绝顺序保持；不缓存stat、fd、字节或校验结论，不改变guard调度、阶段/发布前重核、取消/截止或资源预算。没有新增并发目录替换的原子性保证。

- HEAD：`8fbc8c97fcf1d818caddf6ab556fa82d986643ed`，脏成果保留；无提交、推送、重置、切分支或worktree。
- 产品唯一变化模块SHA256：`c0811da85d56198ee7241722935b364c340905888827a9cdd7eb1a2a6cd151a4`。
- 构建输入：[133项清单](build-inputs.sha256)，最终核验与Windows当前字节一致。
- 新test：`xiangrugu:test-metadata-reader-20261108-a`，`sha256:2e6a01b7915ad3290aa73c0071709590ef9e894cd4423926d9f4f88006a4372f`。
- 新runtime：`xiangrugu:runtime-metadata-reader-20261108-a`，`sha256:55b3f27687ea32e397d49a6fdfa010a6a862c4b6c99c471d4ef68c3fe2030696`。
- 对照旧runtime：`sha256:fed765cd793aa749bb80ece55d50d14a31c25fcda8234deefd40e40b4075d262`。未晋级任何现行镜像别名。

## 失败先行及完整回归

读取器13项覆盖新鲜字节/父链、相对路径、缺件及父符号链接顺序、ENOTDIR、权限、FIFO、增长及有界缓存：RED 2失败11通过，GREEN 13通过。固定人工大夹具新测试RED 1失败，GREEN与读取器合计14通过。

| 新回归 | metadata | remainder | fixtures | 合计 |
|---|---:|---:|---:|---:|
| 开发 | 315通过 | 1015通过 | 9通过 | 1339通过 |
| 安装 | 315通过 | 992通过/23跳过 | 9通过 | 1316通过/23跳过 |

三个分组互斥，按XML中完整测试身份排重；23跳过逐项对应四个仓库审计模块的明确原因，均在开发回归中执行通过，详见[verification.json](verification.json)。这是本轮新回归，不挪用旧775等结果。

## 人工严格路径与性能观察

固定自造10表235列，单次只执行p01的8列；小夹具1000行，大夹具只把人工p01扩至80000行，其他9表仍1000行。独立手编码frame、Counter及标准库排序生成golden，不用产品排序器/编码器生成期望。仅固定场景，无任意rows或外部数据输入。外部标记始终test_fixture_only=true、real_source_read=false；内部project_snapshot/synthetic_only=false表示协议语义，不计真实覆盖。

| 同源普通执行 | 旧runtime整程 | 新runtime整程 | 旧/新排序阶段 |
|---|---:|---:|---:|
| 1000行/8000字段 | 9.029秒 | 9.236秒 | 5.195/4.183秒 |
| 80000行/640000字段 | 493.138秒 | 404.626秒 | 487.580/400.805秒 |

新旧源字节摘要、独立黄金、计数及schema均一致；各批完整快照复核及两次文件摘要完成。大样本双方峰值chunk 4096行、667794字节，临时文件峰值33个/25759868字节，跨chunk及归并得到黄金完整结果；新/旧内存峰值87588864/87388160字节。

大样本单次整程观察下降17.95%，小样本整程未改善；未作重复统计，不把实验原型19.7%当正式收益，不把结果推算到真实p01。人工字段分布、类型和路径与真实源不同，真实1800秒内完成尚未证明。新runtime另行cProfile不覆盖产品函数：guard仍16559次，累计时间嵌套不可加总，也不代表真实耗时比例。

实际负例在首个人工源帧后触发：大样本取消得到artificial_cancel/cancelled；专用请求追加空格得到controller_request_changed。两者无最终batch、进程组消失、scratch空，失败报告摘要与监督绑定。正常源和活动源码未改变。唯一复核及负例验收修正见[review-result.md](review-result.md)。

## 资源、失败留痕与收尾

构建、测试、CLI均在32串行。候选0.5CPU/768MiB、memory-swap等于memory、cgroup swap0、pids128、nice19/ionice idle、network none、只读根与输入；沿用压力、租约、截止及停止门。Windows只编辑/同步/原生核验，私有source副本不覆盖deploy或常驻开发服务。

初次reader-prepare-small包装缺cancel-probe.py/prepare-retry.py绑定源，在Docker create前失败，无CID，失败目录保留；source-green-v5补齐依赖并加启动前检查，v6增加同源旧runtime大样本对照。所有这些是Windows同步，不在远端编辑。产品133项输入构建后未再变化；复核修正仅docs验证包装。

测试时boot ID为7eebd70b-00c3-49bd-b272-80904c308487，各候选PG前后ID/启动时间一致且健康、pswpout不增。用户暂停期间宿主重启；续接收尾boot ID为a5b5f785-8d97-4161-8369-cdfd3b0a3652，PG相同ID在2026-11-08T12:43:11Z重新启动且健康，pswpout0。两时点分开记录，不声称整个暂停期间没有重启；本代理未启动/停止服务。

[verify.ps1](verify.ps1)原生核验937原件摘要、133当前输入、回归/跳过/安装来源、黄金、资源限额、监督及24候选回收；[cleanup.txt](cleanup.txt)记录归档后精确realpath边界检查和44个人工临时路径清理。源码包、私有code、镜像及证据保留。raw.tar.gz SHA256为`d454eab09804608f462f2e0cf9b3bc6b4829ad3ed632c65b182ba1b02a1970d0`；摘要清单绑定见[collection.sha256](collection.sha256)。不归档人工SQLite、排序帧、真实源件或测试临时树。

计划裁决完整保存在[ledger.md](ledger.md)：保留脏工作区、Windows原生记账、采用保守is_symlink顺序、固定80k人工夹具、复核仅修验证包装、只改专用负例请求。无延期Minor。下一步是据此准备新真实读取任务卡并另获具名授权；不得自动重试，任何数据库写入前仍须通知并确认pg32b旧数据处理。

# 五件文本源侧规范值期望执行账

2026-10-08用户“同意”批准短设计：现有source_text与canonical小范围衔接、TDD、sync、32合成测试及自有候选镜像；只读已验收项目快照五件精确文本与证书，生成非执行期望/证据。禁止原NAS、数据库、正式合同覆盖/冻结、长期容器替换、Git提交推送。

技能：TDD和karpathy用于最小实现与独立黄金；worktree技能服从既有用户禁止新工作树，原地保留脏工作区，Windows只编辑不执行Python。无新依赖，不并行派实施Agent。

步骤：1 合成RED→最小衔接GREEN；2 固定候选镜像完整测试；3 原始摘要/头部/列映射/数量严格核验后五件源侧值期望；4 回传SHA、文档和评审。任何失败不返回成功前缀期望。

基线：HEAD 1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05；32可用194550448128B，load .18/.23/.27；前批固定test镜像393通过；dev/pg32/pg32b身份/StartedAt未变。

状态：本批完成。只核验证书及所选五件，不称全快照前后校验；BLOCKED及ready_for_import不放行。

实施：纯函数26 RED（模块缺失）→411累计单元；批准元数据20 RED（接口缺失）→431累计单元。开发证据探针独立路径/链接/预算/旧摘要7项合成核验后438累计单元。探针是开发验证脚本，不称生产文件读取器或导入适配器。

独立静态评审：本批text_values.py、test_text_values.py和探针无Critical/Important；评审未执行测试或真实源。未判全快照不变、冻结/数据库/完整Task9、可写不可信目录的恶意并发路径替换竞态及超出五件（最大字段890B）的CSV扩展；本批维持受控只读快照范围，不据此宣称这些能力完成。

失败证据及裁定：
- sync一次SSH Connection reset；只读重连和开发容器身份检查通过，重试成功。未改网络或服务；中断上传临时件保留，不做额外清理。
- 首次候选446项已过，但runtime smoke的跨shell字符串换行导致命令语法错；改用bytes.fromhex命令后二次整套446和smoke通过，保留首次日志，不称首次全流程成功。
- 探针20261008T125527Z因容器挂载点名snapshot不是证书快照号，在业务文件读取前拒绝；改用保留快照号的容器路径，不放宽身份检查。
- 探针20261008T125622Z因文件UTF-8-SIG与列UTF-8被错误要求相等，在业务文件读取前拒绝。这是本批衔接实现缺陷，不是源或批准合同问题。2项合成回归RED（另46通过）→最小修复后440累计单元GREEN。文件起始BOM策略单独保留；83源列codec仍严格UTF-8，不将UTF-8-SIG施加每列。原投影/决定不变，修复后最终镜像重建中。

最终验证：修复后最终test按image ID运行440单元及8契约=448通过；runtime无网/只读/非root已安装模块合成smoke与pip check通过，dev一次性help通过。测试没有源码/数据卷，真实探针只读快照/证书/三份metadata，镜像内执行脚本，无源码挂载或数据库网络。

最终候选标签xiangrugu:{dev,test,runtime}-text-source-final-20261008T125803Z，OCI created为本次实际构建时钟2026-10-08T12:58:03Z，revision原HEAD、dirty。本地Docker image ID（不是registry RepoDigest）：
- dev sha256:89a9ca2e355e431aee81006152fabaa1399b9eaadf561652f7c9ae0bd6c77c08
- test sha256:c0378c4c1477bfb2ca20f79ad7bdce8dab87447c73f058662cd1c75b391c81c8
- runtime sha256:8d63006a4eb2f5f9c8d98780297634fc1bb418f9dd07b63e9f48032d009205ad

真实探针成功运行20261008T130021Z（32 data/var/text-source-values-20261008T130021Z）：新非执行期望及所选五件数量/前后校验结论只展开于release/text-review.md最新节。第一次和第二次失败目录均保留，没有前缀成功报告。一次性探针容器均已退出/回收；长期dev/pg32/pg32b身份及StartedAt保持基线，未提升现有dev/test/runtime标签。

新证据回传目录docs/superpowers/evidence/2026-10-08-text-source-values，16份证据逐件Windows/32 SHA-256核对，清单artifact-hashes.json；源期望SHA47c2401197e557be356941842d099a27db867e707682a3ef536cee2430d7ac38。最终边界日志绑定包内代码/脚本与同步源码摘要、长期容器/旧标签未变、current不存在；磁盘剩余193942335488B。正式sources/decoding/assertions及批准投影/读取决定摘要保持基线，未提交推送。后续表名/全版本合同/真实适配器需另批；任何真实导入先通知并共同确认pg32b旧数据处置。

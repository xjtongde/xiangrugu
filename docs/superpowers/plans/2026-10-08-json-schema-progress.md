# 独立 JSON Schema 校验执行记录

授权：用户“同意”；仅代码/测试/依赖锁/交接文档、32 候选镜像及无源无库测试。
不替换长期容器、不读取真实源、不连接数据库、不冻结、不提交或推送。

基线：HEAD 1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05，main，既有 dirty 工作区。
按用户指定入口原地继续；不新建 worktree/分支。32 基线 448 passed。
Docker 29.7.2，Compose 5.4.0，磁盘可用 193944838144 字节；长期容器未变。

步骤：
1. 官方 PyPI 核实 jsonschema 4.26.0、必要依赖及 Linux amd64/CPython 3.11 wheel SHA-256。
   已加入两个锁，保留所有旧 pins；没有安装到长期 dev。
2. 新增原始文档结构、Schema 自校验、本地引用、外部引用拒绝、JSON 域及语义保留测试。
   RED：32 failed（全部缺独立 callable），0.43秒。依赖镜像已构建；
   原始日志在32 data/var/json-schema-20261008T143630Z/red.log。
   外层SSH管道exit1，但记录RED_EXIT=1；后续命令改用UTF8/base64传输避免末行CR。
3. 最小实现原始文档独立校验，再调用现有模型；不放宽 Schema 或合同。
4. 首轮候选480 passed；独立评审提出三项Important，全部合成复现后一次修复。
   最终无源码挂载候选484 passed（5.39秒）；三镜像构建、pip check及runtime smoke通过。
   初次pip check仅有只读cache警告；设置PIP_NO_CACHE_DIR=1后三份再测无警告，旧日志保留。
   两份原始合同均独立Schema/模型通过：各8,004规则、BLOCKED分别7,918/7,914；
   原始字节SHA-256不变，仍draft、ready_for_import=false、conforms=false。

Ruling：独立函数接受显式 Schema；loader 用现有 contract_schema() 导出，
测试与实测另读取镜像内静态 Schema，并检查两者相同。
因此独立性在实例验证实现，不声称 Schema 定义独立于模型；若二者冲突停止报告。

资源门：原合同文件上限 16 MiB 不变；JSON 域检查限制深度128、节点100万，
避免递归 YAML 别名和非 JSON 值进入第三方校验器。Schema 只允许片段引用；
拒绝 $id 重定基址，并显式配置禁止外部检索的 Registry。错误不得回显文档值。

评审：/root/json_schema_review，只读本批代码/锁/测试，不再派agent；没有运行项目代码。
- Important：const字面$ref误判、引用指向非Schema的异常、引用DAG展开预算缺失。
  2项正确性RED→GREEN；执行预算RED→GREEN；补充子方言切换绕过RED→GREEN。
  新增总36项，最终484全套通过。关键词调用上限200万，与输入域预算分别计数。
- Ruling：引用必须指向声明的非根Schema节点，拒绝子节点$schema，以防第三方
  evolve切回未加预算的原版验证器；现有导出Schema无需放宽或改写。
  代价：不支持根递归或嵌套方言Schema；后续确需支持必须另设计，不静默接受。
- Final: minor (deferred)：深度/节点精确阈值、非递归共享YAML别名展开缺少专项边界测试。
  现有递归别名/非JSON类型与执行预算测试不能代替这些用例。

评审未判断项及处置：
- 候选测试/镜像安装、静态Schema相等：由主agent最终镜像全套、pip check和文档报告确认，
  不以评审断言代替实测；未测部分不得报完成。
- 原始合同、源/数据库行为：原始合同由本批受控元数据报告验证；源/数据库不在授权范围，
  明确未访问，代价是本批不证明源未变或真实导入正确。
- 供应链未知漏洞：只确认官方元数据/哈希/兼容性，不宣称完成漏洞审计；未披露风险仍可能存在。

开发反馈实际影响：旧dev缺jsonschema，同步新代码后watcher收集失败，容器ID/启动时间未变。
B-15待单独部署授权；不在旧dev原地pip安装，不替换/停止/重启服务。
构建和验证通过仅属于最终候选，不属于旧dev当前环境。

最终候选：xiangrugu:{dev,test,runtime}-schema-final-20261008T144709Z；
OCI创建2026-10-08T14:47:09Z、HEAD同基线、source.status=dirty、version=0.1.0。
- dev：sha256:89f1a0978cb817871d50d6468f3dec19e3ea1e67d5bc73457a62fd10b5b8732d
- test：sha256:f9145505921ec58fe0a04ca097828c89dd48a0f356920ca1284c261f69e0c265
- runtime：sha256:a0db75fe65479bd8172fe9374cc18e3a8d109319e74b791c9a19cb294906c738
Schema原始SHA-256：bf3a9e01fd7e4a4e38f67710e45cf7d20c8d2ade91579bd742fc66482edd1e51，
未改静态定义，与模型导出相同。

三长期容器ID/启动时间与基线一致；只检查容器元数据，不连接数据库。
接续：先申请仅dev晋级授权；确认旧镜像/回退tag可寻址，再更新dev并验证真实watcher。
导入前通知与共同确认pg32b旧数据处置门继续有效；不得随部署自动导入、冻结或删库。

本批24份新生成证据已回传Windows并逐份与32 SHA-256比较一致，索引为
docs/superpowers/evidence/2026-10-08-json-schema/artifact-hashes.json。
历史证据未覆盖；静态Schema和两份正式合同字节未改。本切片实现/验证完成，部署B-15待授权。

## 随后单独授权：仅dev晋级（2026-10-08）

用户答复“同意”，授权先确认回退镜像，再仅更新xiangrugu-dev并验证真实watcher。
本节是新的部署批次，不回写上一批“未替换”事实。
Windows不运行项目代码；无源/快照读取、数据库连接/内容操作、导入、冻结或Git提交推送。

预检：HEAD仍1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05；Docker29.7.2/Compose5.4.0；
磁盘可用192958713856字节。最终候选全套重新484 passed（5.16秒）。
部署根docker-compose.yml不存在，首条预检因此exit1，未发生服务修改。
容器Compose标签确认入口为/opt/mydocker/xiangrugu/deploy/docker-compose.yml，
其SHA-256与Windows相同：67212d2871b2dd1036ec36a2feed47ef99480e528c3d6503c2ee14e528de0689。
不新建或复制第二份Compose入口；使用既有受控镜像入口。
显式--env-file /dev/null避免读取私人.env；没有读取任何凭据。

旧镜像sha256:121f86c85e784cd78d145c8bf7db36722c17472c055926f53ef096421bcd5f10，
固定回退tag xiangrugu:dev-pre-schema-20261008T153027Z。
image save成功，tar留在32工作账rollback-dev-image.tar（72228352字节），
摘要见rollback-SHA256SUMS.txt；旧tag一次性无网络/nonroot运行包导入通过。
这是镜像回退资产，不包括挂载工作树/持久数据，也不声称旧依赖兼容当前新工作树；
实际回退须先处理代码/依赖一致性并另获授权，不能单独回退镜像后宣称反馈已恢复。

晋级：仅xiangrugu:dev别名切到本账最终dev候选，test/runtime别名不变。
compose --profile dev up -d --no-deps --no-build --pull never --force-recreate dev；
未启动其他服务、未拉镜像、未修改挂载/权限/依赖或生产数据。
新容器ID29795c60ae15d85c4ba877dad78dcbd288d792a2d0df6e2d4d72f677201788e6，
启动2026-10-08T15:30:32.106799784Z；镜像89f1a0978cb817871d50d6468f3dec19e3ea1e67d5bc73457a62fd10b5b8732d。
仍UID10001、/workspace、readonly rootfs、network none，只有readonly源码及persistent/var挂载；
没有源或快照卷。pip check无依赖错误，jsonschema4.26.0实际可用。

真实watcher首轮476 passed（5.08秒），run1/returncode0/finished_at15:30:38Z。
484完整候选=476unit+8container；不混淆这两个测试范围。B-15恢复。
pg32/pg32b容器ID、镜像与启动时间和预检完全一致，未连接数据库。
证据目录docs/superpowers/evidence/2026-10-08-dev-schema-promotion；
32工作账/opt/mydocker/xiangrugu/data/var/dev-schema-promotion-20261008T153027Z。
下一步同步本批交接文档，验证真实watcher第二轮自动触发及通过后回传摘要。

第二轮正常同步已验证自动触发：run2/returncode0/finished_at2026-10-08T15:33:06Z，
476 passed（4.83秒）；未再次up或重启。B-15恢复包含实际热反馈，不只首次启动。
回退tar SHA-256：094b302b473dea4ee4cb5140ef628416de801e9e8aacb2e09ceb5c72c0d6a575。
19份新部署证据回传Windows并逐份SHA-256比对，索引保存在本批证据目录artifact-hashes.json；
tar只留32不入Git。两个数据库容器以及test/runtime别名前后断言不变。
部署批完成；仍无真实导入、源验证、冻结或Git操作。本批不授权进入其他载体或源读取。

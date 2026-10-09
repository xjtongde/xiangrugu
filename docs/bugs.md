# bugs.md —— 我方缺陷账

> 状态：现行｜as_of 2026-10-06

本账只记录我方实现或资产的缺陷。源数据自身的已确认现象见 `docs/cbdb.md`，不得混入修复队列。

| 编号 | 缺陷 | 状态与影响 |
|---|---|---|
| B-03 | Gitea 1.27.1 Wiki API 写正文异常 | 未修；Wiki 非权威，不阻塞导入 |
| B-04 | Gitea 1.27.1 Wiki API 读取 CJK 页名返回 404 | 未修；Wiki 非权威，不阻塞导入 |
| B-13 | `demo/` 页面数字未随数据变化重建 | 候授权；演示不在导入执行链上 |
| B-14 | CRS镜像重建前未先固定旧dev回退tag，运行中旧镜像摘要无法寻址 | 部署阻断已恢复：授权export/import救急备份核验后仅更新dev；原manifest/构建历史未恢复，防漏自动化尚未实现。事实见首版release/spatial-review.md最新节 |
| B-15 | 同步新依赖代码后，旧dev缺少jsonschema，watcher测试收集失败 | 已恢复：2026-10-08用户单独授权仅dev晋级，旧镜像导出/可运行验证后重建；真实watcher476项及pip check通过。事实及后续自动重测证据见JSON Schema执行账，未原地安装依赖、不操作数据库 |

历史装载缺陷已经提炼为 `datamgmt/docs/PITFALLS.md` 的自动拦截要求，不在本账重复展开。当前导入实现缺口统一列于 `datamgmt/README.md`；只有实际实现偏离已批准合同后，才在此新增缺陷。

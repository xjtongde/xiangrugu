# JSON Schema dev 晋级证据

用户“同意”授权：确认回退镜像后，仅重建xiangrugu-dev并验证真实watcher。
不读源/快照、不连接数据库、不冻结、不导入、不提交或推送。
完整事实统一见 ../../plans/2026-10-08-json-schema-progress.md 的 dev晋级节。

32工作账：/opt/mydocker/xiangrugu/data/var/dev-schema-promotion-20261008T153027Z。
旧镜像导出tar留在32，不复制进Git；此处仅保存其摘要、命令日志和状态证据。
旧镜像回退标签不等于当前新工作树的兼容回退，不能以回退镜像单独保证watcher通过。
容器元数据仅证明同机数据库容器未变，不声称完成数据库内容审计。
官方命令依据：
- https://docs.docker.com/reference/cli/docker/compose/up/
- https://docs.docker.com/reference/cli/docker/image/save/

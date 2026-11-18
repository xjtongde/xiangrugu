# AGENTS.md —— 香如故项目入口

本文件供 Codex、DSH 及其他 AI/开发者进入项目时使用。

## 1. 项目目标

把唯一权威数据源 `/mnt/wd61workmetadata/usedata` 忠实、完整、可重复地导入 32 主机的 `pg32b` PostgreSQL 实例，新建目标数据库 `xiangrugu`。

成功标准：

- 每个源成员都有明确处置，不能静默遗漏；
- 数据库中的结构和值能由独立验证器追溯到源字节；
- 同一版本的源、配置和 Git 提交可重复得到同一结果；
- 导入过程不得修改源件，不得影响同机 `pg32` 生产实例；
- 验收结论由机器可读证据支持，而不是由旧库或叙述性日志支持。

现有 `pg32b/cbdb`、`pg32b/cbdb_reh` 保留，仅供观察，不是来源、基线或验收依据；删除、清空、改名或覆盖必须另获用户明确同意。

## 2. 当前角色

当前分工为 Codex 总协调与独立只读验收，DSH 执行；DSH 指令由茶香转发。茶香明确授权 Codex 修改的事项按该次范围执行，本次文档整理属于此类授权。操作边界见 `rules.md`，当前进度统一见 `datamgmt/docs/IMPORT-PACKAGE-TODO.md`。

## 3. 开发与执行位置

- Codex 和 DSH 各自使用自己的 clone；共享文档以仓库根为路径基准，个人 clone 的绝对路径只记在本机文档。Windows 不安装或运行项目 Python、Docker 测试或服务。
- 项目文档只通过 Gitea 对齐，双方分别使用自己的账号提交。执行纪律见 `rules.md` R-10/R-11；未经茶香明确授权，不直接改写其他工作区的文档。
- 32 主机 `/opt/mydocker/xiangrugu/deploy` 是受控运行目录；接收经核对的 Git 版本，不直接形成未回传 Git 的独立修改。
- 所有构建、测试、CLI 和常驻开发进程都通过 SSH 在 `root@192.168.3.32` 执行。
- 常驻开发容器固定为 `xiangrugu-dev`，工作目录 `/workspace`；数据接入只是同一项目中的首个低频模块，不是独立项目。
- DSH 在 38 使用自己的 clone，当前交付分支为 `dsh/p01-real-prep-20261113`。工作树保持原状，通过 Gitea 交付与接收；不同 clone 的已提交和未提交成果分别核对，不能视为已自动同步。

## 4. 阅读顺序

```text
AGENTS.md
→ rules.md
→ docs/index.md
→ datamgmt/docs/IMPORT-PACKAGE-TODO.md
→ datamgmt/README.md
→ datamgmt/docs/DESIGN.md
```

按需查阅：`datamgmt/docs/OPERATIONS.md`、`datamgmt/docs/PITFALLS.md`、`datamgmt/config/roots.yaml`、`docs/cbdb.md`、`docs/codemap.md` 和三本专职账。

如文档、配置、代码或实际环境互相冲突，停止推断，记录冲突并按 `docs/index.md` 的权威顺序处理。

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

现有 `pg32b/cbdb` 仅供观察，不是来源、基线或验收依据；最终将删除，但删除数据库必须另获用户明确同意。

## 2. 当前角色

Codex 默认承担审计与实现协作：先核实事实，再按用户授权修改。操作边界见 `rules.md`。

## 3. 开发与执行位置

- Windows 工作区 `C:\Users\zkyxy\Documents\codex-xiangrugu` 是当前 Git 修改入口；不得在 Windows 安装或运行项目 Python、Docker 测试或服务。
- 32 主机 `/opt/mydocker/xiangrugu/deploy` 是该工作区的受控运行镜像；只由同步流程更新，不在远端直接形成未回传 Git 的独立修改。
- 所有构建、测试、CLI 和常驻开发进程都通过 SSH 在 `root@192.168.3.32` 执行。
- 常驻开发容器固定为 `xiangrugu-dev`，工作目录 `/workspace`；数据接入只是同一项目中的首个低频模块，不是独立项目。

## 4. 阅读顺序

```text
AGENTS.md
→ rules.md
→ docs/index.md
→ datamgmt/README.md
→ datamgmt/docs/DESIGN.md
```

按需查阅：`datamgmt/docs/OPERATIONS.md`、`datamgmt/docs/PITFALLS.md`、`datamgmt/config/roots.yaml`、`docs/cbdb.md`、`docs/codemap.md` 和三本专职账。

如文档、配置、代码或实际环境互相冲突，停止推断，记录冲突并按 `docs/index.md` 的权威顺序处理。

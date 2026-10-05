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

## 3. 阅读顺序

```text
AGENTS.md
→ rules.md
→ docs/index.md
→ datamgmt/README.md
→ datamgmt/docs/DESIGN.md
```

按需查阅：`datamgmt/docs/OPERATIONS.md`、`datamgmt/docs/PITFALLS.md`、`datamgmt/config/roots.yaml`、`docs/cbdb.md`、`docs/codemap.md` 和三本专职账。

如文档、配置、代码或实际环境互相冲突，停止推断，记录冲突并按 `docs/index.md` 的权威顺序处理。

# features.md —— 新能力账

> 状态：现行｜as_of 2026-10-25

## 当前项目

| 编号 | 能力 | 状态 |
|---|---|---|
| F-13 | 建立长期数据接入模块，将 `usedata` 忠实发布到 `pg32b/xiangrugu`，支持换版和新增来源 | 当前先收口六块整理与映射；待办和讨论统一见 [进度文档](../datamgmt/docs/IMPORT-PACKAGE-TODO.md)，全量发布按 DESIGN 验收 |
| F-14 | large单表子任务准备与独立覆盖核验 | 人工单表闭环已验证，真实协议接线见F-15；真实覆盖68/78、Task8未完。见人工链证据（历史路径 `superpowers/evidence/2026-10-15-partition-coverage/README.md`） |
| F-15 | 真实large单表受控执行与离线覆盖 | 11月9日新runtime的p01唯一真实attempt c仍1800秒timeout，无完整批/新期望；59原件核验、3候选回收、scratch空、PG健康。仍68/78、Task8未完，本次授权已用，不自动重读；先人工验证足量吞吐（I-07）。见[本次真实终态](superpowers/evidence/2026-11-09-real-p01-attempt/README.md)及[人工集成证据](superpowers/evidence/2026-11-08-metadata-reader-integration/README.md) |

## 后续候选，不属于当前导入范围

| 编号 | 能力 |
|---|---|
| F-01 | 地名主表及溯源字段设计 |
| F-02 | 简繁归一管线 |
| F-03 | 面向应用层的溯源规范 |
| F-04 | 向量检索层 |
| F-05 | LLM 消歧、系年和实体链接 |
| F-06 | 行迹、诗文和关系网络等内容产品 |
| F-07 | 钱币与经济史资料 |
| F-08 | 文言语料与工具书接入 |
| F-10 | Hartwell 宋辽金官员 GIS |
| F-11 | 古籍自动标点工具 |
| F-12 | 全元文、书院及传教士资料 |

这些候选不得改变本次保真导入的数据，需由用户另行立项。

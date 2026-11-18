# import-plan.md —— 数据接入模块入口

> 状态：现行指针｜as_of 2026-11-19

数据导入不是项目级一次性迁移，而是 `datamgmt/` 长期子系统。为避免项目文档与模块内部形成双账，本文件不再展开方案。

权威入口：

- 最终设计、数据合同、验证与发布：`datamgmt/docs/DESIGN.md`；
- 当前阶段、六块数据整理待办与讨论结论：`datamgmt/docs/IMPORT-PACKAGE-TODO.md`；
- 首次构建、后续更新和失败处理：`datamgmt/docs/OPERATIONS.md`；
- 历史失败模式与强制拦截：`datamgmt/docs/PITFALLS.md`；
- 模块现状与实现缺口：`datamgmt/README.md`；
- 源根及目标实例：`datamgmt/config/roots.yaml`。

当前先完成全量导入包与映射六块工作；具体状态只在上述进度文档维护。模块设计中的“阶段 0–6”和工程计划的“Task 1–18”是不同编号，均不能冒充六块整理的完成比例。

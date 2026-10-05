# import-plan.md —— 数据接入模块入口

> 状态：现行指针｜as_of 2026-10-06

数据导入不是项目级一次性迁移，而是 `datamgmt/` 长期子系统。为避免项目文档与模块内部形成双账，本文件不再展开方案。

权威入口：

- 最终设计、数据合同、验证与发布：`datamgmt/docs/DESIGN.md`；
- 首次构建、后续更新和失败处理：`datamgmt/docs/OPERATIONS.md`；
- 历史失败模式与强制拦截：`datamgmt/docs/PITFALLS.md`；
- 模块现状与实现缺口：`datamgmt/README.md`；
- 源根及目标实例：`datamgmt/config/roots.yaml`。

当前阶段仍是阶段 0：冻结首个 release 的完整导入合同。任何开发应从上述模块文档进入。

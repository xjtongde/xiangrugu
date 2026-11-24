# 首批七项 PG 装载器候选与分批门验收 · lead 记录（30 分钟盒）

- 起表 18:13:02 UTC，硬停 18:43:02。基线 698a07138b6265d1b16f704d0b73e634049a7ee8。授权=候选分支实现测试+32 独立临时 PG/PostGIS 试装；生产接收/写库另批。lead 收口（a02 起始失败惯例接管披露）。

## 交付
1. **范围合同草案**（first-batch-scope.draft.json）：绑冻结合同 canonical ba8118fb…/原清单 fb5e6b33…/两核销证据 5dd1739c…+623723ff…/七项对象身份（schema.table）；**mode isolated-test**（审批 ref 明示 isolated-test-only-not-a-production-approval@698a071）；**full_ready_for_import=False 保持/uncovered_members=7995 不动**；实例策略（镜像 d562e436…/--network none/无端口/唯一名/禁 pg32/pg32b）。
2. **装载器候选**（datamgmt/src/xiangrugu_datamgmt/first_batch_loader.py，stdlib+canonical，同一入口）：门序=scope 审批→合同/清单/证据摘要绑定→实例身份（生产库可见先拒）→目标已存在 fail-closed（**CREATE TABLE 无 IF NOT EXISTS，绝不覆盖**）→**单事务 BEGIN→schemas/extension/DDL/COPY×7→事务内全量回读（行数/列元 5 字段/attr+geom 摘要重建/重复组与额外行/rownum 序）→全合 COMMIT 否则 ROLLBACK 零残留**；重试重跑全门。几何流 XRGGEOM-v1（0x52 记录标记+0x45 尾计数）；空间属性 text 投影 column_id 法；N 值 width/scale 重建。
3. **单测 14 条全过**（test_first_batch_loader.py，FakeSession）：正例 47725/63/74 单事务；缺审批/合同摘要不符/证据摘要不符/实例不符/生产库可见/目标已存在/回读不一致 ROLLBACK 零残留/失败后重试干净成功/全量 ready 翻正拒/production 模式拒/7995 漂移拒/对象身份不符拒/DDL 无 IF NOT EXISTS。
4. **32 真试装**（trial_driver.py，host 32 stdlib，复用已审读件法）：临时唯一名容器 **xiangrugu-loader-trial-20261124-182217-041b5267**（Id 1aa28898e4fde869…，镜像 pg32b-full:18-pgdg==d562e436 核，--network none 无端口）；源侧门先于写（5 文本 sha/行数+2 空间 attr/geom/DBF 身份）；**TRIAL_EXIT=0 FIRST_BATCH_TRIAL_LOAD_PASS**：**47725 行**（59/59/29/3389/2957/40199/1033），七摘要全合已批锚（3519649f/a2ad2d24/ff7081a0/3c606784/b3f6ceb6/3bad44a0/475ea1d8/dcbedb5a/d233ed9c），列元全合，**m008003 63 组 74 额外保留**，单事务 committed。
5. **活体反例**：二次装载→**target_already_exists 拒+零突变**（47725 不变）；错误实例身份→**instance_identity_mismatch 拒**。
6. **回归八套 R10_EXIT=0 stderr 0B 186 passed**（172 旧+14 新）。

## 过程披露（环境/实现修正，非交付缺陷）
- ValueColumn.column_key 须 digest/ROW_KEY；合同 columns=纯值列 rownum 在 derived_rownum；合同 JSON schema 别名归一化；XRGGEOM 记录标记/尾计数补齐；DBF 字段 length 键；CSV 空串 "" 引号面解析；PG initdb 临时服务器就绪竞态→双重探测；docker cp 异常→exec 管道；三失败容器（4750def3/a811d980/c78afa81+ed57d130）均本盒创建经 Id 核后清除。
- 回归首两轮 36 failed 系隔离树缺 contracts/config/证据目录（环境性），补送即 186 全过。

## 边界
源件只读；deploy 未更新；现役镜像/服务未改；**生产 PG 未连接**（仅本盒临时唯一名实例）；M=2 未触；全量 ready_for_import=false 保持；**isolated-test 审批≠生产装载授权**。试装容器保留供 a03 独立回读，复核窗口后经 Id 清理。

## 首个剩余缺口
生产装载授权事件（另批）+装载器候选经 Codex 独立验收→正式接收链；7995 未覆盖成员处置扩展。

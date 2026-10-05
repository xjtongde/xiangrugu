# datamgmt 操作生命周期

> 状态：已批准操作契约，CLI 尚未实现｜as_of 2026-10-06

本文件规定模块实现后的唯一操作顺序。当前命令是接口契约，不代表现有代码已经支持；在实施和测试完成前不得用于正式数据。

## 首次构建

```bash
python -m xiangrugu_datamgmt inventory --release <release_id>
python -m xiangrugu_datamgmt contract build --release <release_id>
python -m xiangrugu_datamgmt contract check --release <release_id>
python -m xiangrugu_datamgmt import --release <release_id> --database xiangrugu_sample
python -m xiangrugu_datamgmt verify --release <release_id> --database xiangrugu_sample
python -m xiangrugu_datamgmt rehearse --release <release_id>
python -m xiangrugu_datamgmt publish --release <release_id>
```

`publish` 只有在两次全量彩排均为 `CONFORMS` 时才允许继续，并且创建数据库、写正式库和开放权限仍须取得用户明确授权。

## 数据更新或新增来源

1. 用户先确认新源应进入 `usedata`；源件本身只读；
2. 创建新的、不可变的 `release_id`；
3. 运行 `inventory`，生成新 manifest；
4. 运行 `diff --from <current> --to <new>`，审阅新增、改变、删除和镜像变化；
5. 生成并审阅新合同；
6. 从当前 `usedata` 完整重建影子 schema；
7. 完成两次彩排和全闸验证；
8. 获得授权后发布并切换 `current.yaml`；
9. 保留上一版 retired schema，清理须另获授权。

计划命令：

```bash
python -m xiangrugu_datamgmt diff --from <old_release> --to <new_release>
python -m xiangrugu_datamgmt status --run-id <run_id>
python -m xiangrugu_datamgmt cancel --run-id <run_id>
```

## 失败处理

- 合同不完整：停止在导入前；
- 对象导入失败：回滚该对象事务，记录 `FAILED`；
- 验证失败：禁止发布，保留结构化证据；
- 运行中断：由同一 `run_id` 恢复或清理，不能新开无关联修补任务；
- 资源门槛触发：自动暂停，不自行修改主机或数据库参数；
- 正式发布失败：事务回滚，稳定 schema 保持原版本；
- 已发布版本需回退：使用保留的 retired schema，执行前另获授权。

## 禁止操作

- 直接修改 `usedata`；
- 直接执行源 SQL 到正式库；
- 以旧 `cbdb`/`cbdb_reh` 生成期望值；
- 对正式业务表做临时 `UPDATE`/`DELETE` 修补；
- 跳过 `BLOCKED` 或未登记成员；
- 只有一次彩排就发布；
- 未经授权创建、删除、重建数据库或切换正式 schema。

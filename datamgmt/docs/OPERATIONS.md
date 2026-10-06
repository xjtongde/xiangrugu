# datamgmt 操作生命周期

> 状态：已批准操作契约，CLI 尚未实现｜as_of 2026-10-06

本文件规定模块实现后的唯一操作顺序。当前命令是接口契约，不代表现有代码已经支持；在实施和测试完成前不得用于正式数据。

## 运行形态与目录

香如故以自有版本化镜像长期运行，项目代码进入镜像；生产环境不挂载宿主机源码。宿主机部署根为 `/opt/mydocker/xiangrugu`，长期数据在其 `data/` 子目录，容器内对应 `/data`。容器通过 PostgreSQL 标准协议连接外部 `pg32b`，不得把项目代码写入数据库镜像，也不得依赖 SSH 或 `docker exec pg32b` 作为应用传输层。

`usedata` 只在导入相关操作期间临时出现：

1. 保持全局 CIFS 挂载不变；它在 2026-10-06 实测为 `rw`，不得直接暴露给导入容器；
2. 获得授权后，把 `/mnt/wd61workmetadata/usedata` bind 到 `/opt/mydocker/xiangrugu/data/imports/usedata`，再把该项目专用 bind mount 重挂为 `ro`；
3. 在宿主机和长期容器内分别确认 `/data/imports/usedata` 是独立只读挂载，而不是普通目录或仅靠文件权限“看似只读”；
4. 运行 inventory、contract、import、verify 或 rehearsal；
5. 完成 G0 后置检查并确认无进程占用；
6. 获得授权后卸载项目专用 bind mount；项目容器继续运行，常态功能只使用已发布数据库和项目持久数据。

镜像构建、容器替换、挂载和卸载均会改变宿主机状态，每次执行前必须报告目标、影响、停止条件和恢复方式并取得明确授权。

## 镜像晋级

代码变更按以下顺序晋级，不允许在运行中容器里直接修补：

```text
Git 工作区 → 构建候选镜像 → 镜像内单元/集成测试
→ 记录 Git commit 与镜像 digest → 替换长期容器 → 健康检查
```

持久目录不进入镜像。候选镜像测试失败不得替换长期容器；替换失败时使用上一镜像 digest 恢复，不能靠重新挂载旧源码回滚。

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
- 在生产环境挂载宿主机源码覆盖镜像代码，或直接修改运行中容器的可写层；
- 修改第三方源码、第三方镜像或第三方容器内部文件来实现集成；
- 在 `usedata` 未被证明为独立只读挂载时启动导入，或把项目输出写入其挂载点。
- 修补、截断或重写源内校验账；已知 `SHA256SUMS-b2` 尾部 NUL 异常必须按原字节留证并由固定摘要合同显式处置。

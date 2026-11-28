# D3 单点修复：lead 独立核验

基线 `bdb1371`｜运行时起点 `a5d12b1`｜修复提交 `9f78610`｜PIN/镜像 `0deb35f`

## 一、修复形态（独立核验 ✅）
```python
L282  ddl = ddl_for(target, create_schema=create_schema)
L295  "ddl": ddl,
L298  session.execute(ddl)
```
`grep 'ddl_for('` 仅剩定义处 L205 + 调用处 L282，**建一次、两处共用**，消除证据与执行分歧的可能。
formal 路径 `create_schema=False` 只建表；isolated 路径保留 `CREATE SCHEMA`。

## 二、红绿对照（lead 独立复跑，与 a02 报告一致）
用**同一份测试文件**分别打在修复前后 loader 上：
```
RED   (bdb1371 修复前)  2 failed, 3 passed
      FAILED test_formal_execute_sends_no_create_schema
      FAILED test_evidence_ddl_matches_executed_statement
GREEN (9f78610 修复后)  5 passed
```
失败的两条正是关键断言，**测试驱动的是真实入口 `_load_and_verify`**，
不是自己调 `ddl_for(..., create_schema=False)`——a02 第一版测试正是犯了这个错（假红），已自纠。

## 三、工件三方一致（独立核验 ✅）
| 载体 | loader 摘要 |
|---|---|
| 仓库 `git show 9f78610:...` | `802088c0bb0ea260af5b308c1da273b0ac9723679c82d888bdd96b58de6b0f47` |
| 镜像 `/usr/local/.../cbdb_social_addr_loader.py` | 同上 |
| `PIN_MODULES.json`（16 条目） | 同上 |

镜像完整摘要：`sha256:2ba6c23602bc1e176607ab8d56fa53f0110b6a33ac2fff25f205837626350d03`
tag `xiangrugu:load-cand-a02-d3`；镜像内 `/usr/bin/psql` 可执行 ✅

## 四、真库用例（a02 交付，lead 阅证未复跑）
隔离实例预建 `cbdb` schema；测试角色 `d3_loader` 有 schema USAGE/CREATE、
**无 database CREATE**（`has_database_privilege(...,'CREATE')=f`，与生产 `xrg_loader` 同形）：
```
executed OK / regclass -> 目标表创建成功
rollback 后 -> ABSENT
发送语句含 CREATE SCHEMA -> False
```

## 五、装载入口修正（关键）
原 `COMMAND-FORMAL.txt` 用 `docker exec … xiangrugu-dev`，但 **dev 容器无 psql**，
该命令在自指定容器里必崩（上一盒实测 `FileNotFoundError: 'psql'` exit 1）。
`COMMAND-FORMAL-v2.sh` 改为 `docker run` 候选镜像，并新增第 0 步自证：
```python
assert str(p).startswith('/data/var/'), 'PYTHONPATH 未生效：解析到镜像 site-packages'
assert 'ddl = ddl_for(target, create_schema=create_schema)' in p.read_text(), 'D3 修复不在'
```
**这道检查是必要的**：a02 实测曾因挂载源少一层导致容器内 code 目录不存在，
Python 静默退回镜像 site-packages 那份码，而证据里看不出异常。

## 六、a02 自报差错三项（采纳，均为真实手法风险）
1. **第一版测试是假红**——绕过真实入口，打修复前代码照样通过
2. **挂载源少一层致 PYTHONPATH 静默失效**——由第 0 步探针抓出
3. **abandoned COPY 会话持锁**致后续用例挂起——COPY 协议下不写完 `\.` 会占住服务端会话

## 七、边界（独立核验 ✅）
未改生产权限、**未执行生产装载**（只跑到 preflight）、生产凭据/角色/schema 未动、未连 pg32。
生产现场：目标表 **ABSENT**、`cbdb` 对象 0、库集合 `postgres,template0,template1,xiangrugu`、
secret `-r-------- root:root` 在位、`xrg_loader` `super=false`、隔离残留 **0**。
M=2 保持未暂存，未用 `git commit -a`，未改写历史。

## 八、首个差异
a02 首个差异为其自查中的「挂载源少一层导致 PYTHONPATH 静默失效」——
发生在验证阶段而非装载阶段，已由第 0 步探针固化防护。
**本盒未发现新的阻塞级差异。**

## 九、待 Codex 裁定
证据已齐：修复形态、红绿对照、三方摘要一致、真库三件事实证、装载入口修正。
**正式重试尚未执行**，等 Codex 独立验收后裁定。

# B 批正式装载（Codex 放行的一次）——REFUSED，已停报，现场保留

`LOAD_EXIT=2`｜`outcome=REFUSED`｜用时约 4 分钟｜基线 `234c068`｜运行时 `9f78610`

## 结果
```
{"outcome": "REFUSED", "exit_code": 2,
 "evidence": "/data/var/b-batch/evidence-formal-d3.json"}
INNER_EXIT=2
LOAD_EXIT=2
refusal.error_code = instance_marker_mismatch
refusal.detail     = instance_marker_mismatch: 3d93fc7741f66f1f01aa250b25c4959addfe4c84df22ecbd0d0f82c13920c1fc
target_probe_after = {"measured": true, "residue_rows": 0, "target_table_present": false}
```
**零写入、现场原样保留**（未重跑、未删表、未覆盖）：
```
target table : ABSENT
cbdb objects : 0
marker       : 3d93fc7741f66f1f01aa250b25c4959addfe4c84df22ecbd0d0f82c13920c1fc   （未变）
databases    : postgres,template0,template1,xiangrugu                              （未变）
```

## 🔴 首个差异：是我带错工件，不是代码问题
拒绝值 `3d93fc77…` **正是生产实例的正确 container id**（live marker 实测一致）。
门禁却判它 mismatch —— 因为**期望侧根本没有这个键**：

我这次用的 `formal-expected.runcopy.json`（sha `0a756a6a…`）是上一盒从
`git show 91746fe:…formal-expected.json` 取回的**原件**派生的，只改了 `inet_server_addr`。
而 `dab4305` 早已给该文件补上 formal 门禁所需的三键：
```
keys @ dab4305 : container_id, databases, dbname, image_id, in_session_port,
                 inet_server_addr, instance_marker_verified, server_version
  dbname                   = xiangrugu
  in_session_port          = 5432
  instance_marker_verified = 3d93fc7741f6…      ← 我的副本缺这三项
keys @ 我的副本: container_id, databases, image_id, inet_server_addr, server_version
```
`check_instance_identity` 在 formal 分支比较
`observed["instance_marker_verified"] != expected["instance_marker_verified"]`，
后者为 `None` → 必然不等 → 拒绝。**detail 打印的是 observed 值**，所以看起来像"标记不对"，
实际是"期望里没有可比对的标记"。

讽刺的是：**这正是我上一盒复述过的 `dab4305` 教训**——"改了判断但批准工件没跟上，
拒绝点只是平移"。我自己又犯了一遍：把修复前的陈旧工件形状带了回来。

## D3 修复本身有效（本次得到正面证据）
上一盒死在 `session_eof: permission denied for database xiangrugu`（CREATE SCHEMA 被拒）。
本次**没有再出现该错误**，说明 L289 漏传参数的修复确实生效；装载得以继续走到身份门禁，
并在那里因工件缺键被干净拒绝，`target_probe_after.measured=true`、残留 0 行。
即：**门禁现在报的是可诊断的 gate code，而不是会话崩断**。

## 修法（一行数据准备，不需改码）
用 `dab4305` 及之后的 `formal-expected.json`（含三键、且 `databases` 已是生产真实集合）
重新派生运行副本，仅按实测调整 `inet_server_addr`；或确认 `code7` 树里那份就是交付版。
注意 `dab4305` 版 `databases = cbdb,cbdb_reh,postgres,template0,template1,xiangrugu`，
而生产现已删除 legacy 两库，实测为 `postgres,template0,template1,xiangrugu`——
若沿用 dab4305 版还需同步这一项，否则会撞 `instance_identity_mismatch: databases`。
**我没有自行改动固定工件**，等 Codex 定夺。

## 边界遵守
未重跑装载、未删表、未覆盖、未改生产权限、未新建角色/schema、未连 pg32、
未更新 deploy、未重建镜像、未跑全仓测试。口令未上命令行、未入日志/Git。
逐个 git add，M=2 保持未暂存，未改写历史。

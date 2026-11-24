# 32 受控接收 · lead 记录（30 分钟盒）

- 起表 17:22:57 UTC，硬停 17:52:57。授权执行受控接收。来件固定 f546783f88b8cc0440d4288fc40f22765094ff27；冻结候选形成提交 6eb7691bd4dddcc689bd12a63fc8b18890414ca5（git merge-base 核为来件祖先）。lead 执行收口，a03 独立复核。

## 执行链
1. **接收前清单重算**：deploy find+sha256sum 重算→**62737bd0c16ac23f…==预检清单，7719 文件，零漂移**。
2. **R0 快照（deploy 之外）**：/opt/mydocker/xiangrugu/reception-20261124/R0.tgz，**sha 4833c60d9bce1790…**（14976032B）；gzip -t OK；tar 内 7719 文件；权限记录（7266×666/453×644/959 目录 755/65 目录 700，root:root，deploy 755）；**恢复干跑**：解至 /tmp/r0-verify 重算清单==62737bd0 cmp 逐字节等→**R0_RESTORE_VERIFIED，实测 R0 为回退依据**。
3. **来件取得**：32 无 Gitea 凭据（host key verification failed）→经 38 认证 clone fetch+ls-remote 核 f546783==分支头；git archive 管道直传 32 隔离目录（38 /tmp 中间件被清事件→改直 pipe）；archive sha 43ad4f7b…；**逐文件 git blob sha1 对账 2099/0 mismatch→BLOB_BINDING_OK（内容密码学绑定固定提交）**。
4. **隔离核对**：容器以来件 src+来件候选跑 validate_frozen→**INC_VF_EXIT=0 canonical 2dd4064250e6c4a9…==已审记录**，total 47725 all_match True，七项齐套；变更范围=123 改+1459 增+517 同值覆盖，**零删除**（deploy-only 7079 历史证据保全）。
5. **三门**：R0 可验证✓/接收范围明确（来件路径集）✓/无需改现役服务✓→**执行 overlay 接收**（tar pipe incoming→deploy，无 --delete）。
6. **接收后复核**：deploy 9178 文件；清单 sha **474d111399943ff4…**；diff==恰 1459 增 123 改 0 删→**BOUNDARY_OK**；冻结候选文件 sha 43f2cb2b… deploy==incoming 字节一致（canonical 验证传递）；**服务状态：xiangrugu-dev running StartedAt 14:58:59Z 前后不变（未重启）/镜像 89f1a097 不变/pg32b Up healthy 未触**。
7. 例外与核销：两例外（NUL/CHGIS line4）未入冻结候选；**本盒不补录例外、不签发正式核销**；不改镜像/不重启服务/不写库。

## 判定
**PASS——32 已实际接收**（overlay 至 f546783 树，边界零删除）。回退依据=实测 R0（4833c60d…）。

## 首个剩余缺口
装载授权链（loader GAP：production loader 未实现；两例外入合同+正式核销另行批准）；受控接收已完成，数据库写入仍另批。

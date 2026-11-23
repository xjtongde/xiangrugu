# m004812 隔离装载与全量回读 · lead 记录（30 分钟盒）

- 起表 17:17:50 UTC，硬停 17:47:50。基线 44e5f56（M=2 完好）。茶香明确授权。a02 起始即失败→lead 接管（披露）。
- 实施链：
  1. 32 快照只读 m004812 源件（sha cdc6d3e5…/3727B/30 行含 header/无 CR/""×24+\"×2）；读法 additional-text-reading-decisions m004812（utf-8/bom_as_signature false/backslash_escape true）；解析引号字段+双引号/反斜杠转义+尾空格 U+00A0 保留。
  2. canonical.py 源侧流核验先行：sha b3f6ceb609a853cb…==已批期望（29 行 232 字段 5605B）才允许写入。
  3. 独立临时 PG：docker run xiangrugu-trial-m004812 postgres:18-bookworm --network none（无宿主端口）；写入前实例身份核 True（server_version 18.4/PGDATA /var/lib/postgresql/18/docker/postmaster 全新/库清单仅 trial+模板/inet_server_addr null/镜像≠pg32b-full）。
  4. 最小装载路径：psql DDL（harv.trial_m004812_20261123，7 text NOT NULL+__src_rownum bigint PK）+COPY（csv 重编码）exit 0/0。
  5. 全量回读：29 行/count 29/information_schema 列名列序类型 nullable 全合/rownum [1,29]/重复 0/库值重建流 sha b3f6ceb6…==已批/5605B；TL_EXIT=0 stderr 0B first_difference None。
  6. 驱动器三处修正留证：①PGDATA 18 镜像路径 /var/lib/postgresql/18/docker（非 data）②entrypoint initdb 临时服务器竞态→身份稳定重试 ③psql -A 覆盖 --csv→旗标序 -t --csv。
  7. 接收方案补正：失效示例 InventoryManifest.load_json（API 不存在）→实际 InventoryManifest(entries/issues/checksums/limits) 构造全例；版本锚 19a7718→44e5f56；R1 checkout 44e5f56；试装单列节。
  8. 审批表三态分列：七项 formal_contract_integration_status NOT_INTEGRATED；顶层 trial_load_result 单列 separate_from_formal_approval=True；approval-table e009c2ad527228aa/生成器 35cc08cce9fd08ff 双跑全等。
  9. 回归：五套 141 passed REG_EXIT=0 stderr 0B（src 零改写）。
  10. 临时容器用后销毁（docker rm -f xiangrugu-trial-m004812）；pg32b 容器仍在运行未触。
- a03 R41 一期（期望基线独立锁定+回读驱动就绪+实例身份方案）PASS；R41b 二期独立全量回读（自写 rb.sh+json_agg 无损取回+本地流重建，零复用 lead 码）RB_EXIT=0/STREAM_EXIT=0：列规格/count 29/重复双查 0/rownum 1|29|29/流 sha match True（schema_sha 19287ad3 match）/实例身份 NetworkMode none/方案补正/三态分列/范围核全 PASS 无首个差异（integration_status 首判 0/7 系 a03 精确等值 vs 长串，startswith 复核 7/7 更正记录非交付缺陷）。
- 边界：绝不触 pg32/pg32b:5433/xiangrugu；rollup 19 件不动；src 零改写（驱动器在证据目录）；原 inventory/五块不动；M=2 未触；候选生产名未批（试装显式临时名）。
- 临时试装结果单列；正式接收/冻结/落盘/写入 pg32b:5433/xiangrugu 仍待授权。

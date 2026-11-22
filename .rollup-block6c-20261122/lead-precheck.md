# 第 6/6 块续盒（组件引用+镜像与命名裁定草案）· lead 预核（2026-11-22，30 分钟盒）

- 起表 14:33:31 UTC，硬停 15:03:31 UTC。基线 17097e850d2fcaaa870b7048e1986108933b5bfb（M=2 完好、暂存空）。
- 本轮限只读验证+草案交付；正式合并/合同冻结/32 版本化落盘/入库留后续授权。

## MapInfo 孪生漏链定位（lead 14:34–14:36 UTC 结构核）
- spatial object-mapping.json proposed_objects 中含 **components_exact_identity** 者恰 **2**：
  - sid f13db8a539baf98756a2a1c0fd6a7d520e3148661911c0133eed91427fa269f3（group ca752f78d2b5ff45…，lane mapinfo）
  - sid 5039b37adef85d98cffc972837b0cb331dabc37d320721d86fe335c8a67dfa79（group ff9ffff7dc710cf9…，lane shapefiles）
- 两案 components_exact_identity **5 件字节全同**（孪生实证）：
  | 角色 | 名 | sha256 | size |
  |---|---|---|---|
  | DAT | v3_time_pref_pgn_PRC.DAT | 3937da6c333df757… | 601,448 |
  | ID | V3_time_pref_pgn_PRC.ID | f3956a79239f2b7c… | 7,956 |
  | IND | v3_time_pref_pgn_PRC.IND | c422403b5cd9865e… | 28,672 |
  | MAP | v3_time_pref_pgn_PRC.MAP | a7b44b35a4123c7c… | 20,469,248 |
  | TAB | V3_time_pref_pgn_PRC.TAB | c7bb2a785505bd4d… | 715 |
- 现 object-index 两对象各 **bindings 3**，缺 **TAB+ID 各 2=合计 4 条**（与派工「每案五件合计补四条」吻合）；根因待 a02/a03 独立证：**TAB/ID 大写词干 V3_… vs DAT/IND/MAP 小写 v3_…**（大小写敏感 join 漏绑）。
- 对象可用字段：components_bound/twin_copy_lane/inner_zip_identity/group_id/tab_definition_verbatim/source_file_or_chain。
- **批准 2 件非本项孪生**：Ca1884route_przh_1251（9b4496c9…）/Ca1884route_przh_utf8（e601ce1a…）系 shapefile 面 6 组件（cpg/dbf/prj/qpj/shp/shx）全绑，component_binding_approved=True，勿混。

## 草案范围控制
- mirror-adjudication-draft：381 组全覆盖三分类（同字节内容复用/异字节独立版本/伴随或大小写待裁关联）；四案优先详证（V4 MDB/MapInfo 孪生/pdb2 四副本/Peking 2 件）；pdb2 与 Peking **分别**核对配准证据保留原读值；不预决合并、不同源语义不得提前合并。
- naming-draft：83 保留+1208 待分配逐件可复算候选名+2 批准单列+13 组 V4 MDB 可复算区分方案+全量联查；DRAFT_NOT_APPROVED。
- 归属账 8004 零漂移（仅 mapped_objects 增列）；五块原交付零改写。
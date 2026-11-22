# 第 6/6 块续盒三（统一镜像与命名裁定草案）· lead 预核（2026-11-22，30 分钟盒）

- 起表 14:57:55 UTC，硬停 15:27:55 UTC。基线 2b37abd50b4313eaa047bbd459eebf5730dd3de5（M=2 完好、暂存空）。
- 本轮只读核查+草案交付；正式批准/合并/落盘/入库留后续授权。复用 1311 条引用与已有读取证据。

## Peking 两案六项仿射对账（lead 14:58 UTC 预换算，原证据直取）
- 源：raster-mapping.json proposed_objects[10]（beijing_1875.zip!peking_1875_bretschneider.tif）与 [36]（CHGIS_V2.zip!shapefiles/v2_1875_peking_map.ZIP!peking_1875_bretschneider.tif）。
- wf6（world_file_declared，左上像素中心语义）：A=x_resolution=0.00051999099099355，D=rot_2=0，B=rot_3=0，E=y_resolution=−0.0005197807032760976，C=x_origin_upper_left=115.10228304632693，F=y_origin_upper_left=40.36766312627496（两案值同）。
- 换算（像素中心→左上角点）：GT=[C−A/2, A, D, F−E/2, B, E] = **[115.10202305083143, 0.00051999099099355, 0.0, 40.3679230166266, 0.0, −0.0005197807032760976]**。
- 内部 geotransform（observed.geotransform）两案均 == 换算值，**六项逐字全等**（容差 <1e-12 内精确相等）。
- 结论：tfw casefold 关联获数值佐证（换算后与内部 GT 全等）——关联确认建议可升级（证据支持），**最终确认仍留茶香裁定**；binding_basis/status 原读值不改写。

## 现 mirror-draft 孪生组缺陷（lead 结构核）
- mapinfo_twin_bound 2 组（group_id 3d1e641e…/6369b62a…）：identities 为字符串路径（非结构三元组）；**evidence_ref 误引「spatial approved_objects_verbatim（孪生绑定批准 2 组）」**——孪生实为 proposed_objects 含 components_exact_identity 之 2 件（sid f13db8a5…/5039b37a…）；批准 2 件系 Ca1884route_przh_1251/utf8 shapefile 六组件面，两者不可混。
- 修正要求：真实两案 SID+五对同角色组件（DAT/ID/IND/MAP/TAB）逐对两完整归档链+序号+size+sha；两内层 ZIP 成员自身 sha256 一致记录；案数 2/镜像对数 5/候选记录数显式区分；其余 379 组覆盖保留（381 总账不破）。
- 两案链：案A mapinfo lane V3_Data_Archive.zip!mapinfo/v3_time_pref_pgn_PRC.ZIP!组件 ord[114,*]；案B shapefiles lane …!shapefiles/v3_time_pref_pgn_PRC.ZIP!组件 ord[66,*]。五组件 sha/size：DAT 3937da6c…/601448、ID f3956a79…/7956、IND c422403b…/28672、MAP a7b44b35…/20469248、TAB c7bb2a78…/715。

## 本盒范围控制
- V4 命名统一：主表与冲突表同源派生、逐 SID 13 组 39 条全等；直接件 a2cc4039… vs 包裹件 04be983d… 两字节版本分别保留；两同摘要包裹副本各自来源身份保留；批准空间 2 件 .shp 主件派生候选名+显式候选 schema+原批准范围保留；1293 完整 schema.name 长度≤63+唯一性联查，实际冲突逐项留证。
- pdb2：三份同容器 exact-stem 绑定各自保留；V4 [159,6] 继续标配准未决（GT=null 无 wf）。
- 同字节候选共用存储方案可提（逐件来源+对象身份保留）；逻辑表合并单列供茶香裁定，不与存储复用混同。
- 归属账 8004+1311 引用零漂移；五块原交付零改写；草案不预决批准/合并。
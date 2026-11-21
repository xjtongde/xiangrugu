# 第 5/6 块 · 栅格及其他成员包（SUMMARY）

基线 git 926ed98；inventory sha256=fb5e6b334b898d62… 断言一致；32 只读探测（快照 :ro，嵌套按 ordinals 隔离流式提取，读后即删）；**未装依赖/未建新镜像/未写库/未执行源 SQL；源件零触**。

## 候选与归属
- 候选 **2522** = 块2交接 620 + 块4 Thumbs.db 1 + 无归属扫描 1901（文件 2437 + 目录 85）。
- 全 inventory 8004 对账闭合：**前四块实际归属 5482**（块1=3/块2=174/块3=5294/块4=11）+ 本块候选 **2522** = 8004（首盒「6103 已归属」系把交接面 621 件〔620 块2+1 Thumbs.db〕误计前四块——621 已在块5候选内，更正后等式机器断言在码）；unresolved 0；跨块引用 4 件逐条在 members.json（不重复认领）。
- sha256 全量流式重算 **2437/2437 ==声明值，失配 0**。

## 分类计数（逐件处置，unknown 0）
- cache **1** → NON_TABULAR
- checksum_ledger **3** → NON_TABULAR
- documentation_license **1446** → NON_TABULAR
- geo_raster **43** → IMPORT
- ordinary_image **299** → NON_TABULAR
- sidecar_companion **116** → NON_TABULAR
- structural_container **614** → NON_TABULAR
- 处置合计：{'NON_TABULAR': 2479, 'IMPORT': 43}；geo_raster 43 件 IMPORT 提案全 PROPOSED_NOT_AUTHORIZED，ready_for_import=false。
- 块5范围内同 sha 镜像候选组 **377**（合并裁定留第 6 块，本轮不选主不丢弃）。

## 地理栅格面（43/43 读通）
- 工具：现有候选镜像 xiangrugu:runtime-spatial-mapinfo-20261120-a（Id f1675321e33e…，GDAL 3.6.2 osgeo 绑定；**镜像无 gdalinfo CLI，python3-gdal 半装态如实披露**，改用 osgeo 只读探针，--network none/无凭据/无 socket/快照:ro）。
- 逐件：尺寸/波段(类型/色带/NoData/blocksize)/仿射/**源 CRS WKT 逐字**（无声明=null 不推导）/世界文件六参数 verbatim。
- 内部 GT/CRS 声明 19 件；世界文件关联回填 25 件=**精确同 stem 确证绑定 23 件**（同容器同目录同 stem，跨容器不借用）+**casefold 近似关联登记 2 件**（binding_basis 显式标 PENDING_BLOCK6，非确证绑定，语义裁定留块6）；source_member/sha256/参数语义（第五六参数=左上像素中心）/文本出处（verbatim 原文 vs parsed 规整文本）enriched，join 断言 25/25 命中；逐波段 checksum **实跑 26 件、仅登记方法 17 件**（执行留导入阶段，纯实绩不附尺寸判据）。
- ODS 改注记：CountryFilesFormat_2016-07-16.ods（ngia_dsg_codes_2017-03-15.zip!ord[2]）由 structural_container 改判 documentation_license＝字段格式说明材料（内层 content.xml 表名 Sheet1/FULL_NAME/UFI+Field Name/Type/Length/Precision/RC 单元格文本为证，text_head 已落 probe_evidence）；structural 计数随之 614。世界文件关联回填 25 件（stage B「内部 GT 即跳过」缺陷修正后一律逐字转录，GT 与世界文件并存各自引用）：23 件精确同 stem 确证绑定 + 2×Peking tfw casefold 近似关联登记（binding_basis=PENDING_BLOCK6_ADJUDICATION、binding_status=association_registered_not_confirmed_binding，非确证绑定）；真未绑定仅 1 件 .jgwx（XML 变体非六参数语法，守卫拒收）显式登记不推断。
- NoData：源未声明波段 113 个如实 null（探测脚本 GetNoDataValue 传参缺陷由 lead 令 a02 定点修复后回填，修复披露在证据）。

## 缺口与批准面
缺口 **7** 组：pdb2.TIF（真身=V4_Data_Archive.zip!shapefiles/v4_ras_1904_tibet_pts.zip!pdb2.TIF，ordinals [159,6]，sha bd56086a…；首盒误写 v4_dem_geotiff.zip 已更正）无几何声明且本容器无世界文件（同 sha 四副本合并留块6）；WMF 12 件 tool_gap 待授权；checksum 26 实跑/17 方法登记；NoData 源未声明留导入合同；inventory 历史阻断 3 项显式登记留块6；LOCAL_CS 非 EPSG 不推导；未绑定世界文件 1 件（.jgwx）显式登记，2 件 Peking tfw casefold 近似关联待块6裁定。
全部 43 栅格提案待茶香/Codex 批准；命名/装载器（PostGIS raster vs bytea）留第 6 块与导入阶段。

## 边界
本轮仅 32 只读读件+38 整理交付+Gitea；依赖/镜像/服务/数据库/历史对象处置均在授权外。entry/rehearsal M=2 保留态未触。

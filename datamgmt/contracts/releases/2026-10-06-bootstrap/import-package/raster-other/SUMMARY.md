# 第 5/6 块 · 栅格及其他成员包（SUMMARY）

基线 git 5d0c9e3；inventory sha256=fb5e6b334b898d62… 断言一致；32 只读探测（快照 :ro，嵌套按 ordinals 隔离流式提取，读后即删）；**未装依赖/未建新镜像/未写库/未执行源 SQL；源件零触**。

## 候选与归属
- 候选 **2522** = 块2交接 620 + 块4 Thumbs.db 1 + 无归属扫描 1901（文件 2437 + 目录 85）。
- 全 inventory 8004 对账闭合：前四块已归属 6103（块1=3/块2=174/块3=5294/块4=11/交接面 620+1）+ 本块候选 2522 = 8004；unresolved 0；跨块引用 4 件逐条在 members.json（不重复认领）。
- sha256 全量流式重算 **2437/2437 ==声明值，失配 0**。

## 分类计数（逐件处置，unknown 0）
- cache **1** → NON_TABULAR
- checksum_ledger **3** → NON_TABULAR
- documentation_license **1445** → NON_TABULAR
- geo_raster **43** → IMPORT
- ordinary_image **299** → NON_TABULAR
- sidecar_companion **116** → NON_TABULAR
- structural_container **615** → NON_TABULAR
- 处置合计：{'NON_TABULAR': 2479, 'IMPORT': 43}；geo_raster 43 件 IMPORT 提案全 PROPOSED_NOT_AUTHORIZED，ready_for_import=false。
- 块5范围内同 sha 镜像候选组 **377**（合并裁定留第 6 块，本轮不选主不丢弃）。

## 地理栅格面（43/43 读通）
- 工具：现有候选镜像 xiangrugu:runtime-spatial-mapinfo-20261120-a（Id f1675321e33e…，GDAL 3.6.2 osgeo 绑定；**镜像无 gdalinfo CLI，python3-gdal 半装态如实披露**，改用 osgeo 只读探针，--network none/无凭据/无 socket/快照:ro）。
- 逐件：尺寸/波段(类型/色带/NoData/blocksize)/仿射/**源 CRS WKT 逐字**（无声明=null 不推导）/世界文件六参数 verbatim。
- 内部 GT/CRS 声明 19 件；世界文件同 stem 绑定 23 件（绑定依据=同容器同目录同 stem，跨容器不借用）；逐波段 checksum ≤20MB 实跑 26 件，大件登记方法留导入阶段。
- NoData：源未声明波段 113 个如实 null（探测脚本 GetNoDataValue 传参缺陷由 lead 令 a02 定点修复后回填，修复披露在证据）。

## 缺口与批准面
缺口 **6** 组：pdb2.TIF(v4_dem_geotiff.zip) 无几何声明且本容器无世界文件（跨容器同名 tifw×3 留块6）；WMF 12 件 tool_gap 待授权；大件 checksum 方法未跑；NoData 源未声明留导入合同；inventory 历史阻断 3 项显式登记留块6；LOCAL_CS 非 EPSG 不推导。
全部 43 栅格提案待茶香/Codex 批准；命名/装载器（PostGIS raster vs bytea）留第 6 块与导入阶段。

## 边界
本轮仅 32 只读读件+38 整理交付+Gitea；依赖/镜像/服务/数据库/历史对象处置均在授权外。entry/rehearsal M=2 保留态未触。

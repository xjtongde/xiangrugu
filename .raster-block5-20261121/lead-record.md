# 第 5/6 块首盒 lead 记录（2026-11-21，30 分钟盒）

- 起表 15:01:29 UTC，硬停 15:31:29 UTC。基线 5d0c9e3a7b8e8f55cc9af7cd8867f569ce52f818。
- lead 对账（recon_block5.py，两版迭代）：v1 缺陷=disposition 连字符/下划线误配+嵌套 member_key 链重建错误（'!'+ '/' 混合分隔）+handoff 超序认领；v2 修复后 unresolved 0。8004=6103 已归属+1901 无归属；候选 2522=620 块2交接+1 Thumbs.db+1901 扫描。跨块引用 4 件（2 TAB text 归块2、china_chron.txt 归块2、README_CHINA_CHRON 归块5，均被块3/块4注记引用，不重复认领）。
- a02 探测（probe_block5.py 阶段A 87 秒 + bindings_gdal_block5.py 阶段B）：2522/2522，sha 2437/2437 失配 0，目录 85 n/a；分类 doc_license 1445/structural 615/ordinary_image 299/sidecar 116/geo_raster 43/checksum 3/cache 1/unknown 0。
- 工具披露：镜像 f1675321e33e 无 gdalinfo CLI（python3-gdal iU 半装态），a02 改用 osgeo Python 绑定只读探针，43/43 rc=0；未装依赖、未建新镜像、未改别名。
- **缺陷与修复披露**：①a02 GetNoDataValue(True) 传参错误致 113 波段 noData_error；lead 复核发现下令，a02 fix_nodata_block5.py 仅重探 43 件修复（无参调用），113 波段全 None=源未声明真值态，错误键 0；修复件 probe_evidence.json sha a8b543f2c46cbfca…（旧件 0b2b3706… 作废）。a02 完成报告与修复令交叉，时间线如实披露。②lead 生成器两缺陷：32 浅目录 HERE.parents[5] 越界（改证据目录守卫）、目录件 sha_verified 断言过严（改 n/a_directory 分支）；另 SUMMARY 硬编码计数改派生。修复后 32 双跑 exit 0/0、stderr 0/0、DOUBLE_RUN_BYTE_IDENTICAL（/tmp/raster5-uhYO6c）。
- 四产物 sha：members 829eabc6bb2d75d6…/raster-mapping a696479e73ca4d07…/evidence-gaps 0595546966b32fe9…/SUMMARY 8c815b9c9c59fe8b…。
- 首个阻塞：pdb2.TIF(v4_dem_geotiff.zip) 无内部 GT/CRS 且本容器无同 stem 世界文件；同名 tifw 在另 3 容器（ELTD3L/HIMIVE-V3/ZZKZ6U），跨容器借用属镜像/合并语义留第 6 块，本轮不推断。
- 其余缺口：WMF 12 件 tool_gap 待授权；大件 17 件 checksum 方法登记未跑；NoData 源未声明 113 波段留导入合同；inventory 历史阻断 3 项（SHA256SUMS-b2 line173/nul126、harvard/chgis/SHA256SUMS.txt line4）显式登记留块6；LOCAL_CS 非 EPSG 不推导。
- 镜像候选组 377（块5范围内同 sha），含 map1_.TIF/Ca1884_przh_partial.TIF checksum 全同疑似异名同内容；合并裁定留块6，本轮不选主不丢弃。
- 边界：快照 :ro 零触；隔离提取读后即删不入 git；未写库/未执行源 SQL/未进 pg32/pg32b；entry/rehearsal M=2 保留态未触（WT sha 668900d4…）。
- 32 工作目录：/opt/mydocker/xiangrugu/build-candidates/raster-other-20261121/（脚本+证据+四件+stageA 中间件）；双跑隔离 /tmp/raster5-uhYO6c。
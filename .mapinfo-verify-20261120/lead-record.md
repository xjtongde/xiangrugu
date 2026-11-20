# MapInfo 几何核验 · lead 运行记录（2026-11-20，第 3/6 块）

基线 2df6e3db87068d9372aab0b5906a8a7b0243bd98；盒 17:14:26Z–17:44:26Z（30 分钟）。
过程披露：a02 本轮第四次早退（路由杂讯未执行），lead 接管构建与读取；a03 独立复读不变。

## 镜像
- 标签 xiangrugu:runtime-spatial-mapinfo-20261120-a（独立标签，未覆盖任何别名）
- Id sha256:f1675321e33eeb95b6e43eb21410f1a48459f77e250de445f595c02caac6e595
- labels: revision=2df6e3db87068d9372aab0b5906a8a7b0243bd98 / created=2026-11-20T17:19:38Z / source.status=clean / version=0.1.0 / gdal=3.6.2+dfsg-1+b2 / purpose=mapinfo-mitab-readonly-verification
- 基座 python@sha256:4b4c524dc3dce996864e030c7bd9c6b0e517597189fee48f48e05b499442444b（现有镜像复用）
- 锁定：datamgmt/requirements-apt.lock 92 deb（来源 http://ftp.us.debian.org/debian bookworm/main amd64；python3-gdal=3.6.2+dfsg-1+b2 sha256 7f80b3715d6d766fb2fb424b5daa3f6b67a7f6c733dccd4788287bbdeda6b09f）；deb 实物 32:/opt/mydocker/xiangrugu/build-candidates/runtime-spatial-mapinfo-20261120-a/debs/（a03 抽核 14/14 match）
- 构建命令（32，上下文=build-candidates/runtime-spatial-mapinfo-20261120-a/）：
  docker build --network none -t xiangrugu:runtime-spatial-mapinfo-20261120-a --build-arg BUILD_DATE=2026-11-20T17:19:38Z --build-arg VCS_REF=2df6e3db87068d9372aab0b5906a8a7b0243bd98 --build-arg SOURCE_STATUS=clean --build-arg VERSION=0.1.0 -f Dockerfile .
  （--network none 成功=92 deb 离线闭包完整实证；Dockerfile 仓内 datamgmt/Dockerfile.spatial-candidate；dpkg -i 两遍+--configure -a；构建内联 /usr/bin/python3 osgeo+MITAB 断言）
- 预检命令：docker run --rm --network none --entrypoint /usr/bin/python3 xiangrugu:runtime-spatial-mapinfo-20261120-a -c "from osgeo import ogr,gdal;…"
  结果：GDAL 3.6.2；驱动列表含 'MapInfo File'（该版本 MITAB 注册名；GetDriverByName('MITAB') 返 None 属命名差异，a03 如实注记）
- 宿主软件零改、现有别名零触、未进 pg32/pg32b 容器、无 DB 凭据、无 Docker socket 挂载。

## 读取运行命令（两案同一脚本一次运行）
docker run --rm --network none \
  -v /opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap:/data:ro \
  -v /opt/mydocker/xiangrugu/mapinfo-verify-20261120:/work \
  --entrypoint /usr/bin/python3 xiangrugu:runtime-spatial-mapinfo-20261120-a /work/read_mapinfo.py
EXIT=0；ALL ASSERTS PASSED；脚本 .mapinfo-verify-20261120/read_mapinfo.py（expected.json 由 inventory 生成）。
几何类型分布补测：同镜像同挂载运行内联脚本→geom_types.json（POLYGON 1456+MULTIPOLYGON 533，与 a03 独立同值）。

## 源件摘要（前后）
- 外层 harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip：前=后=4dec393bb9ff4acb3c61511817777f41c9215b7ef25e0d1128adc80b776f9660（355618602B，==inventory；快照 :ro 零触）
- 内层两案 v3_time_pref_pgn_PRC.ZIP：69b5119f01f2b593…（字节相同）==inventory
- 组件×两案：TAB c7bb2a78…/DAT 3937da6c…/MAP a7b44b35a4123c7c…/ID f3956a79…/IND c422403b… 全匹配（match_inventory+size_match True×10）

## 两案结果（case_mapinfo / case_shapefiles 同值）
- 图层 V3_time_pref_pgn_PRC；要素 1989==DAT 1989 互证；遍历 1989；空几何 0；读取错误 0
- 几何类型：POLYGON 1456 + MULTIPOLYGON 533（OBJ_TYPE 属性全 POLYGON）；纯 POLYGON 环数 {1:1418,2:37,4:1}；MULTIPOLYGON 部件数 2–39 另记（口径注记在证）
- extent [106.60376, 124.576195, 18.160896, 35.726135]（a03 逐位同值）
- 属性：23 字段全量 jsonl×2（953627B  each，字节同大小）；a03 独立 struct DAT 全量解码 1989×23 full-field diffs=0
- 大小写：临时副本统一 V3_time_pref_pgn_PRC.*（DAT/MAP/IND v3_→V3_ 3 件映射记录；TAB/ID 原名已大写）；原件零触
- **CRS 裁定**：TAB 无 Coordsys；MITAB 返回 GEOGCS unnamed/Pulkovo_1942/Krassovsky WKT=读取器默认猜测非源声明⇒不采纳，UNRESOLVED 保留，不推断不转换
- **属性坐标裁定**：X_COOR 1970/1989 零（19 非零 [1.0,57.0]）、Y_COOR 1975 零（14 非零含哨兵 999.999999）⇒源件属性坐标未填充/占位，几何为权威，不补造；质心-属性偏差（mean dx 115.4/max dy 977.2）全由零值/哨兵解释
- 镜像处置留第 6 块；其余 MapInfo TAB 对象 MAP 几何不在本轮授权范围

## 证据
.mapinfo-verify-20261120/{read_mapinfo.py, expected.json, mapinfo_evidence.json, geom_types.json, attributes_case_mapinfo.jsonl, attributes_case_shapefiles.jsonl}
32 隔离目录 /opt/mydocker/xiangrugu/mapinfo-verify-20261120/（保留供复核）；a03 隔离 .spatial-block3-20261120/mapinfo-verify-a03-20261120/ + 32:/tmp/a03_r12_verify/（保留）。
a03 ROUND 12 五项 PASS（17:26:30Z）+披露 A/B 已修正复测；集成后非回归补段待 a03。
# MAP 几何只读读取方案（提案，待茶香批准）

日期：2026-11-20。基线 c0d0799。本轮**未安装任何依赖、未写库、未在 pg32b 服务容器内做任何读件试验**。

## 受影响对象（剩余缺口）

| 对象 | 链 | size | sha256（前 16） |
|---|---|---|---|
| V3_time_pref_pgn_PRC.MAP（mapinfo 案） | harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip!mapinfo/v3_time_pref_pgn_PRC.ZIP!v3_time_pref_pgn_PRC.MAP | 20469248 | a7b44b35a412… |
| V3_time_pref_pgn_PRC.MAP（shapefiles 案） | 同上外层!shapefiles/v3_time_pref_pgn_PRC.ZIP!v3_time_pref_pgn_PRC.MAP | 20469248 | a7b44b35a412… |

两案内层 ZIP 字节相同（sha 69b5119f01f2…），MAP 为同一字节的两个登记路径；镜像合并处置留第 6 块。属性面 DAT 已按 TAB 23 字段 schema struct 试解（1989 记录、OBJ_TYPE 全 POLYGON、结构置信 HIGH/值 MEDIUM）；**几何本体 .MAP 现有工具不可解码**。

## 自有环境复用勘察（32 实测，16:41–16:43Z，只读）

- 宿主 32：无 ogrinfo/gdalinfo；python3 无 osgeo/ogr、fiona、shapefile（pyshp）模块。
- xiangrugu-dev 容器：无 ogrinfo/gdalinfo 二进制；pip 无 gdal/fiona/pyshp/shapely/geopandas；**pyproj 3.7.2 在位（PROJ 9.5.1，与 requirements.lock L24 锁定一致）**——可复用于 CRS 诊断/投影比对，但 pyproj 不读 MapInfo 文件几何。
- 自有镜像列表：无 gdal/ogr/spatial/gis 标签镜像；块 2 候选镜像（xlrd 2.0.2）无 GDAL。
- 仓内 PROJ 锁定件：spatial-review.md L39 记 pyproj 3.7.2 wheel 锁定、内置 proj.db 9,261,056B sha a25d85a2…（工具只读资源）。
- **结论：自有环境无可复用的 MapInfo 几何读取器；需新增 GDAL/OGR（MITAB driver）。**

## 方案 A（推荐）：GDAL/OGR MITAB，apt 版本锁定 + 自有候选镜像

- **锁定版本**：Debian bookworm main amd64 `python3-gdal=3.6.2+dfsg-1+b2`、`libgdal32=3.6.2+dfsg-1+b2`（32 apt-cache policy 实测候选，16:43Z）；依赖 libgeos-c1v5/libproj25/proj-data 按 apt 依赖树同锁。
- **哈希锁定**：`apt-get download python3-gdal=3.6.2+dfsg-1+b2 libgdal32=… <依赖闭包>` → 逐 deb 记 sha256 入新锁件 `datamgmt/requirements-apt.lock`（增量追加 lineage，同 pip 锁纪律）；安装走 `dpkg -i` 本地 deb 或 apt 版本钉住 + 锁件校验，**不声称重新解析依赖树**。
- **构建命令**（Dockerfile 增 `runtime-spatial` stage，FROM 现有 base；**永不覆盖 dev/test/runtime 别名**）：
  ```
  docker build --target runtime-spatial \
    -t xiangrugu:runtime-spatial-mapinfo-<date>-a \
    --build-arg BUILD_DATE=<utc> --build-arg VCS_REF=<commit> \
    --build-arg SOURCE_STATUS=clean --build-arg VERSION=0.1.0 .
  ```
  构建上下文经 lead `git archive <commit> | ssh 32 tar -x -C build-candidates/…`（deploy 不动）。
- **只读使用**：嵌套 ZIP 经 zipfile 提取到隔离 /tmp（快照 :ro 字节零接触）；`ogrinfo -ro -al <dir>/V3_time_pref_pgn_PRC.TAB`（MITAB 经 TAB 联动 DAT/MAP/ID）或 Python `ogr.Open(path, 0)`（update=0）。**运行于自有候选容器，严禁 pg32b 服务容器**。
- **验证计划（批准后）**：两案 MAP 各读要素数==1989（与 DAT 记录数互证）、几何类型 POLYGON、bbox 与 DAT X_COOR/Y_COOR 属性坐标交叉核对；a03 独立容器复读取证；证据 sha 链入 basis。
- **影响**：镜像增约 60–80MB；新增 apt 锁面（distro deb 哈希锁定）；**PROJ 版本并存注记**：GDAL 用系统 libproj25（bookworm 9.1.1），pyproj 用内置 PROJ 9.5.1——CRS 诊断须记录所用 PROJ 源，srid=null 政策不变；**孪生 TAB 无 Coordsys 声明**⇒即便几何可读，CRS 仍 unresolved（证据缺口保持，不自动推导 EPSG）；无别名/服务/源件改动。

## 方案 B（备选，无新依赖）：派生 stdlib .MAP 解析器

MapInfo MAP 二进制格式部分公开（对象头类型字节+坐标 double 对+多边形环）；自写解析器风险高、须完整证据轨（格式文档引用+逐对象字节对照+独立复核）且**另需茶香批准**。不推荐优先于成熟的 MITAB。

## 状态

待茶香批准方案 A（或 B）。批准前 MAP×2 几何保持工具缺口注记；属性面（DAT 1989 记录）与组件绑定已登记不受影响。第 4 块暂不启动（茶香指令）。
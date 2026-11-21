# 第 5/6 块独立验收补正 · lead 记录（2026-11-21，30 分钟盒）

- 起表 16:15:27 UTC，硬停 16:45:27 UTC。基线 926ed988cceed533bb26cc765c00a36c2963f1d2（M=2 完好、暂存空）。
- 范围：归属账/证据字段/文档补正，复用首盒证据与 32 现有工具，源件只读。
- lead 预核：pdb2 真身 inventory 确证（PDGOZ0/V4_Data_Archive.zip chain [shapefiles/v4_ras_1904_tibet_pts.zip, pdb2.TIF] ordinals [159,6]，13,967,046 B，sha bd56086a9967f0e12775d4de923d39dd06bf861f85e9ffb076eaf888677ed873）；同 sha 四副本枚举（RAS_1900_pdb2_scan.zip[2]/V3[13,5]/CHGIS_V2[56,5]/本件）；缺口机器身份首盒即正确，误在叙述（v4_dem_geotiff.zip）。ODS 身份 ngia_dsg_codes_2017-03-15.zip![2] 13,980 B sha d8adf2a3…。checksum 实绩 26/17，已跑最大 20,342,738 B（>20MB 十进制，首盒「≤20MB」判据不准确）。
- a02 S1–S3（硬停 16:32 内）：ODS 改判（content.xml text_head 实提为证：Sheet1/FULL_NAME/UFI+Field Name/Description/Type/Maximum Field Length/Precision/RC+DSG 代码域）；等式 5482+2522=8004 断言入码；wf enriched（source_member/sha256/参数语义/文本出处）；reader_source×43；pdb2 detail 全身份+四副本；checksum 纯实绩；双跑 0/0。
- **a02 事实更正**：stage B「内部 GT 存在即跳过世界文件转录」缺陷致 2×Peking_1875_Bretschneider.tfw 漏录（首盒 23 绑定被推翻）；修正一律转录后回填 25 件关联；.jgwx XML 变体守卫拒收（非六参数语法），真未绑定仅 1 件。probe_evidence sha 链 a8b543f2→c8021a58（S1）→63e7102d（stageB 重跑+S1 复应用）。
- **lead 接管补强（披露）**：a02 交付件 2 件 casefold 关联无绑定依据标记，与 23 件确证绑定不可区分（违「不推断绑定」令精神）——lead 定点改生成器：binding_basis 分级（exact vs casefold_stem_proximity_PENDING_BLOCK6_ADJUDICATION + binding_status=association_registered_not_confirmed_binding）、counts 拆分 worldfile_bound_exact_stem=23/worldfile_bound_casefold_pending=2 断言入码、gaps detail/SUMMARY 文案同步（「已完成绑定」→「已登记关联，非确证绑定」）。32 双跑 exit 0/0 stderr 0/0 DOUBLE_RUN_BYTE_IDENTICAL（/tmp/raster5fix-gOXOUS）。
- 终态 sha：members f60dd06daf42f49a…（不变）/raster-mapping bff1c0392e9ed422…/evidence-gaps ceb3c0b222572134…/SUMMARY 7376ba951496d614…/probe_evidence 63e7102dd380f0f4…；缺口 7 组（新增 world_files_unbound_explicit）；分类 structural 614/doc_license 1446/ordinary 299/sidecar 116/geo 43/checksum 3/cache 1。
- 漂移守卫：43 sid 对称差空；identity/尺寸/波段/geotransform/WKT 值/六参数值漂移 0；变化仅注解性增列（a03 穷举核验）。
- TODO：第 3 块 Codex 整理验收通过记入（派工新事实）；第 5 块补正记录+讨论账；首盒 lead-record 追加更正注记（历史原文保留）。
- 边界：快照 :ro 零触；隔离提取用后即删不入 git；未装依赖/未建镜像/未写库；entry/rehearsal M=2 未触；块3补正面（926ed98 spatial 件）零触碰。
- 32 工作目录：/opt/mydocker/xiangrugu/build-candidates/raster-other-20261121/（生成器+evidence/+四件）；双跑隔离 /tmp/raster5fix-gOXOUS。
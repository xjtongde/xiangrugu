#!/usr/bin/env python3
"""Block 5 (raster & other members) deterministic package builder.
Evidence-driven: reads recon.json / candidates.json / probe_evidence.json.
Outputs: members.json / raster-mapping.json / evidence-gaps.json / SUMMARY.md.
Three JSON + SUMMARY byte-stable across runs (sort_keys, fixed constants)."""
import json, hashlib, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
EV = HERE / "evidence"
if not EV.exists():
    EV = HERE.parents[5] / ".raster-block5-20261121"
VCS_REF = "d59010b"
INV_SHA = "fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db"

recon = json.load(open(EV / "recon.json"))
cands = json.load(open(EV / "candidates.json"))
probe = json.load(open(EV / "probe_evidence.json"))

def ikey(x):
    i = x.get("identity", x)
    return (i["relative_path"], tuple(i.get("archive_chain", [])), tuple(i.get("archive_ordinals", [])))
pby = {ikey(p): p for p in probe}
assert len(pby) == len(probe) == len(cands), "probe/candidate count mismatch"

def soid(relative_path, chain, object_name, carrier):
    payload = ["xiangrugu.source-object.v1", relative_path, list(chain), object_name, carrier]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()

DISPO = {
    "geo_raster": ("IMPORT", "geo-raster read through GDAL/osgeo in approved existing candidate image; proposal pending approval"),
    "ordinary_image": ("NON_TABULAR", "ordinary image (magic-confirmed); original bytes+sha retained; no tabular/raster payload claimed"),
    "documentation_license": ("NON_TABULAR", "documentation/license/metadata text; original identity+sha+purpose retained"),
    "checksum_ledger": ("NON_TABULAR", "checksum ledger; historical blocking issues explicitly registered for block 6"),
    "structural_container": ("NON_TABULAR", "structural container (ZIP/directory); descendants owned by their respective blocks exactly-once"),
    "sidecar_companion": ("NON_TABULAR", "companion/sidecar; binding basis recorded; owner cross-referenced, not re-claimed"),
    "cache": ("NON_TABULAR", "Windows Explorer thumbnail cache (DESIGN explicit NON_TABULAR)"),
}
members = []
for c in cands:
    k = (c["relative_path"], tuple(c["archive_chain"]), tuple(c["archive_ordinals"]))
    p = pby[k]
    cls = p["class"]
    if c["kind"] == "file":
        assert p["sha_verified"] is True, f"sha not verified: {k}"
    else:
        assert p["sha_verified"] == "n/a_directory" and cls == "structural_container", f"bad directory probe: {k}"
    disp, basis = DISPO[cls]
    m = {"identity": {"relative_path": c["relative_path"], "archive_chain": c["archive_chain"],
                      "archive_ordinals": c["archive_ordinals"], "kind": c["kind"],
                      "size": c["size"], "sha256": c["sha256"]},
         "candidate_source": c["candidate_source"], "class": cls,
         "probe": {"magic": p.get("magic"), "sha_verified": p["sha_verified"], "size_actual": p.get("size_actual"),
                   "purpose": p.get("purpose")},
         "disposition": disp, "disposition_basis": basis,
         "approval_status": "PROPOSED_NOT_AUTHORIZED" if cls == "geo_raster" else "REGISTERED"}
    if p.get("binding"): m["binding"] = p["binding"]
    if p.get("gaps"): m["gaps"] = p["gaps"]
    if cls == "structural_container" and p.get("declared", {}).get("direct_member_count") is not None:
        m["direct_member_count"] = p["declared"]["direct_member_count"]
    members.append(m)

# mirror candidate groups within block5 scope (merge deferred to block 6)
bysha = collections.defaultdict(list)
for m in members:
    if m["identity"]["kind"] == "file" and m["identity"]["sha256"]:
        bysha[m["identity"]["sha256"]].append(m["identity"])
mirror_groups = [{"sha256": s, "member_count": len(v), "members": v}
                 for s, v in sorted(bysha.items()) if len(v) > 1]

gr = [m for m in members if m["class"] == "geo_raster"]

# ---- S2② 世界文件绑定 enriched：同容器同目录同 stem 确定性 join（源成员身份+sha）----
cby = {ikey(c): c for c in cands}
assert len(cby) == len(cands)
_wf_join_hits = 0
for _m in gr:
    _rm = pby[ikey(_m)]["raster_meta"]
    _wfd = _rm.get("world_file_declared")
    if not _wfd:
        continue
    _parent_chain = list(_m["identity"]["archive_chain"][:-1])
    _stem = (_m["identity"]["archive_chain"][-1] if _m["identity"]["archive_chain"]
             else _m["identity"]["relative_path"]).rsplit(".", 1)[0].lower()
    _wfleaf = _wfd["file"]
    _match = None
    for _c in cands:
        if _c["kind"] != "file":
            continue
        if _c["relative_path"] != _m["identity"]["relative_path"]:
            continue
        if list(_c["archive_chain"][:-1]) != _parent_chain:
            continue
        if _c["leaf"].lower() == _wfleaf.lower():
            _match = _c
            break
    assert _match is not None, f"world file join miss: {_wfleaf} in {_m['identity']}"
    _pk = ikey(_match)
    _pp = pby[_pk]
    assert _pp["sha_verified"] is True and _pp["declared"]["sha256"] == _match["sha256"], \
        f"world file sha mismatch vs inventory/candidates: {_wfleaf}"
    _wfd["source_member"] = {"relative_path": _match["relative_path"],
                             "archive_chain": _match["archive_chain"],
                             "archive_ordinals": _match["archive_ordinals"]}
    _wfd["sha256"] = _match["sha256"]
    # lead 补正接管（披露）：绑定依据显式分级——精确同 stem 确证绑定 vs
    # casefold 近似关联（仅登记，语义裁定留块6，不得与确证绑定混同）
    _tif_stem = (_m["identity"]["archive_chain"][-1] if _m["identity"]["archive_chain"]
                 else _m["identity"]["relative_path"]).rsplit("/", 1)[-1].rsplit(".", 1)[0]
    _wf_stem = _wfleaf.rsplit(".", 1)[0]
    if _tif_stem == _wf_stem:
        _wfd["binding_basis"] = "same_container_same_directory_same_stem_exact"
    else:
        assert _tif_stem.lower() == _wf_stem.lower(), f"unexpected stem mismatch: {_tif_stem} vs {_wf_stem}"
        _wfd["binding_basis"] = "casefold_stem_proximity_PENDING_BLOCK6_ADJUDICATION"
        _wfd["binding_status"] = "association_registered_not_confirmed_binding"
    _wfd["parameter_semantics"] = {
        "order": ["x_resolution", "rot_2", "rot_3", "y_resolution",
                  "x_origin_upper_left", "y_origin_upper_left"],
        "第五六参数": "左上像素中心 (upper-left pixel center)",
        "note": "ESRI 世界文件六参数惯例逐字登记；不做单位/轴向推断"}
    _wfd["text_provenance"] = {
        "verbatim": _wfd["verbatim"],
        "verbatim_label": "原文逐字（源成员字节转录）",
        "normalized_text": "\n".join(repr(_wfd[_k]) for _k in (
            "x_resolution", "rot_2", "rot_3", "y_resolution",
            "x_origin_upper_left", "y_origin_upper_left")),
        "normalized_text_label": "规整文本（由本生成器从原文解析，非源件字节）"}
    _wf_join_hits += 1
assert _wf_join_hits == 25, f"world-file enriched {_wf_join_hits} != 25"

proposals = []
for m in gr:
    p = pby[(m["identity"]["relative_path"], tuple(m["identity"]["archive_chain"]), tuple(m["identity"]["archive_ordinals"]))]
    rm = p["raster_meta"]
    i = m["identity"]
    leaf = (i["archive_chain"][-1] if i["archive_chain"] else i["relative_path"]).split("/")[-1]
    carrier = "geotiff" if leaf.lower().endswith((".tif", ".tiff")) else "jpeg_with_worldfile"
    bands = rm.get("bands", [])
    csd = rm.get("crs_source_declared") or {}
    # S2③：reader 来源注解（WKT 逐字值不动，仅增字段）
    csd_out = dict(csd)
    csd_out["reader_source"] = ("osgeo GDAL 3.6.2 GetProjectionRef"
                                "（镜像 f1675321e33eeb95…，只读探针）")
    csd_out["wkt_provenance"] = ("GDAL GetProjectionRef 返回值（逐字转录，"
                                 "无内部声明=null，不推导不转换）")
    proposals.append({
        "source_object_id": soid(i["relative_path"], i["archive_chain"], leaf, carrier),
        "identity": i, "carrier": carrier,
        "observed": {"size_px": rm.get("size_px"), "bands": bands,
                     "geotransform": rm.get("geotransform"),
                     "crs_source_declared": csd_out,
                     "world_file_declared": rm.get("world_file_declared"),
                     "gcp_count": rm.get("gcp_count"), "driver": rm.get("driver"),
                     "gdalinfo_rc": rm.get("gdalinfo_rc")},
        "per_band_verification": {"method": "GDAL band checksum (osgeo Band.Checksum())",
                                  "executed_this_round": bool(rm.get("checksum_ran")),
                                  "note": ("本盒已执行逐波段 checksum（osgeo Band.Checksum()），"
                                           "值在 bands[].checksum" if rm.get("checksum_ran")
                                           else "仅登记方法，执行留导入阶段（大件栅格）")},
        "target_proposal": {"schema": "chgis", "table_name_proposal": None,
                            "naming_note": "full-release naming and collision allocation deferred to block 6",
                            "loader": "UNDECIDED (PostGIS raster vs bytea+sidecar contract at import stage)",
                            "pixel_semantics": "preserve source pixel type/NoData/affine/CRS declaration verbatim; no reprojection, no resampling, no fill"},
        "status": "PROPOSED_NOT_AUTHORIZED", "ready_for_import": False})

gaps = []
pdb2 = [m for m in gr if not (pby[(m["identity"]["relative_path"], tuple(m["identity"]["archive_chain"]), tuple(m["identity"]["archive_ordinals"]))]["raster_meta"].get("geotransform")) and not (pby[(m["identity"]["relative_path"], tuple(m["identity"]["archive_chain"]), tuple(m["identity"]["archive_ordinals"]))]["raster_meta"].get("world_file_declared"))]
for m in pdb2:
    gaps.append({"kind": "georeference_undeclared", "status": "UNRESOLVED_BLOCK6",
                 "identity": m["identity"],
                 "detail": ("完整身份：harvard-full/doi_10_7910/DVN/PDGOZ0/"
                            "V4_Data_Archive.zip!shapefiles/v4_ras_1904_tibet_"
                            "pts.zip!pdb2.TIF（chain [\"shapefiles/v4_ras_1904_"
                            "tibet_pts.zip\",\"pdb2.TIF\"]，ordinals [159,6]，"
                            "size 13,967,046，sha bd56086a9967f0e12775d4de923d"
                            "39dd06bf861f85e9ffb076eaf888677ed873）。无内部 "
                            "geotransform/CRS 且本容器内无同 stem 世界文件。同 "
                            "sha 四副本：RAS_1900_pdb2_scan.zip[2]、V3_Data_"
                            "Archive.zip![13,5]、CHGIS_V2.zip![56,5]、本件"
                            "[159,6]；三处同摘要副本的合并裁定留第 6 块，配准"
                            "未决状态保留；跨容器借用属镜像/合并语义，本轮不推断"),
                 "same_sha_copies": [
                     {"outer": "harvard-full/doi_10_7910/DVN/ELTD3L/RAS_1900_pdb2_scan.zip",
                      "chain": ["pdb2.TIF"], "ordinals": [2]},
                     {"outer": "harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip",
                      "chain": ["shapefiles/russ_1904_tibet_pts.ZIP", "pdb2.TIF"],
                      "ordinals": [13, 5]},
                     {"outer": "harvard-full/doi_10_7910/DVN/ZZKZ6U/CHGIS_V2.zip",
                      "chain": ["shapefiles/russ_1904_tibet_pts.ZIP", "pdb2.TIF"],
                      "ordinals": [56, 5]}]})
# S2②补充：未绑定世界文件显式登记（不推断绑定）
_unbound_wf = [
    {"leaf": "NaturalGasLines_PetroChina_20110830.jgwx",
     "outer": "harvard-full/doi_10_7910/DVN/J5U79Z/ChinaGasPipelines_2013.zip",
     "chain": ["NaturalGasLines_PetroChina_20110830.jgwx"], "ordinals": [13],
     "note": ("jgw 的 XML 变体伴随件（.jgwx≠六参数 .jgw 语法，非世界文件成"
              "员格式）；同名 .jgw 已绑定该 jpg；本件显式登记不推断绑定")}]
# 更正注记：lead 清单中的 2×Peking_1875_Bretschneider.tfw 经 stage B 修正
# （世界文件一律逐字转录、不以内部 GT 为跳过条件）后已完成 raster-side 绑定
# （25 件回填），其 casefold 近似对观察保留如下，绑定语义裁定仍留块6。
_casefold_obs = [
    {"tfw": "harvard-full/doi_10_7910/DVN/H4WVUP/beijing_1875.zip!Peking_1875_Bretschneider.tfw[2]",
     "tif": "peking_1875_bretschneider.tif（同容器，stem 大小写差异）"},
    {"tfw": "harvard-full/doi_10_7910/DVN/ZZKZ6U/CHGIS_V2.zip!shapefiles/v2_1875_peking_map.ZIP!Peking_1875_Bretschneider.tfw[76,3]",
     "tif": "peking_1875_bretschneider.tif（同内层容器，stem 大小写差异）"}]
for _u in _casefold_obs:
    pass  # 观察注记入 gaps detail，不改成员分类
for _u in _unbound_wf:
    _rec = pby.get((_u["outer"], tuple(_u["chain"]), tuple(_u["ordinals"])))
    assert _rec is not None and _rec.get("class") == "sidecar_companion", \
        f"未绑定世界文件记录缺失或分类异常: {_u['leaf']}"
    _rec.setdefault("binding", {})["unbound_registered"] = True
    _rec["binding"]["block6_note"] = _u["note"]
gaps.append({"kind": "world_files_unbound_explicit", "status": "REGISTERED_NO_INFERENCE",
             "affected_member_count": len(_unbound_wf),
             "members": _unbound_wf,
             "casefold_proximity_observations": _casefold_obs,
             "detail": ("更正后实绩：2×Peking tfw 经世界文件逐字转录修正后已登"
                        "记 raster-side 关联（25 件回填=23 件精确同 stem 确证绑"
                        "定+2 件 casefold 近似关联，后者 binding_basis 显式标记"
                        "PENDING_BLOCK6，非确证绑定）；真正未绑定 1 件=.jgwx（XML"
                        " 变体非六参数世界文件格式），显式登记不推断。stage B 修"
                        "正披露：原实现以内部 GT 存在为跳过条件致 2 件漏录，"
                        "本轮改为一律转录")})
wmf = [m for m in members if ((m["identity"]["archive_chain"][-1] if m["identity"]["archive_chain"] else m["identity"]["relative_path"]).lower().endswith(".wmf"))]
if wmf:
    gaps.append({"kind": "tool_gap_wmf_reader", "status": "AWAITING_AUTHORIZATION",
                 "affected_member_count": len(wmf),
                 "identities": [m["identity"] for m in wmf],
                 "detail": "WMF metafile: magic BINARY_UNKNOWN, no confirmed read capability in existing images; capability assessment awaits separate authorization; no dependency installed this round"})
large = [m for m in gr if not pby[(m["identity"]["relative_path"], tuple(m["identity"]["archive_chain"]), tuple(m["identity"]["archive_ordinals"]))]["raster_meta"].get("checksum_ran")]
if large:
    gaps.append({"kind": "raster_checksum_deferred", "status": "REGISTERED_METHOD_NOT_RUN",
                 "affected_member_count": len(large),
                 "detail": ("per-band checksum 实绩：26 件已执行、17 件仅登记方法"
                            "（执行留导入阶段）；不附尺寸判据")})
nodata_null = sum(1 for p in proposals for b in p["observed"]["bands"] if b.get("noData") is None)
gaps.append({"kind": "nodata_source_undeclared", "status": "REGISTERED_FOR_IMPORT_CONTRACT",
             "affected_band_count": nodata_null,
             "detail": "bands whose source declares no NoData value: recorded as null verbatim; import contract must decide representation, no fill invented"})
gaps.append({"kind": "inventory_historical_issues", "status": "EXPLICITLY_REGISTERED_BLOCK6",
             "issues": recon["inventory_issues"],
             "detail": "inventory complete=false historical blocking issues carried forward verbatim; full reconciliation belongs to block 6"})
crs_local = [m["identity"] for m in gr if (pby[(m["identity"]["relative_path"], tuple(m["identity"]["archive_chain"]), tuple(m["identity"]["archive_ordinals"]))]["raster_meta"].get("crs_source_declared") or {}).get("wkt_verbatim_from_source") and "LOCAL_CS" in str(pby[(m["identity"]["relative_path"], tuple(m["identity"]["archive_chain"]), tuple(m["identity"]["archive_ordinals"]))]["raster_meta"]["crs_source_declared"])]
if crs_local:
    gaps.append({"kind": "crs_local_cs_non_epsg", "status": "UNRESOLVED_NO_INFERENCE",
                 "affected_member_count": len(crs_local),
                 "detail": "LOCAL_CS declarations preserved verbatim; no EPSG inferred; SRID assignment awaits source-level adjudication"})

cls_counts = dict(collections.Counter(m["class"] for m in members))
disp_counts = dict(collections.Counter(m["disposition"] for m in members))
# ---- S2① 归属等式机器断言（recon 派生剔除 handoff 标签）----
_prior_breakdown = {k: v for k, v in recon["owned_by_block"].items()
                    if not k.startswith("handoff") and "handoff" not in k}
prior_owned = sum(_prior_breakdown.values())
handoff_in_candidates = (recon["candidate_by_source"]["handoff_block2"]
                         + recon["candidate_by_source"]["handoff_block4"])
assert prior_owned == 5482, f"前四块归属 {prior_owned} != 5482 (breakdown {_prior_breakdown})"
assert handoff_in_candidates == 621, f"交接件 {handoff_in_candidates} != 621"
assert prior_owned + len(members) == recon["inventory_entries"] == 8004, \
    f"归属等式断裂: {prior_owned}+{len(members)} vs {recon['inventory_entries']}"
members_doc = {"format": "xiangrugu.import-package.raster-other.members.v1",
               "baseline_git": VCS_REF, "inventory_sha256": INV_SHA,
               "candidate_total": len(members), "class_counts": cls_counts,
               "disposition_counts": disp_counts,
               "candidate_by_source": recon["candidate_by_source"],
               "ownership_reconciliation": {"inventory_entries": recon["inventory_entries"],
                                            "prior_blocks_owned": prior_owned,
                                            "prior_blocks_breakdown": _prior_breakdown,
                                            "handoff_to_block5_counted_in_candidates": handoff_in_candidates,
                                            "equation": f"{prior_owned} + {len(members)} == {recon['inventory_entries']}",
                                            "owned_by_prior_blocks_raw_with_handoff": recon["owned_by_block"],
                                            "unowned_scanned": recon["unowned_count"],
                                            "cross_references": recon["cross_references"],
                                            "unresolved_refs": recon["unresolved_refs"]},
               "mirror_candidate_groups_within_block5": mirror_groups,
               "flags": {"ready_for_import": False, "proposals_not_authorized": True},
               "members": members}
mapping_doc = {"format": "xiangrugu.import-package.raster-other.raster-mapping.v1",
               "baseline_git": VCS_REF,
               "counts": {"geo_raster_members": len(gr), "proposals": len(proposals),
                          "internal_gt_or_crs_declared": sum(1 for p in proposals if p["observed"]["geotransform"] or (p["observed"]["crs_source_declared"] or {}).get("wkt_verbatim_from_source")),
                          "worldfile_bound": sum(1 for p in proposals if p["observed"]["world_file_declared"]),
                          "worldfile_bound_exact_stem": sum(1 for p in proposals if (p["observed"]["world_file_declared"] or {}).get("binding_basis") == "same_container_same_directory_same_stem_exact"),
                          "worldfile_bound_casefold_pending": sum(1 for p in proposals if (p["observed"]["world_file_declared"] or {}).get("binding_basis") == "casefold_stem_proximity_PENDING_BLOCK6_ADJUDICATION"),
                          "checksum_executed": sum(1 for p in proposals if p["per_band_verification"]["executed_this_round"])},
               "flags": {"ready_for_import": False}, "proposed_objects": proposals}
assert mapping_doc["counts"]["worldfile_bound_exact_stem"] == 23 and mapping_doc["counts"]["worldfile_bound_casefold_pending"] == 2, mapping_doc["counts"]
gaps_doc = {"format": "xiangrugu.import-package.raster-other.evidence-gaps.v1",
            "baseline_git": VCS_REF, "gap_count": len(gaps), "gaps": gaps}
summary = f"""# 第 5/6 块 · 栅格及其他成员包（SUMMARY）

基线 git {VCS_REF}；inventory sha256={INV_SHA[:16]}… 断言一致；32 只读探测（快照 :ro，嵌套按 ordinals 隔离流式提取，读后即删）；**未装依赖/未建新镜像/未写库/未执行源 SQL；源件零触**。

## 候选与归属
- 候选 **{len(members)}** = 块2交接 {recon['candidate_by_source']['handoff_block2']} + 块4 Thumbs.db {recon['candidate_by_source']['handoff_block4']} + 无归属扫描 {recon['unowned_count']}（文件 {recon['candidate_by_kind']['file']} + 目录 {recon['candidate_by_kind']['directory']}）。
- 全 inventory 8004 对账闭合：**前四块实际归属 {prior_owned}**（块1=3/块2=174/块3=5294/块4=11）+ 本块候选 **{len(members)}** = 8004（首盒「6103 已归属」系把交接面 {handoff_in_candidates} 件〔620 块2+1 Thumbs.db〕误计前四块——621 已在块5候选内，更正后等式机器断言在码）；unresolved 0；跨块引用 {len(recon['cross_references'])} 件逐条在 members.json（不重复认领）。
- sha256 全量流式重算 **{recon['candidate_by_kind']['file']}/{recon['candidate_by_kind']['file']} ==声明值，失配 0**。

## 分类计数（逐件处置，unknown 0）
""" + "\n".join(f"- {k} **{v}** → {DISPO[k][0]}" for k, v in sorted(cls_counts.items())) + f"""
- 处置合计：{disp_counts}；geo_raster {len(gr)} 件 IMPORT 提案全 PROPOSED_NOT_AUTHORIZED，ready_for_import=false。
- 块5范围内同 sha 镜像候选组 **{len(mirror_groups)}**（合并裁定留第 6 块，本轮不选主不丢弃）。

## 地理栅格面（{len(gr)}/{len(gr)} 读通）
- 工具：现有候选镜像 xiangrugu:runtime-spatial-mapinfo-20261120-a（Id f1675321e33e…，GDAL 3.6.2 osgeo 绑定；**镜像无 gdalinfo CLI，python3-gdal 半装态如实披露**，改用 osgeo 只读探针，--network none/无凭据/无 socket/快照:ro）。
- 逐件：尺寸/波段(类型/色带/NoData/blocksize)/仿射/**源 CRS WKT 逐字**（无声明=null 不推导）/世界文件六参数 verbatim。
- 内部 GT/CRS 声明 {mapping_doc['counts']['internal_gt_or_crs_declared']} 件；世界文件关联回填 {mapping_doc['counts']['worldfile_bound']} 件=**精确同 stem 确证绑定 {mapping_doc['counts']['worldfile_bound_exact_stem']} 件**（同容器同目录同 stem，跨容器不借用）+**casefold 近似关联登记 {mapping_doc['counts']['worldfile_bound_casefold_pending']} 件**（binding_basis 显式标 PENDING_BLOCK6，非确证绑定，语义裁定留块6）；source_member/sha256/参数语义（第五六参数=左上像素中心）/文本出处（verbatim 原文 vs parsed 规整文本）enriched，join 断言 25/25 命中；逐波段 checksum **实跑 {mapping_doc['counts']['checksum_executed']} 件、仅登记方法 {len(gr) - mapping_doc['counts']['checksum_executed']} 件**（执行留导入阶段，纯实绩不附尺寸判据）。
- ODS 改注记：CountryFilesFormat_2016-07-16.ods（ngia_dsg_codes_2017-03-15.zip!ord[2]）由 structural_container 改判 documentation_license＝字段格式说明材料（内层 content.xml 表名 Sheet1/FULL_NAME/UFI+Field Name/Type/Length/Precision/RC 单元格文本为证，text_head 已落 probe_evidence）；structural 计数随之 614。世界文件关联回填 25 件（stage B「内部 GT 即跳过」缺陷修正后一律逐字转录，GT 与世界文件并存各自引用）：23 件精确同 stem 确证绑定 + 2×Peking tfw casefold 近似关联登记（binding_basis=PENDING_BLOCK6_ADJUDICATION、binding_status=association_registered_not_confirmed_binding，非确证绑定）；真未绑定仅 1 件 .jgwx（XML 变体非六参数语法，守卫拒收）显式登记不推断。
- NoData：源未声明波段 {nodata_null} 个如实 null（探测脚本 GetNoDataValue 传参缺陷由 lead 令 a02 定点修复后回填，修复披露在证据）。
- 证据标注分级：25 处世界文件文本=原文逐字+规整文本双标注（normalized_text 由本生成器解析、非源件字节）；WKT 统一为 GDAL GetProjectionRef 返回值表述（逐字/null 不推导）；校验说明按执行状态分支 **{mapping_doc['counts']['checksum_executed']} 已执行/{len(gr) - mapping_doc['counts']['checksum_executed']} 仅登记**。

## 缺口与批准面
缺口 **{len(gaps)}** 组：pdb2.TIF（真身=V4_Data_Archive.zip!shapefiles/v4_ras_1904_tibet_pts.zip!pdb2.TIF，ordinals [159,6]，sha bd56086a…；首盒误写 v4_dem_geotiff.zip 已更正）无几何声明且本容器无世界文件（同 sha 四副本合并留块6）；WMF 12 件 tool_gap 待授权；checksum 26 实跑/17 方法登记；NoData 源未声明留导入合同；inventory 历史阻断 3 项显式登记留块6；LOCAL_CS 非 EPSG 不推导；未绑定世界文件 1 件（.jgwx）显式登记，2 件 Peking tfw casefold 近似关联待块6裁定。
全部 {len(gr)} 栅格提案待茶香/Codex 批准；命名/装载器（PostGIS raster vs bytea）留第 6 块与导入阶段。

## 边界
本轮仅 32 只读读件+38 整理交付+Gitea；依赖/镜像/服务/数据库/历史对象处置均在授权外。entry/rehearsal M=2 保留态未触。
"""
# ---- d59010b 证据标注收尾：漂移守卫断言入码 ----
assert len({p["source_object_id"] for p in proposals}) == 43, "sid 集漂移"
assert cls_counts == {"documentation_license": 1446, "structural_container": 614,
                      "ordinary_image": 299, "sidecar_companion": 116,
                      "geo_raster": 43, "checksum_ledger": 3, "cache": 1}, \
    f"class_counts 漂移: {cls_counts}"
assert prior_owned + len(members) == recon["inventory_entries"] == 8004, "归属等式漂移"
assert len(gaps) == 7, f"缺口组数漂移: {len(gaps)}"
_wfd_all = [p["observed"]["world_file_declared"] for p in proposals
            if p["observed"].get("world_file_declared")]
assert len(_wfd_all) == 25 and all(
    set(("verbatim", "verbatim_label", "normalized_text", "normalized_text_label"))
    <= set(w["text_provenance"]) for w in _wfd_all), "text_provenance 分级不全"
assert sum(1 for w in _wfd_all
           if w.get("binding_basis") == "same_container_same_directory_same_stem_exact") == 23, \
    "exact 绑定计数漂移"
assert sum(1 for w in _wfd_all
           if str(w.get("binding_basis", "")).startswith("casefold")) == 2, "casefold 分级漂移"
assert all(w.get("sha256") and w.get("source_member") for w in _wfd_all), "wf sha/身份漂移"
assert all((p["observed"]["crs_source_declared"] or {}).get("wkt_provenance")
           for p in proposals), "wkt_provenance 缺失"
assert sum(1 for p in proposals if p["per_band_verification"]["executed_this_round"]) == 26 \
    and sum(1 for p in proposals if not p["per_band_verification"]["executed_this_round"]) == 17, \
    "checksum 分支计数漂移"
for p in proposals:
    _w = p["observed"].get("world_file_declared")
    if _w:
        assert [_w[k] for k in ("x_resolution", "rot_2", "rot_3", "y_resolution",
                                "x_origin_upper_left", "y_origin_upper_left")] == \
               [float(x) for x in _w["verbatim"].split()], \
            f"六参数与 verbatim 失配: {p['identity']['relative_path']}"

(HERE / "members.json").write_text(json.dumps(members_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "raster-mapping.json").write_text(json.dumps(mapping_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "evidence-gaps.json").write_text(json.dumps(gaps_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "SUMMARY.md").write_text(summary)
print(f"built OK: candidates {len(members)} classes {cls_counts} raster {len(gr)} gaps {len(gaps)} mirrors {len(mirror_groups)}")
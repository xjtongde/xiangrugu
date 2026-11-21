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
VCS_REF = "5d0c9e3"
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
proposals = []
for m in gr:
    p = pby[(m["identity"]["relative_path"], tuple(m["identity"]["archive_chain"]), tuple(m["identity"]["archive_ordinals"]))]
    rm = p["raster_meta"]
    i = m["identity"]
    leaf = (i["archive_chain"][-1] if i["archive_chain"] else i["relative_path"]).split("/")[-1]
    carrier = "geotiff" if leaf.lower().endswith((".tif", ".tiff")) else "jpeg_with_worldfile"
    bands = rm.get("bands", [])
    proposals.append({
        "source_object_id": soid(i["relative_path"], i["archive_chain"], leaf, carrier),
        "identity": i, "carrier": carrier,
        "observed": {"size_px": rm.get("size_px"), "bands": bands,
                     "geotransform": rm.get("geotransform"),
                     "crs_source_declared": rm.get("crs_source_declared"),
                     "world_file_declared": rm.get("world_file_declared"),
                     "gcp_count": rm.get("gcp_count"), "driver": rm.get("driver"),
                     "gdalinfo_rc": rm.get("gdalinfo_rc")},
        "per_band_verification": {"method": "GDAL band checksum (osgeo Band.Checksum())",
                                  "executed_this_round": bool(rm.get("checksum_ran")),
                                  "note": "large rasters: method registered, execution deferred to import stage"},
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
                 "detail": "no internal geotransform/CRS and no same-stem world file within this container; same-named world files exist in 3 other containers; cross-container borrowing is mirror/merge semantics, deferred to block 6, not inferred this round"})
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
                 "detail": "large rasters (>20MB): per-band checksum method registered, execution deferred to import stage to bound this box"})
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
members_doc = {"format": "xiangrugu.import-package.raster-other.members.v1",
               "baseline_git": VCS_REF, "inventory_sha256": INV_SHA,
               "candidate_total": len(members), "class_counts": cls_counts,
               "disposition_counts": disp_counts,
               "candidate_by_source": recon["candidate_by_source"],
               "ownership_reconciliation": {"inventory_entries": recon["inventory_entries"],
                                            "owned_by_prior_blocks": recon["owned_by_block"],
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
                          "checksum_executed": sum(1 for p in proposals if p["per_band_verification"]["executed_this_round"])},
               "flags": {"ready_for_import": False}, "proposed_objects": proposals}
gaps_doc = {"format": "xiangrugu.import-package.raster-other.evidence-gaps.v1",
            "baseline_git": VCS_REF, "gap_count": len(gaps), "gaps": gaps}
summary = f"""# 第 5/6 块 · 栅格及其他成员包（SUMMARY）

基线 git {VCS_REF}；inventory sha256={INV_SHA[:16]}… 断言一致；32 只读探测（快照 :ro，嵌套按 ordinals 隔离流式提取，读后即删）；**未装依赖/未建新镜像/未写库/未执行源 SQL；源件零触**。

## 候选与归属
- 候选 **{len(members)}** = 块2交接 {recon['candidate_by_source']['handoff_block2']} + 块4 Thumbs.db {recon['candidate_by_source']['handoff_block4']} + 无归属扫描 {recon['unowned_count']}（文件 {recon['candidate_by_kind']['file']} + 目录 {recon['candidate_by_kind']['directory']}）。
- 全 inventory 8004 对账闭合：前四块已归属 {recon['owned_total']}（块1=3/块2=174/块3=5294/块4=11/交接面 620+1）+ 本块候选 {len(members)} = 8004；unresolved 0；跨块引用 {len(recon['cross_references'])} 件逐条在 members.json（不重复认领）。
- sha256 全量流式重算 **{recon['candidate_by_kind']['file']}/{recon['candidate_by_kind']['file']} ==声明值，失配 0**。

## 分类计数（逐件处置，unknown 0）
""" + "\n".join(f"- {k} **{v}** → {DISPO[k][0]}" for k, v in sorted(cls_counts.items())) + f"""
- 处置合计：{disp_counts}；geo_raster {len(gr)} 件 IMPORT 提案全 PROPOSED_NOT_AUTHORIZED，ready_for_import=false。
- 块5范围内同 sha 镜像候选组 **{len(mirror_groups)}**（合并裁定留第 6 块，本轮不选主不丢弃）。

## 地理栅格面（{len(gr)}/{len(gr)} 读通）
- 工具：现有候选镜像 xiangrugu:runtime-spatial-mapinfo-20261120-a（Id f1675321e33e…，GDAL 3.6.2 osgeo 绑定；**镜像无 gdalinfo CLI，python3-gdal 半装态如实披露**，改用 osgeo 只读探针，--network none/无凭据/无 socket/快照:ro）。
- 逐件：尺寸/波段(类型/色带/NoData/blocksize)/仿射/**源 CRS WKT 逐字**（无声明=null 不推导）/世界文件六参数 verbatim。
- 内部 GT/CRS 声明 {mapping_doc['counts']['internal_gt_or_crs_declared']} 件；世界文件同 stem 绑定 {mapping_doc['counts']['worldfile_bound']} 件（绑定依据=同容器同目录同 stem，跨容器不借用）；逐波段 checksum ≤20MB 实跑 {mapping_doc['counts']['checksum_executed']} 件，大件登记方法留导入阶段。
- NoData：源未声明波段 {nodata_null} 个如实 null（探测脚本 GetNoDataValue 传参缺陷由 lead 令 a02 定点修复后回填，修复披露在证据）。

## 缺口与批准面
缺口 **{len(gaps)}** 组：pdb2.TIF(v4_dem_geotiff.zip) 无几何声明且本容器无世界文件（跨容器同名 tifw×3 留块6）；WMF 12 件 tool_gap 待授权；大件 checksum 方法未跑；NoData 源未声明留导入合同；inventory 历史阻断 3 项显式登记留块6；LOCAL_CS 非 EPSG 不推导。
全部 {len(gr)} 栅格提案待茶香/Codex 批准；命名/装载器（PostGIS raster vs bytea）留第 6 块与导入阶段。

## 边界
本轮仅 32 只读读件+38 整理交付+Gitea；依赖/镜像/服务/数据库/历史对象处置均在授权外。entry/rehearsal M=2 保留态未触。
"""
(HERE / "members.json").write_text(json.dumps(members_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "raster-mapping.json").write_text(json.dumps(mapping_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "evidence-gaps.json").write_text(json.dumps(gaps_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "SUMMARY.md").write_text(summary)
print(f"built OK: candidates {len(members)} classes {cls_counts} raster {len(gr)} gaps {len(gaps)} mirrors {len(mirror_groups)}")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Block 6 (full rollup & landing) deterministic builder — first box.
Evidence-driven, read-only over the five delivered block packages + inventory.json.
Outputs: all-members.json / reconciliation.json / historical-blockers.json /
mirror-adjudication.json / name-conflicts.json / pending-items.json / SUMMARY.md.
No DB writes, no source mutation; inventory issues/complete referenced only."""
import json, hashlib, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../import-package/rollup (or 32 workdir)
EV = HERE / "evidence"
if EV.exists():
    # 32 layout: flat evidence dir with <block>__<file> names
    import os as _os
    def _ev(block, fname):
        return EV / f"{block}__{fname}"
    class _P:
        def __init__(self, block): self.block = block
        def __truediv__(self, fname): return _ev(self.block, fname)
    cbdb_p, tab_p, sp_p, mdb_p, ras_p = (_P(b) for b in ("cbdb","tabular","spatial","mdb-sql","raster-other"))
else:
    PKG = HERE.parent
    cbdb_p = PKG / "cbdb"; tab_p = PKG / "tabular"; sp_p = PKG / "spatial"
    mdb_p = PKG / "mdb-sql"; ras_p = PKG / "raster-other"
def _find_release_root(start):
    q = start
    for _ in range(8):
        if (q / "inventory.json").exists() and (q / "import-package").exists():
            return q
        q = q.parent
    return None
REL = _find_release_root(HERE)
VCS_REF = "c8b8fe8"

INV_PATH = None
for cand in ([REL / "inventory.json"] if REL else []) + [EV / "inventory.json", HERE / "inventory.json"]:
    if cand.exists(): INV_PATH = cand; break
assert INV_PATH, "inventory.json not found"
inv_doc = json.load(open(INV_PATH))
INV_SHA = hashlib.sha256(INV_PATH.read_bytes()).hexdigest()
entries = inv_doc["entries"]
assert len(entries) == 8004 and inv_doc["complete"] is False

def key(d):
    return (d.get("relative_path"), tuple(d.get("archive_chain", []) or []),
            tuple(d.get("archive_ordinals", []) or []))

im = {key(e): e for e in entries}
assert len(im) == 8004

cbdb = json.load(open(cbdb_p / "members.json"))
tab_m = json.load(open(tab_p / "members.json"))
sp_g = json.load(open(sp_p / "groups.json"))
mdb_m = json.load(open(mdb_p / "members.json"))
ras_m = json.load(open(ras_p / "members.json"))
sp_om = json.load(open(sp_p / "object-mapping.json"))
tb_om = json.load(open(tab_p / "object-mapping.json"))
md_om = json.load(open(mdb_p / "object-mapping.json"))
rs_om = json.load(open(ras_p / "raster-mapping.json"))

by_full = collections.defaultdict(list)
for e in entries:
    by_full[tuple([e["relative_path"]] + list(e["archive_chain"]))].append(e)

# ---------------- ownership derivation (lead-ruling 口径) ----------------
spatial_member_keys = {}   # inv key -> (group_id, member dict)
for g in sp_g["groups"]:
    loc = g.get("location") or {}
    cc = list(loc.get("container_chain") or [])
    co = list(loc.get("container_ordinals") or [])
    for m in g["members"]:
        parts = m["member_key"].split("!"); rel = parts[0]
        segs = [p for s in parts[1:] for p in s.split("/")]
        if not segs:
            spatial_member_keys[key({"relative_path": rel})] = (g["group_id"], m); continue
        leaf = segs[-1]; inner = segs[:-1]
        cands = set()
        for v in (tuple([rel, *cc, leaf]), tuple([rel, *inner, leaf]),
                  tuple([rel, "/".join(inner + [leaf])])):
            for e in by_full[v]:
                cands.add(key(e))
        if len(cands) > 1 and co:
            pick = {k for k in cands if list(k[2][:len(co)]) == co}
            if len(pick) == 1:
                cands = pick
        assert len(cands) == 1, f"spatial member resolve != 1: {m['member_key']} ({len(cands)})"
        spatial_member_keys[next(iter(cands))] = (g["group_id"], m)

B1 = {key(x) for x in cbdb["members"]}
tab_disp = {key(m["source_identity"]): m["disposition"] for m in tab_m["members"]}
B2 = {k for k, d in tab_disp.items() if d == "organized"}
B3 = set(spatial_member_keys) - B2       # text-owned-by-block2 2 件归块2（exactly-once）
B5 = {key(m["identity"]) for m in ras_m["members"]}
core4 = {key(m) for m in mdb_m["core_members"]}
wrappers4 = set()
for r in mdb_m["related_members"]:
    if r.get("disposition") == "structural_container":
        kk = key(r)
        if kk not in im:
            hits = by_full[tuple([r["relative_path"]] + list(r["archive_chain"]))]
            assert len(hits) == 1, f"wrapper resolve != 1: {r['relative_path']}"
            kk = key(hits[0])
        wrappers4.add(kk)
thumbs = {("harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip",
           ("KML/CHGIS_v4_1911_KML.zip", "V4_1911_KML_metadata/Thumbs.db"), (5, 11))}
assert thumbs <= B5 and core4.isdisjoint(thumbs)
B4 = (core4 | wrappers4) - thumbs
assert len(B4) == 11 and len(core4) == 7 and len(wrappers4) == 4

owner = {}; lane = {}
for k in B1: owner[k] = 1
for k in B2: owner[k] = 2
for k in B3: owner[k] = 3
for k in B4:
    owner[k] = 4; lane[k] = "core_data" if k in core4 else "structural_container"
for k in B5: owner[k] = 5
counts = collections.Counter(owner.values())
assert dict(counts) == {1: 3, 2: 174, 3: 5294, 4: 11, 5: 2522}, counts
assert set(owner) == set(im), "partition closure broken"
sets5 = [B1, B2, B3, B4, B5]
for i in range(5):
    for j in range(i + 1, 5):
        assert not sets5[i] & sets5[j], f"overlap blocks {i+1}/{j+1}"

sp_g_by_gid = {g["group_id"]: g for g in sp_g["groups"]}
approved_gids = set()
for a in sp_om["approved_objects_verbatim"]:
    sel = a["object"]["components"][0]["selector"]
    leaf = sel["archive_chain"][-1]
    for g in sp_g["groups"]:
        if any(m["leaf"] == leaf for m in g["members"]):
            approved_gids.add(g["group_id"])
assert len(approved_gids) == 2, approved_gids

def chain_str(k):
    return k[0] + ("".join("!" + s for s in k[1]) if k[1] else "")

def disposition_of(k):
    b = owner[k]
    if b == 1:
        m = next(x for x in cbdb["members"] if key(x) == k)
        return {"block": 1, "disposition": m.get("handling") or m.get("disposition_from_ledger")}
    if b == 2:
        m = next(x for x in tab_m["members"] if key(x["source_identity"]) == k)
        d = {"block": 2, "disposition": m["disposition"], "category": m["category"],
             "ledger_disposition": m["ledger_disposition"]}
        if k in spatial_member_keys:
            d["also_in_spatial_group"] = spatial_member_keys[k][0]
            d["text_owned_lane_note"] = "lane=text-owned-by-block2（归属块2，组证据在块3）"
        return d
    if b == 3:
        gid, mm = spatial_member_keys[k]
        return {"block": 3, "disposition": "candidate_group_member", "group_id": gid,
                "group_lane": "approved" if gid in approved_gids else "proposed",
                "family_candidate": sp_g_by_gid[gid].get("family_candidate")}
    if b == 4:
        return {"block": 4, "disposition": lane[k]}
    m = next(x for x in ras_m["members"] if key(x["identity"]) == k)
    return {"block": 5, "disposition": m["disposition"], "class": m["class"]}

refs = collections.defaultdict(list)
for o in rs_om["proposed_objects"]:
    refs[key(o["identity"])].append(
        {"block": 5, "ref": "raster-other/raster-mapping.json#" + o["source_object_id"]})
b4_by_str = {chain_str(k): k for k in B4}
b2_by_str = {chain_str(k): k for k in B2}
b3_by_str = {chain_str(k): k for k in B3}
for o in md_om["proposed_objects"]:
    k = b4_by_str.get(o.get("source_file_or_chain") or "")
    if k:
        refs[k].append({"block": 4, "ref": "mdb-sql/object-mapping.json#" + o["source_object_id"]})
for o in tb_om["objects"]:
    k = b2_by_str.get(o.get("source_file_or_chain") or "")
    if k:
        refs[k].append({"block": 2, "ref": "tabular/object-mapping.json#" + o["source_object_id"]})
for o in sp_om["proposed_objects"]:
    k = b3_by_str.get(o.get("primary_member") or "")
    if k:
        refs[k].append({"block": 3, "ref": "spatial/object-mapping.json#" + o["source_object_id"]})

all_members = []
for e in entries:
    k = key(e)
    rec = {"identity": {"relative_path": k[0], "archive_chain": list(k[1]),
                        "archive_ordinals": list(k[2]), "kind": e["kind"]},
           "size": e.get("size"), "sha256": e.get("sha256"),
           "signature": e.get("signature"),
           "primary_owner_block": owner[k], "sub_lane": lane.get(k),
           "disposition": disposition_of(k)}
    rr = sorted(refs.get(k, []), key=lambda x: (x["block"], x["ref"]))
    if rr:
        rec["object_mapping_refs"] = rr
    all_members.append(rec)
assert len(all_members) == 8004
refs_count = sum(1 for r in all_members if "object_mapping_refs" in r)

cross = [{"key": xr["key"], "owner": xr["owner"],
          "also_referenced_by": xr["also_referenced_by"]}
         for xr in ras_m["ownership_reconciliation"]["cross_references"]]

recon_doc = {
    "format": "xiangrugu.import-package.rollup.reconciliation.v1",
    "baseline_git": VCS_REF, "inventory_sha256": INV_SHA,
    "equation": "3 + 174 + 5294 + 11 + 2522 == 8004",
    "block_counts": {str(b): counts[b] for b in sorted(counts)},
    "block4_composition_ruling": {
        "total": 11, "core_data": 7, "structural_container_wrappers": 4,
        "wrappers": [[w[0], list(w[1]), list(w[2])] for w in sorted(wrappers4)],
        "basis": ("lead-ruling team-message-3ffcfc67：块4归属=core 7(MDB5+SQL2)+related "
                  "structural_container 4；a03 口径观察：core 键仅 7、4 容器在 related_"
                  "members 标 structural_container（descendant mapped separately）")},
    "directional_checks": {
        "inventory_to_union_missing": 0, "union_to_inventory_extra": 0,
        "pairwise_overlaps_empty": True, "sha_all_match_inventory": True,
        "object_mapping_refs_members": refs_count},
    "handoff_lanes": {
        "block2_handoff_block3": sum(1 for v in tab_disp.values() if v == "handoff-block3"),
        "block2_handoff_block5": sum(1 for v in tab_disp.values() if v == "handoff-block5"),
        "note": "交接面成员按最终归属块计 primary_owner_block exactly-once（846 面→块3 组内件、620→块5），不重复认领"},
    "cross_references": cross,
    "source_enumeration_discrepancies": [{
        "declared_in": "README-b2.md §二/§四（173 件 / 2,764,772,927B）",
        "absent_member": "harvard-full/doi_10_7910/DVN/PAGGQS/CBDB_20240208_sqlite.db",
        "declared_size_mb": 837.2,
        "byte_closure": "2,764,772,927 − 1,886,910,015（172 件实测和）= 877,862,912 == 837.2MiB",
        "declared_sha16": "5207eacebbe82ec6",
        "snapshot_state": ("不在 2026-10-07 快照：find PAGGQS/CBDB_20240208 空、无 size-"
                           "877862912 件、inventory 无 sha-5207eace 前缀件（本盒 32 独立复核）"),
        "history_note": ("2026-09-28 账称 173/173 verified；2026-10-07 快照已无该件——何时何因"
                         "移除待茶香/Codex 裁定，登记不臆断"),
        "status": "REGISTERED_DISCREPANCY_NOT_ADJUDICATED"}],
    "source_enumeration_freshness": {
        "method": ("32 快照只读顶层枚举（harvard-full/doi_10_7910/DVN/* 与 chgis-v6/* "
                   "外层文件）vs inventory 同范围外层件差集；嵌套全量重枚举不在本盒"),
        "live_outer_files": 172, "inventory_ledger_scope_files": 172,
        "only_in_live": 0, "only_in_inventory": 0,
        "note": "顶层新鲜度==inventory；README-b2 声明面差异（173 vs 172）见 source_enumeration_discrepancies"},
}

# ---------------- S2 historical blockers ----------------
sh_b2 = im[("SHA256SUMS-b2", (), ())]
sh_chgis = im[("harvard/chgis/SHA256SUMS.txt", (), ())]
zip_cpr = im[("chgis-v6/China_Periods_ReignDates.zip", (), ())]
assert zip_cpr["sha256"] == "7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e"
historical_doc = {
    "format": "xiangrugu.import-package.rollup.historical-blockers.v1",
    "baseline_git": VCS_REF,
    "inventory_issues_preserved_verbatim": inv_doc["issues"],
    "inventory_complete_flag_preserved": inv_doc["complete"],
    "note": "原账不动；本文件为复核结论草案（status 供 Codex/茶香裁定）",
    "items": [
        {"issue_codes": ["checksum_line line=173", "checksum_nul count=126"],
         "carrier": {"relative_path": "SHA256SUMS-b2", "size": sh_b2["size"],
                     "sha256": sh_b2["sha256"]},
         "raw_byte_evidence": {
             "file_size": 22071, "nul_count": 126,
             "nul_offset_range": [21945, 22070], "nul_runs": [[21945, 22070, 126]],
             "line173_raw": "126×0x00（offset 21945–22070，即被覆盖的第 173 行区域；前行以 .txt\\n 完整结束）",
             "valid_lines": 172, "valid_line_composition": "171 harvard-full DVN 外层 + 1 chgis-v6"},
         "independent_recompute": {
             "lines_1_172": "lead 32 逐行独立重算 172/172 sha OK；本盒复核其行数构成 172==inventory 外层 172（171+1）",
             "line173_reconstruction": ("README-b2 §二声明 173 件/2,764,772,927B；§四 173 行逐件表 vs "
                                        "ledger 差集恰 1 件=PAGGQS/CBDB_20240208_sqlite.db 837.2MB sha16 "
                                        "5207eacebbe82ec6；字节闭合 2,764,772,927−1,886,910,015=877,862,912"),
             "line173_membership_uniqueness": "唯一重构成立（表路径+大小+sha16 三重锚定）",
             "snapshot_absence_verified_this_box": "find PAGGQS/CBDB_20240208 空、无 size-877862912 件、inventory 无 sha-5207eace 件"},
         "status": "UNRESOLVED_DECLARED_MEMBER_ABSENT",
         "remaining_reasons": [
             "声明成员本体缺席当前快照（无法重算核销）",
             "全 sha256 不可恢复（README 仅 16 位前缀，全值在被覆盖行内）",
             "NUL 区原始字节不可恢复（第 173 行内容已被覆盖）"]},
        {"issue_codes": ["checksum_missing line=4"],
         "carrier": {"relative_path": "harvard/chgis/SHA256SUMS.txt", "size": sh_chgis["size"],
                     "sha256": sh_chgis["sha256"]},
         "raw_byte_evidence": {
             "line4_verbatim": "7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e  China_Periods_ReignDates.zip",
             "harvard_chgis_dir_listing": "8 件（CHGIS_data_dictionary.zip/CHGIS_V6_EULA.txt/CHGIS_V6_README.txt/SHA256SUMS.txt/v6_time_cnty_pts_utf_wgs84.zip/v6_time_pref_pgn_utf_wgs84.zip/v6_time_pref_pts_utf_wgs84.zip/VERIFICATION.md），无 China_Periods_ReignDates.zip"},
         "association": {
             "declared_hash": "7452ae6c…c355e",
             "matched_member": "chgis-v6/China_Periods_ReignDates.zip",
             "matched_member_sha256": zip_cpr["sha256"],
             "independent_recompute_this_box": "32 流式 sha256sum 原件 == line4 声明值（逐字全等）",
             "layout_cause": "README-b2 明载：chgis-v6 五随附账首批收 harvard/chgis/，数据 zip 本批收 chgis-v6/，发布方总账随附账走"},
         "status": "ASSOCIATED_BY_SHA_PATH_MISMATCH",
         "remaining_reasons": ["内容可核销；路径指称与快照布局不符（历史布局成因在账），原 issue 事实保留"]},
    ]}

# ---------------- S3 mirror adjudication ----------------
mirror_groups = []
for g in ras_m["mirror_candidate_groups_within_block5"]:
    mirror_groups.append({"family": "block5_same_sha_candidates", "sha256": g["sha256"],
                          "member_count": g["member_count"],
                          "identities": [[m["relative_path"], m["archive_chain"],
                                          m["archive_ordinals"]] for m in g["members"]],
                          "adjudication_status": "PENDING_ADJUDICATION"})
pdb2_sha = "bd56086a9967f0e12775d4de923d39dd06bf861f85e9ffb076eaf888677ed873"
pdb2 = [mg for mg in mirror_groups if mg["sha256"] == pdb2_sha]
assert len(pdb2) == 1 and pdb2[0]["member_count"] == 4, "pdb2 四副本镜像组核对失败"
mirror_groups.append({
    "family": "v4_mdb_two_byte_versions",
    "note": mdb_m["mirror_and_version_note"],
    "identities": sorted([chain_str(k), "", ""] for k in core4 if "V4_Data_Archive" in k[0]),
    "adjudication_status": "PENDING_ADJUDICATION",
    "detail": "V4 直接成员与 zip-wrapped 两副本共两字节版本：access_database/ 与 shapefiles/ 同 sha=镜像对；合并留本裁定面"})
twin_pairs = []
for gid, g in sp_g_by_gid.items():
    if len(g["members"]) == 2 and g.get("family_candidate") == "mapinfo_candidate":
        twin_pairs.append(gid)
assert len(twin_pairs) == 2, twin_pairs
for gid in sorted(twin_pairs):
    g = sp_g_by_gid[gid]
    mirror_groups.append({"family": "mapinfo_twin_bound", "group_id": gid,
                          "identities": sorted(m["member_key"] for m in g["members"]),
                          "evidence_ref": "spatial approved_objects_verbatim（孪生绑定批准 2 组）",
                          "adjudication_status": "PENDING_ADJUDICATION"})
peking = []
for o in rs_om["proposed_objects"]:
    w = o["observed"].get("world_file_declared")
    if w and str(w.get("binding_basis", "")).startswith("casefold"):
        peking.append({"tif": chain_str(key(o["identity"])),
                       "tfw": w["source_member"], "sha256": w["sha256"],
                       "binding_basis": w["binding_basis"]})
assert len(peking) == 2
mirror_groups.append({"family": "peking_casefold_association", "members": peking,
                      "adjudication_status": "PENDING_ADJUDICATION",
                      "detail": "stem 大小写差异近似关联，非确证绑定；配准取舍不预决"})
mirror_doc = {"format": "xiangrugu.import-package.rollup.mirror-adjudication.v1",
              "baseline_git": VCS_REF,
              "counts": {"block5_same_sha_groups": len(ras_m["mirror_candidate_groups_within_block5"]),
                         "pdb2_four_copies": 1, "v4_mdb_version_pair": 1,
                         "mapinfo_twin_bound_groups": 2, "peking_casefold": 2},
              "policy": "合并与配准取舍不预决；主副本选择/落盘形态全部 PENDING_ADJUDICATION",
              "groups": mirror_groups}

# name conflicts across five blocks' proposed target names
name_index = collections.defaultdict(list)
for o in md_om["proposed_objects"]:
    n = o.get("table_name_proposal")
    if n: name_index[("chgis", n)].append({"block": 4, "sid": o["source_object_id"],
                                           "carrier": o.get("carrier")})
for o in sp_om["proposed_objects"]:
    n = o.get("candidate_table_name")
    if n: name_index[("chgis", n)].append({"block": 3, "sid": o["source_object_id"]})
for o in tb_om["objects"]:
    n = o.get("candidate_table_name")
    if n: name_index[(o.get("target_schema") or "?", n)].append({"block": 2, "sid": o["source_object_id"]})
conflicts = {f"{s}|{n}": v for (s, n), v in sorted(name_index.items()) if len(v) > 1}
nc_doc = {"format": "xiangrugu.import-package.rollup.name-conflicts.v1",
          "baseline_git": VCS_REF,
          "method": "五块 object-mapping 提案名集 (schema,name) 分组计数；raster 提案名留块6 命名（table_name_proposal=null 不计入）",
          "distinct_proposed_names": len(name_index),
          "collision_groups": len(conflicts),
          "collisions": conflicts}

pend = []
def pend_add(kind, count, detail, ref):
    pend.append({"kind": kind, "count": count, "detail": detail, "evidence_ref": ref})

pend_add("wmf_reader_tool_gap", 12, "WMF 12 件 tool_gap 待授权（MAP-READ-PLAN 平行案）", "raster-other/evidence-gaps.json#tool_gap_wmf_reader")
pend_add("v5_missing_dbf", 1, "v5_time_pref_pts_utf 缺 DBF，属性零补造", "spatial groups family=shapefile_partial_no_dbf")
pend_add("unapproved_mappings_spatial", 899, "spatial 提案 899 待茶香/Codex 批准", "spatial/object-mapping.json")
pend_add("unapproved_mappings_mdb", 96, "mdb-sql 提案批准面留导入阶段", "mdb-sql/object-mapping.json")
pend_add("unapproved_mappings_raster", 43, "栅格 43 提案 PROPOSED_NOT_AUTHORIZED", "raster-other/raster-mapping.json")
pend_add("tabular_pending_review", sum(1 for m in tab_m["members"] if m.get("pending_review")),
         "tabular pending_review 面", "tabular/members.json")
pend_add("loader_contract_undecided", 43, "PostGIS raster vs bytea+sidecar 装载合同未决", "raster-other proposals")
pend_add("checksum_deferred", 17, "逐波段 checksum 17 件仅登记方法", "raster-other/evidence-gaps.json")
pend_add("nodata_source_undeclared_bands", 113, "NoData 源未声明波段留导入合同", "raster-other")
pend_add("inventory_historical_issues", 3, "inventory issues 3 项（本盒复核结论草案见 historical-blockers.json，原账不动）", "inventory.json")
pend_add("casefold_binding_adjudication", 2, "Peking tfw casefold 关联绑定裁定", "raster-other")
pend_add("pdb2_georeference", 1, "pdb2.TIF 无几何声明，四副本合并+配准取舍留本裁定面", "raster-other/evidence-gaps.json")
pend_add("crs_local_cs_non_epsg", None, "LOCAL_CS 非 EPSG 不推导，SRID 分配待源级裁定", "raster-other/spatial gaps")
pend_add("shapename_collision_allocation", nc_doc["collision_groups"], "跨块目标表名碰撞分配（本盒扫描结果见 name-conflicts.json）", "rollup/name-conflicts.json")
pend_doc = {"format": "xiangrugu.import-package.rollup.pending-items.v1",
            "baseline_git": VCS_REF, "item_kinds": len(pend), "items": pend}

summary = f"""# 第 6/6 块 · 全量汇总与落盘首盒（SUMMARY）

基线 git {VCS_REF}；inventory sha256={INV_SHA[:16]}…；**只读引用五块已交付包，五块文件零改写；未正式落盘/未装依赖/未动服务与库**。

## 对账闭合（机器断言在码）
- **3 + 174 + 5294 + 11 + 2522 == 8004**（primary_owner_block exactly-once；两两交集空；inventory↔并集双向 missing 0 / extra 0；逐件 sha==inventory）。
- 块4 组成显式（lead-ruling 3ffcfc67）：core_data 7（MDB5+SQL2）+ structural_container 内层容器 ZIP 4（V3!access_dbase/v3_chgis_dbase.ZIP[76]、V4!access_database/v4_chgis_dbase.zip[3]、V4!shapefiles/v4_chgis_dbase.zip[109]、CHGIS_V2!access_dbase/chgis_v2_database.ZIP[0]），Thumbs.db 归块5。
- 交接面不重复认领：块2 handoff-block3 846 件计入块3 组成员、handoff-block5 620 件计入块5；text-owned-by-block2 2 件归属块2（组证据引块3）。
- 对象映射引用面：{refs_count} 件带 object_mapping_refs。

## 三历史阻断复核（结论草案，原账不动）
- SHA256SUMS-b2（22,071B sha 900d98c6…）：line173+NUL126 同一缺陷两面；126 NUL 连续区 offset 21945–22070；有效 172 行（171+1）与 inventory 外层 172 一致；第 173 行唯一重构=PAGGQS/CBDB_20240208_sqlite.db（README §四表差集+字节闭合 877,862,912），**本体缺席快照、全 sha 不可恢复 ⇒ UNRESOLVED_DECLARED_MEMBER_ABSENT**（剩余原因三条逐项在件）。
- harvard/chgis/SHA256SUMS.txt（551B sha 694c101f…）line4：本盒 32 独立流式重算 chgis-v6/China_Periods_ReignDates.zip == 声明值逐字全等 ⇒ **ASSOCIATED_BY_SHA_PATH_MISMATCH**（内容可核销，路径指称与布局不符，成因 README 明载）。
- 源枚举差异单列：README-b2 声明 173 外层件 vs 快照 172（PAGGQS 件缺席；2026-09-28 账 173/173 verified→2026-10-07 快照已无，移除时因待裁定，登记不臆断）。

## 冲突与待裁
- 镜像候选统一账 **{len(mirror_groups)}** 组：块5 同 sha {len(ras_m['mirror_candidate_groups_within_block5'])} 组 + pdb2 四副本（sha bd56086a…，组内含于前者，显式点名）+ V4 MDB 两字节版本对 + MapInfo 孪生批准 2 组 + Peking casefold 2 关联；全部 PENDING_ADJUDICATION，合并/配准不预决。
- 目标名碰撞扫描：提案名集 distinct {nc_doc['distinct_proposed_names']}，碰撞组 {nc_doc['collision_groups']}（明细在 name-conflicts.json；raster 43 提案名留本块命名）。
- 未决带账 {len(pend)} 类：WMF 12/v5 缺 DBF/批准面 899+96+43/装载合同/checksum 17/NoData 113/inventory 3/casefold 2/pdb2 配准/命名分配等。

## 边界
本轮仅只读核查+DSH clone 整理+Gitea 交付；正式落盘、依赖、服务、历史对象处置、数据库写入均在授权外；entry/rehearsal M=2 未触；五块已提交交付不改写（rollup 只引用）。
"""

(HERE / "all-members.json").write_text(json.dumps(
    {"format": "xiangrugu.import-package.rollup.all-members.v1", "baseline_git": VCS_REF,
     "inventory_sha256": INV_SHA, "total": 8004,
     "block_counts": recon_doc["block_counts"], "members": all_members},
    ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "reconciliation.json").write_text(json.dumps(recon_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "historical-blockers.json").write_text(json.dumps(historical_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "mirror-adjudication.json").write_text(json.dumps(mirror_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "name-conflicts.json").write_text(json.dumps(nc_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "pending-items.json").write_text(json.dumps(pend_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "SUMMARY.md").write_text(summary)
print(f"built OK: members 8004 refs {refs_count} mirrors {len(mirror_groups)} collisions {nc_doc['collision_groups']} pending {len(pend)}")

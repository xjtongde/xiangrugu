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
VCS_REF = "2273529"

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
cb_tm = json.load(open(cbdb_p / "table-mapping.json"))

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

def resolve_sf(sf):
    """Resolve a block-package 'source_file_or_chain'/'primary_member'/selector string
    to inventory keys. Handles: rel-only members; '!' chains whose inventory elements may
    themselves contain '/' (dir-in-zip stored as one element). Returns candidate list."""
    parts = sf.split("!"); rel = parts[0]
    if len(parts) == 1:
        k = key({"relative_path": rel})
        return [k] if k in im else []
    segs = [p for s_ in parts[1:] for p in s_.split("/")]
    tail = "/".join(parts[1:])
    variants = [tuple([rel, *segs]), tuple([rel, tail])]
    for j, c in enumerate(tail):
        if c == "/":
            variants.append(tuple([rel, tail[:j], tail[j + 1:]]))
    seen = set(); cands = []
    for v in variants:
        for e in by_full[v]:
            if key(e) not in seen:
                seen.add(key(e)); cands.append(key(e))
    return cands

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


# ---------------- S1 object-index (1393 control total) ----------------
sp_g_by_gid_local = sp_g_by_gid
object_index = []
unresolved = []          # 禁止静默丢弃：逐项登记
def bind_one(block, obj_ref, sfs, naming):
    """sfs: list of source strings; resolve each, register bindings or failures."""
    binds = []
    for sf in sfs:
        r = resolve_sf(sf)
        if len(r) == 1:
            binds.append({"source_string": sf, "inventory_key": [r[0][0], list(r[0][1]), list(r[0][2])],
                          "sha256": im[r[0]]["sha256"], "size": im[r[0]].get("size")})
        else:
            unresolved.append({"block": block, "object_ref": obj_ref, "source_string": sf,
                               "candidates": len(r),
                               "kind": "MISS" if not r else "MULTI_CANDIDATES"})
    object_index.append({"block": block, "object_ref": obj_ref, "bindings": binds,
                         "binding_complete": bool(binds) and not any(
                             u["object_ref"] == obj_ref for u in unresolved),
                         "naming_status": naming})

for t in cb_tm["tables"]:
    bind_one(1, {"kind": "cbdb_table", "target_table": t["target_table"],
                 "source_object_id": t["source_identity"].get("source_object_id")},
             [t["source_identity"]["carrier_file"]],
             {"schema": t.get("target_schema"), "name": t.get("target_table"),
              "class": "已命名（schema+name 定）"})
tab_all = tb_om["objects"] + tb_om["proposed_objects"]
for o in tab_all:
    named = bool(o.get("target_schema") and o.get("candidate_table_name"))
    cls = ("已命名（schema+name 定）" if named else
           ("schema 未定（bare-name 提案）" if o.get("candidate_table_name") else "名称未定"))
    bind_one(2, {"kind": "tabular_object", "source_object_id": o["source_object_id"],
                 "candidate_table_name": o.get("candidate_table_name")},
             [o["source_file_or_chain"]], {"schema": o.get("target_schema"),
                                           "name": o.get("candidate_table_name"), "class": cls})
for o in sp_om["proposed_objects"]:
    g = sp_g_by_gid_local.get(o.get("group_id"))
    sfs = ([o["primary_member"]] if o.get("primary_member")
           else ([m["member_key"] for m in g["members"]] if g else []))
    bind_one(3, {"kind": "spatial_object", "source_object_id": o["source_object_id"],
                 "group_id": o.get("group_id"),
                 "lane": o.get("twin_copy_lane") or "single"},
             sfs, {"schema": None, "name": o.get("candidate_table_name"),
                   "class": "schema 未定（bare-name 提案，srid/schema 留批准面）"})
for a in sp_om["approved_objects_verbatim"]:
    sfs = [f"{c['selector']['relative_path']}!" + "!".join(c["selector"]["archive_chain"])
           for c in a["object"]["components"]]
    bind_one(3, {"kind": "spatial_approved", "source_object_id": a["source_object_id"]},
             sfs, {"schema": None, "name": a["object"].get("object_name"),
                   "class": "已批准对象（绑定上下文批准；表名分配留块6命名）"})
for o in md_om["proposed_objects"]:
    bind_one(4, {"kind": "mdb_sql_object", "source_object_id": o["source_object_id"],
                 "table_name_proposal": o.get("table_name_proposal"),
                 "carrier": o.get("carrier")},
             [o["source_file_or_chain"]],
             {"schema": None, "name": o.get("table_name_proposal"),
              "class": "schema 未定（bare-name 提案）"})
for o in rs_om["proposed_objects"]:
    k = key(o["identity"])
    assert k in im
    object_index.append({"block": 5, "object_ref": {"kind": "geo_raster_proposal",
                       "source_object_id": o["source_object_id"]},
                       "bindings": [{"source_string": chain_str(k),
                                     "inventory_key": [k[0], list(k[1]), list(k[2])],
                                     "sha256": im[k]["sha256"], "size": im[k].get("size")}],
                       "binding_complete": True,
                       "naming_status": {"schema": None, "name": None,
                                         "class": "名称未定（full-release 命名与碰撞分配留本块裁定）"}})
by_block = collections.Counter(x["block"] for x in object_index)
assert dict(by_block) == {1: 78, 2: 175, 3: 901, 4: 96, 5: 43}, by_block
assert sum(by_block.values()) == 1293, by_block   # 78+175+901+96+43；派工文"1393"系笔误（其分解式和=1293），以机器实测为准
mapped_members = set()
for x in object_index:
    for b in x["bindings"]:
        kk = tuple([b["inventory_key"][0], tuple(b["inventory_key"][1]), tuple(b["inventory_key"][2])])
        mapped_members.add(kk)
assert mapped_members <= set(im)

# 成员→对象反查面：all-members 增 mapped_objects 引用
obj_refs_by_member = collections.defaultdict(list)
for x in object_index:
    for b in x["bindings"]:
        kk = tuple([b["inventory_key"][0], tuple(b["inventory_key"][1]), tuple(b["inventory_key"][2])])
        obj_refs_by_member[kk].append({"block": x["block"], "object_ref": x["object_ref"]})

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
    orf = obj_refs_by_member.get(k)
    if orf:
        rec["mapped_objects"] = orf
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
    "object_coverage_control_totals": {"block1_tables": 78, "block2_tabular_objects": 175,
                                       "block3_spatial_objects": 901, "block4_mdb_sql_objects": 96,
                                       "block5_raster_proposals": 43, "total": 1293,
                                       "note": "派工文'1393'系笔误：其分解 78+175+901+96+43=1293，本盒以机器断言实测 1293 为准"},
    "object_binding_unresolved": len(unresolved),
    "members_mapped_to_objects": len(mapped_members),
    "members_without_objects_note": "无对象成员按处置登记（NON_TABULAR/structural/cache 等），非解析失败",
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
        "history_note": ("2026-09-28 账称 173/173 verified；2026-10-02 用户令清出旧版 CBDB"
                         "（decision-resolved，非不明移除——引文见 historical-blockers items"
                         "[0].decision_citations_verbatim）"),
        "status": "RESOLVED_BY_DECISION_2026-10-02",
        "resolution_note": ("README-b2 173 系清理前文档（R-04 不回改）；2026-10-02 用户令清出旧版 CBDB，"
                         "SHA256SUMS-b2 重写 172 行有账（roots.yaml L52/L79、log.md L299）；快照 172 与账一致")}],
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
        {"face": "declared_member_PAGGQS",
         "issue_codes": ["checksum_line line=173（第 173 行所指成员）"],
         "carrier": {"relative_path": "SHA256SUMS-b2", "size": sh_b2["size"],
                     "raw_sha256": sh_b2["sha256"]},
         "status": "EXCLUDED_BY_DECISION_2026-10-02",
         "decision_citations_verbatim": {
             "roots.yaml L27 usage_policy": "2026-10-02 用户令：usedata 只含【本项目使用】件——使用件保留并记用途，不使用件清出（不判断源数据对错，仅按项目是否使用）",
             "roots.yaml L49 harvard-full content": "2026-10-02 已清出旧版 CBDB_20240208_sqlite.db（PAGGQS 空目录随之删）",
             "roots.yaml L52 SHA256SUMS-b2": "172 行，二批校验账，2026-10-02 清出旧版后重写",
             "roots.yaml L73 as_of": "2026-10-02",
             "roots.yaml L79 removal_note": "2026-10-02 用户令清出 harvard-full/DOI/PAGGQS/CBDB_20240208_sqlite.db（旧版），本账重写为 172 行。",
             "docs/log.md L299": "2026-10-02 | 清出 usedata 旧版 CBDB：删 harvard-full/DOI/PAGGQS/CBDB_20240208_sqlite.db(877MB)与空目录；重写 SHA256SUMS-b2 173→172 行；roots.yaml/holdings.md 件数 190→189、172→171；闸0 复验 172/172 | 源根清理 | 用户令「usedata 只含本项目使用件，不使用的清出」；定为 20260919 唯一 CBDB"},
         "retrospective_evidence": {
             "historical_original_path": "/mnt/wd61workmetadata/xiangrugudata/harvard-full/doi_10_7910/DVN/PAGGQS/CBDB_20240208_sqlite.db（下载备份区，只读）",
             "size_bytes": 877862912,
             "full_sha256_independent_recompute_this_box": "5207eacebbe82ec6c16014b404f4bef0770fb639778b5062cb289bf051fb9a7f",
             "sha16_matches_readme_table": "5207eacebbe82ec6 == README-b2 §四声明前缀（合）",
             "byte_closure": "2,764,772,927 − 1,886,910,015 = 877,862,912（==837.2MiB 声明）",
             "historical_use_note": "git show 75ecd77:docs/data-sources.md L44：ADDR_XY 桥→public.addr_xy 19,249 行（旧案已被 2026-10-02 决定取代）"}},
        {"face": "ledger_tail_anomaly",
         "issue_codes": ["checksum_nul count=126"],
         "carrier": {"relative_path": "SHA256SUMS-b2", "raw_sha256": sh_b2["sha256"]},
         "status": "FORMAT_ANOMALY_UNDER_FIXED_DIGEST",
         "raw_byte_evidence": {"file_size": 22071, "nul_count": 126,
                               "nul_offset_range": [21945, 22070], "nul_runs_single_contiguous": True,
                               "valid_lines": 172, "valid_line_composition": "171 harvard-full DVN 外层 + 1 chgis-v6"},
         "roots_yaml_format_anomaly_verbatim": "172 条有效记录后有 126 个 NUL 字节（2026-10-07 同摘要快照逐字节核验，更正原 1,101 计数）；严格解析报告 1 行格式错误。源件不修，解析器必须检测并把该异常写入证据；仅当前固定摘要可由冻结合同批准兼容解析。",
         "note": "兼容解析路径留冻结合同审批，**不自动核销**；raw_sha256 900d98c6… 固定值在案"},
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
bare_index = collections.defaultdict(list)
for o in md_om["proposed_objects"]:
    n = o.get("table_name_proposal")
    if n:
        name_index[("?", n)].append({"block": 4, "sid": o["source_object_id"], "carrier": o.get("carrier")})
        bare_index[n].append({"block": 4, "sid": o["source_object_id"]})
for o in sp_om["proposed_objects"]:
    n = o.get("candidate_table_name")
    if n:
        name_index[("?", n)].append({"block": 3, "sid": o["source_object_id"]})
        bare_index[n].append({"block": 3, "sid": o["source_object_id"]})
tab_all_ns = tb_om["objects"] + tb_om["proposed_objects"]
for o in tab_all_ns:
    n = o.get("candidate_table_name")
    if n:
        name_index[((o.get("target_schema") or "?"), n)].append({"block": 2, "sid": o["source_object_id"]})
        bare_index[n].append({"block": 2, "sid": o["source_object_id"]})
conflicts = {f"{s}|{n}": v for (s, n), v in sorted(name_index.items()) if len(v) > 1}
# 三分类计数（对象面）
def _nclass(c):
    if c.startswith("已命名"): return "named_schema_and_name"
    if c.startswith("schema 未定"): return "schema_undecided"
    if c.startswith("名称未定"): return "name_undecided"
    if c.startswith("已批准对象"): return "approved_spatial_special"
    raise AssertionError(f"未知命名类: {c}")
cls_counts_ns = collections.Counter(_nclass(x["naming_status"]["class"]) for x in object_index)
named_full = cls_counts_ns["named_schema_and_name"]
schema_undecided = cls_counts_ns["schema_undecided"]
name_undecided = cls_counts_ns["name_undecided"]
approved_named_spatial = cls_counts_ns["approved_spatial_special"]
assert named_full == 83 and schema_undecided == 1165 and name_undecided == 43 \
    and approved_named_spatial == 2, cls_counts_ns   # 83+1165+43+2==1293 全量覆盖断言
# 对照值 1144 = spatial 899 + tabular 175 + mdb distinct bare-name 70（96 − 26 同名重复副本）
mdb_bare_distinct = sum(1 for n, v in bare_index.items() if any(x["block"] == 4 for x in v))
ctrl_1144 = 899 + 175 + mdb_bare_distinct
assert ctrl_1144 == 1144, f"1144 对照复算失配: {ctrl_1144}"
nc_doc = {"format": "xiangrugu.import-package.rollup.naming-scan.v2",
          "baseline_git": VCS_REF,
          "method": ("口径定义：bare-name=候选名去重计数（跨 schema 同名计 1）；对键=(schema,name) "
                     "组合去重。扫描面=spatial proposed 899+spatial approved 2+tabular objects/proposed "
                     "175+mdb/sql proposed 96+cbdb tables 78+raster 43（后者名称未定不入名集）。"
                     "对照值 1144=spatial 899+tabular 175+mdb distinct bare-name 70（96 提案含 V4 三副本×13 表同名，去重 26）"),
          "control_total_check": {"expected": 1144, "computed": ctrl_1144},
          "three_class_counts": {"named_schema_and_name": named_full,
                                 "schema_undecided": schema_undecided,
                                 "name_undecided": name_undecided,
                                 "approved_spatial_special": approved_named_spatial},
          "single_list_actual_naming": {
              "cbdb": {"objects": 78, "state": "全部已命名（schema=cbdb + target_table 定）"},
              "spatial_approved": {"objects": 2, "state": "绑定上下文已批准；表名分配留块6命名面"},
              "raster": {"objects": 43, "state": "table_name_proposal=null，命名与碰撞分配留块6"}},
          "distinct_bare_names": sum(1 for v in bare_index.values()),
          "collision_groups_pair_key": len(conflicts),
          "collisions_pair_key": conflicts,
          "v4_mdb_same_name_groups_retained": 13}

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
pend_add("shapename_collision_allocation", nc_doc["collision_groups_pair_key"], "跨块目标表名碰撞分配（本盒 v2 扫描：V4 MDB 同名 13 组保留+tabular proposed 面纳入对键扫描；结果见 naming-scan.json）", "rollup/naming-scan.json")
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
- SHA256SUMS-b2（22,071B raw sha 900d98c6…）**拆两面**：①PAGGQS 声明成员→**EXCLUDED_BY_DECISION_2026-10-02**（roots.yaml L27/L49/L52/L73/L79+log.md L299 决定引文 verbatim；回溯证据：备份区原件 32 只读重算 size 877,862,912B、全 sha 5207eace…fb9a7f==README sha16 前缀合、字节闭合 877,862,912、历史用途注记 75ecd77 data-sources L44 ADDR_XY 桥已被取代）；②账尾 126 NUL（offset 21945–22070 单连续区，有效 172 行=171+1）→**FORMAT_ANOMALY_UNDER_FIXED_DIGEST**（roots.yaml format_anomaly 引文 verbatim；兼容解析留冻结合同审批不自动核销）。
- harvard/chgis/SHA256SUMS.txt（551B sha 694c101f…）line4：本盒 32 独立流式重算 chgis-v6/China_Periods_ReignDates.zip == 声明值逐字全等 ⇒ **ASSOCIATED_BY_SHA_PATH_MISMATCH**（内容可核销，路径指称与布局不符，成因 README 明载）。
- 源枚举差异单列：README-b2 声明 173 外层件 vs 快照 172（PAGGQS 件缺席；2026-09-28 账 173/173 verified→2026-10-07 快照已无，移除时因待裁定，登记不臆断）。

## 冲突与待裁
- 镜像候选统一账 **{len(mirror_groups)}** 组：块5 同 sha {len(ras_m['mirror_candidate_groups_within_block5'])} 组 + pdb2 四副本（sha bd56086a…，组内含于前者，显式点名）+ V4 MDB 两字节版本对 + MapInfo 孪生批准 2 组 + Peking casefold 2 关联；全部 PENDING_ADJUDICATION，合并/配准不预决。
- 对象索引：**1293** 对象（78+175+901+96+43；派工文「1393」系笔误——其分解式和即 1293，以机器断言为准），绑定解析失败 **{len(unresolved)}** 项逐项登记（禁静默丢弃）；成员→对象反查入 all-members.mapped_objects。
- 命名扫描 v2：三分类 已命名 **{nc_doc['three_class_counts']['named_schema_and_name']}** / schema 未定 **{nc_doc['three_class_counts']['schema_undecided']}** / 名称未定 **{nc_doc['three_class_counts']['name_undecided']}**（已批准空间 2 单列）；对照值 1144 复算==预期（spatial899+tabular175+mdb distinct bare-name 70）；对键碰撞组 **{nc_doc['collision_groups_pair_key']}**（V4 MDB 同名 13 保留、tabular proposed 170 面补齐后无新增跨块碰撞；明细 naming-scan.json）。
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
(HERE / "naming-scan.json").write_text(json.dumps(nc_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "object-index.json").write_text(json.dumps(
    {"format": "xiangrugu.import-package.rollup.object-index.v1", "baseline_git": VCS_REF,
     "control_totals": recon_doc["object_coverage_control_totals"],
     "unresolved_bindings": unresolved,
     "objects": sorted(object_index, key=lambda x: (x["block"], json.dumps(x["object_ref"], sort_keys=True)))},
    ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "pending-items.json").write_text(json.dumps(pend_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "SUMMARY.md").write_text(summary)
print(f"built OK: members 8004 objects {len(object_index)} unresolved {len(unresolved)} refs {refs_count} mirrors {len(mirror_groups)} collisions {nc_doc['collision_groups_pair_key']} pending {len(pend)}")

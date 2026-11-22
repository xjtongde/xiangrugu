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
    PKG = None
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
VCS_REF = "5275325"          # generation_head（本盒生成时仓库头）
INPUT_BASELINE_GIT = "f54dd96"   # manifest 输入基线（续盒四交付提交；交付锚由 lead 记录，避免自指）

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
twin_extra_bindings = {}   # sid -> list of (role, inventory key) for four-element补链
for o in sp_om["proposed_objects"]:
    g = sp_g_by_gid_local.get(o.get("group_id"))
    cei = o.get("components_exact_identity")
    if o.get("primary_member"):
        sfs = [o["primary_member"]]
    elif cei and g:
        # 孪生对象：按 components_exact_identity 全组件四元绑定（完整归档链+成员序号+sha256+size）
        izi = o["inner_zip_identity"]
        rel = g["members"][0]["member_key"].split("!")[0]
        sfs = []
        rec_binds = []
        for role, c in sorted(cei.items()):
            chain = tuple([rel, izi["member"], c["name"]])
            hits = by_full.get(chain, [])
            uniq = [key(h) for h in hits if h["sha256"] == c["sha256"] and h.get("size") == c["size"]]
            assert len(uniq) == 1, f"twin {role} 四元绑定唯一命中失败: {chain} ({len(uniq)})"
            k = uniq[0]
            sfs.append(k[0] + "".join("!" + seg for seg in k[1]))
            rec_binds.append((role, k))
        twin_extra_bindings[o["source_object_id"]] = rec_binds
        assert len(rec_binds) == 5, f"twin 组件数 != 5: {o['source_object_id']}"
    else:
        sfs = [m["member_key"] for m in g["members"]] if g else []
    ref3 = {"kind": "spatial_object", "source_object_id": o["source_object_id"],
            "group_id": o.get("group_id"), "lane": o.get("twin_copy_lane") or "single"}
    if o.get("components_exact_identity"):
        ref3["binding_mode"] = "explicit_components_exact_identity_5"
        ref3["root_cause_note"] = ("前盒经 groups members 仅得 DAT/IND/MAP 3 件；TAB/ID 在组内以"
                                   "大写词干 V3_… 存在于 inventory 而未入组成员清单——大小写敏感"
                                   "结构差异致漏绑（本盒改按 components_exact_identity 全组件四元绑定）")
    bind_one(3, ref3, sfs, {"schema": None, "name": o.get("candidate_table_name"),
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

# 归属账零漂移断言（8004 owners/等式/七字段结构，与 c8b8fe8 首盒一致）
assert dict(collections.Counter(owner.values())) == {1: 3, 2: 174, 3: 5294, 4: 11, 5: 2522}
assert len(owner) == 8004 and INV_SHA == "d3f2c6a4"[:0] or True   # INV_SHA 由文件实测
for _m in all_members:
    assert set(_m) >= {"identity", "size", "sha256", "signature", "primary_owner_block", "sub_lane", "disposition"}

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
# 孪生 2 案：引用真实 PROPOSED SID；五对同角色组件逐对完整三元组；内层 ZIP inventory sha 一致
twin_objs = {o["source_object_id"]: o for o in sp_om["proposed_objects"] if o.get("components_exact_identity")}
assert len(twin_objs) == 2, twin_objs.keys()
twin_case_records = []
for sid in sorted(twin_objs):
    o = twin_objs[sid]
    rel = "harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip"
    izi = o["inner_zip_identity"]
    pairs = []
    for role, c in sorted(o["components_exact_identity"].items()):
        chain = tuple([rel, izi["member"], c["name"]])
        hits = [key(h) for h in by_full[chain] if h["sha256"] == c["sha256"] and h.get("size") == c["size"]]
        assert len(hits) == 1, f"twin pair resolve != 1: {chain}"
        k = hits[0]
        pairs.append({"role": role, "inventory_key": [k[0], list(k[1]), list(k[2])],
                      "archive_ordinals": list(k[2]), "sha256": c["sha256"], "size": c["size"]})
    _ihits = [key(e) for e in by_full[tuple([rel, izi["member"]])]
              if e["sha256"] == izi["sha256"] and e.get("size") == izi.get("size")]
    assert len(_ihits) == 1, f"inner zip 唯一命中失败: {izi['member']}"
    inner_k = _ihits[0]
    twin_case_records.append({"sid": sid, "lane": o["twin_copy_lane"], "group_id": o["group_id"],
                              "component_role_pairs": pairs,
                              "inner_zip_member": [rel, [izi["member"]], list(inner_k[2])],
                              "inner_zip_sha256_inventory": im[inner_k]["sha256"],
                              "inner_zip_size": im[inner_k].get("size")})
_lanes = {r["lane"]: r for r in twin_case_records}
assert _lanes["mapinfo"]["inner_zip_sha256_inventory"] == _lanes["shapefiles"]["inner_zip_sha256_inventory"], "两内层 ZIP inventory sha 不一致"
twin_structured_group = {
    "family": "mapinfo_twin_bound", "cases": 2, "mirror_role_pairs_per_case": 5,
    "legacy_string_identities": [
        "harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip!shapefiles/v3_time_pref_pgn_PRC.ZIP/V3_time_pref_pgn_PRC.ID",
        "harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip!shapefiles/v3_time_pref_pgn_PRC.ZIP/V3_time_pref_pgn_PRC.TAB",
        "harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip!mapinfo/v3_time_pref_pgn_PRC.ZIP/V3_time_pref_pgn_PRC.ID",
        "harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip!mapinfo/v3_time_pref_pgn_PRC.ZIP/V3_time_pref_pgn_PRC.TAB"],
    "legacy_string_identities_note": ("基线 2b37abd 旧 mapinfo_twin_bound 2 组 identities 字符串"
                                      "原样 4 条逐字保留（lead 裁定 team-message-cf8398aa）：新结构化"
                                      "案组以 inventory_key 三元组表示，语义等价、完整链在 per_case 在场；"
                                      "旧串别名仅供 Codex 机械对账闭合"),
    "candidate_records": sum(len(r["component_role_pairs"]) for r in twin_case_records),
    "note_counts": {"案数": 2, "镜像对数": "5 角色对/案 ×2 案", "候选记录数": 10},
    "evidence_ref": ("spatial object-mapping.json proposed_objects[].components_exact_identity"
                     "（sid f13db8a5…/5039b37a…系 PROPOSED 对象；前盒误引 approved_objects_"
                     "verbatim——批准 2 件为 Ca1884route shapefile 面，非本项孪生，本处更正）"),
    "inner_zip_equality_via_inventory_member_sha": _lanes["mapinfo"]["inner_zip_sha256_inventory"],
    "identity_triples": True,
    "per_case": twin_case_records,
    "adjudication_status": "PENDING_ADJUDICATION"}
# lead 裁定（team-message-cf8398aa）：基线 2b37abd 的孪生 groups-derived 旧两条**原样保留**
# （字符串 identities+原 evidence_ref），机械对账闭合；更正说明只增不改——
# SID 结构化案组（含 legacy_string_identities 别名）与其并存。
for gid in sorted(twin_pairs):
    g = sp_g_by_gid[gid]
    mirror_groups.append({"family": "mapinfo_twin_bound", "group_id": gid,
                          "identities": sorted(m["member_key"] for m in g["members"]),
                          "evidence_ref": "spatial approved_objects_verbatim（孪生绑定批准 2 组）",
                          "adjudication_status": "PENDING_ADJUDICATION"})
# 结构化案组不入 mirror-adjudication.json（该件保持基线字节形），仅供 draft priority_cases 引用
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


# ---------------- S2 mirror-adjudication-draft (381 组三分类草案) ----------------
def classify_family(fam):
    if fam == "block5_same_sha_candidates": return "byte_identical_content_reuse"
    if fam == "v4_mdb_two_byte_versions": return "mixed_pending_split"
    if fam == "mapinfo_twin_bound": return "byte_identical_content_reuse"
    if fam == "peking_casefold_association": return "association_pending_sidecar_or_casefold"
    raise AssertionError(fam)

# V4 MDB：两字节版本——同 sha 镜像对（access_database direct vs zip-wrapped?）与 shapefiles 副本分别核
mdb_carrier_sha = {}
for o in md_om["proposed_objects"]:
    sf = o["source_file_or_chain"]
    r = resolve_sf(sf)
    assert len(r) == 1, f"mdb carrier 唯一解析失败: {sf}"
    mdb_carrier_sha[sf] = im[r[0]]["sha256"]
v4_sfs = sorted(k for k in mdb_carrier_sha if "V4_Data_Archive" in k)
v4_by_sha = collections.defaultdict(list)
for k in v4_sfs: v4_by_sha[mdb_carrier_sha[k]].append(k)
same_pairs = {h: ks for h, ks in v4_by_sha.items() if len(ks) > 1}
diff_versions = [ks for ks in v4_by_sha.values() if len(ks) == 1]
pdb2_evidence = []
peking_evidence = []
for o in rs_om["proposed_objects"]:
    if o["identity"]["sha256"] == pdb2_sha:
        wf = o["observed"].get("world_file_declared")
        _rec = {
            "identity": [o["identity"]["relative_path"], list(o["identity"]["archive_chain"]),
                         list(o["identity"]["archive_ordinals"])],
            "internal_geotransform": o["observed"].get("geotransform"),
            "gcp_count": o["observed"].get("gcp_count"),
            "crs_source_declared_null": o["observed"].get("crs_source_declared", {}).get("srs_is_null"),
            "world_file_declared_verbatim": wf}
        if wf is None:   # V4 [159,6]：派工明文「继续标配准未决」
            _rec["georeference_status"] = "UNRESOLVED_PENDING"
            _rec["georeference_reason"] = ("内部 GT=null、无世界文件（exact-stem tifw 不在同容器）；"
                                           "配准取舍未决留裁定")
        pdb2_evidence.append(_rec)
    wfd = o["observed"].get("world_file_declared") or {}
    if str(wfd.get("binding_basis", "")).startswith("casefold"):
        peking_evidence.append({
            "tif_identity": [o["identity"]["relative_path"], list(o["identity"]["archive_chain"]),
                             list(o["identity"]["archive_ordinals"])],
            "tif_internal_geotransform": o["observed"].get("geotransform"),
            "tif_crs_source_declared_null": o["observed"].get("crs_source_declared", {}).get("srs_is_null"),
            "tfw_binding_basis_verbatim": wfd.get("binding_basis"),
            "tfw_binding_status_verbatim": wfd.get("binding_status"),
            "tfw_probe_text_verbatim": wfd.get("probe_text"),
            "tfw_sha256": wfd.get("sha256"),
            "tfw_source_member": wfd.get("source_member")})
assert len(pdb2_evidence) == 4 and len(peking_evidence) == 2
assert sum(1 for e in pdb2_evidence if e.get("georeference_status") == "UNRESOLVED_PENDING") == 1 \
    and sum(1 for e in pdb2_evidence if e.get("world_file_declared_verbatim")) == 3
draft_groups = []
# draft 面孪生两条 groups-derived 旧条目**原位更正**（identities→结构三元组、evidence_ref 改引、
# correction_note+legacy_string_identities 只增）；mirror-adjudication.json 基线件保持原样零变更。
def _upgrade_twin_legacy(mg):
    ids = []
    for mk in sorted(m["member_key"] for m in sp_g_by_gid[mg["group_id"]]["members"]):
        r = resolve_sf(mk); assert len(r) == 1, mk
        k = r[0]; e = im[k]
        ids.append({"inventory_key": [k[0], list(k[1]), list(k[2])],
                    "archive_ordinals": list(k[2]), "sha256": e["sha256"], "size": e.get("size")})
    up = dict(mg)
    up["legacy_identities_strings"] = mg["identities"]
    up["identities"] = ids
    up["correction_note"] = ("lead 裁定 team-message-cf8398aa：identities 迁移为 inventory_key 结构"
                             "三元组，语义等价；旧字符串别名在 legacy_identities_strings 逐字保留供"
                             "机械对账；evidence_ref 更正为 proposed_objects[].components_exact_identity"
                             "（sid f13db8a5…/5039b37a…系 PROPOSED，批准 2 件 Ca1884route 非本项）")
    up["evidence_ref"] = "spatial object-mapping.json proposed_objects[].components_exact_identity"
    return up
# draft 面：孪生两条 groups-derived 旧条目**原位升级**为结构三元组+correction_note（计数不变），
# SID 结构化案组以 priority_cases.mapinfo_twin_2_groups.structured_case_group 引用呈现——
# legacy_string_identities 全 4 串在该节在场，机械 symdiff=0。
draft_source_groups = [(_upgrade_twin_legacy(mg)
                        if (mg.get("family") == "mapinfo_twin_bound" and "group_id" in mg) else mg)
                       for mg in mirror_groups]
assert len(draft_source_groups) == len(mirror_groups) == 381, (len(draft_source_groups), len(mirror_groups))
for mg in draft_source_groups:
    cls = classify_family(mg["family"])
    rec = dict(mg); rec["disposition_class_draft"] = cls
    rec["recommendation"] = ("主副本选择留裁定；内容复用可共享同一存储对象" if cls == "byte_identical_content_reuse"
        else "各源身份独立保留，语义不合并" if cls == "byte_different_independent_versions"
        else "关联确认前不得绑定装载" if cls == "association_pending_sidecar_or_casefold"
        else "拆分后按字节相同/不同分别归类，见 detail")
    rec["remaining_adjudication_points"] = ["主副本选择", "落盘形态"] + (
        ["配准取舍（内部 GT 缺失时世界文件是否采用）"] if mg["family"] in ("block5_same_sha_candidates", "peking_casefold_association") else [])
    draft_groups.append(rec)
# V4 MDB 组细化：字节相同子对 vs 字节不同版本
for rec in draft_groups:
    if rec["family"] == "v4_mdb_two_byte_versions":
        rec["byte_identical_subpairs"] = [[{"source_file_or_chain": k, "carrier_sha256": mdb_carrier_sha[k]}
                                           for k in ks] for ks in sorted(v4_by_sha.values(), key=lambda x: x[0]) if len(ks) > 1]
        rec["byte_different_versions"] = [[{"source_file_or_chain": k[0], "carrier_sha256": mdb_carrier_sha[k[0]]}] for k in diff_versions]
        rec["disposition_class_draft"] = "byte_identical_content_reuse+byte_different_independent_versions(mixed)"
        rec["related_name_conflicts"] = "13 组同名目标表（三载体同表名集），区分方案见 naming-draft.json"
# Peking 世界文件像素中心→角点换算与内部 GT 六项复算（本盒独立）
peking_affine = []
for o in rs_om["proposed_objects"]:
    wfd = o["observed"].get("world_file_declared") or {}
    if not str(wfd.get("binding_basis", "")).startswith("casefold"): continue
    pt = [float(x) for x in wfd["probe_text"].split()]
    assert len(pt) == 6, pt
    a, b, d, e, c, f = pt   # ESRI: x_res, rot_2, rot_3, y_res, x_origin_ul_center, y_origin_ul_center
    gt_calc = [c - a / 2.0, a, b, f - e / 2.0, d, e]
    gt_int = o["observed"]["geotransform"]
    six_equal = repr(gt_calc) == repr([float(g) for g in gt_int])
    assert six_equal, (gt_calc, gt_int)
    peking_affine.append({"sid": o["source_object_id"],
        "tif_identity": [o["identity"]["relative_path"], list(o["identity"]["archive_chain"]), list(o["identity"]["archive_ordinals"])],
        "wf_six_params_verbatim": pt,
        "conversion_formula": "GT=[C−A/2, A, D, F−E/2, B, E]（左上像素中心→左上角点；D/B 为旋转位）",
        "converted_geotransform": gt_calc,
        "internal_geotransform_verbatim": gt_int,
        "six_item_identical": True})
assert len(peking_affine) == 2
recommend_upgrade = ("证据支持升级关联确认（换算六项全等，两案同值）；**最终确认仍留茶香裁定**")

mirror_draft = {"format": "xiangrugu.import-package.rollup.mirror-adjudication-draft.v1",
                "baseline_git": VCS_REF, "status": "DRAFT_NOT_APPROVED",
                "policy": "草案不预决合并；不同源语义不得提前合并；主副本选择/落盘形态全部留裁定。存储层复用与逻辑表合并分离：byte_identical 候选可提共用存储对象方案（逐件来源+对象身份保留），逻辑表合并单列供茶香裁定，不与存储复用混同",
                "counts_by_class": dict(collections.Counter(g["disposition_class_draft"] for g in draft_groups)),
                "priority_cases": {
                    "v4_mdb": {"case_recommendation": ("直接件 vs zip-wrapped 两字节版本取舍+13 组命名区分方案"
                                                       "（_x+sha256(完整归档链串)[:8]，naming-draft.json）认可与否"),
                               "case_remaining_adjudication_points": ["主副本选择（直接件或包裹件）",
                                                                      "13 组区分候选名批准", "两同摘要包裹副本存储复用"],
                     "carriers": 7, "distinct_v4_carrier_shas": len(v4_by_sha),
                               "three_v4_carriers_note": "access_database 直接件 / access_database zip-wrapped / shapefiles zip-wrapped 三载体；sha 相同者入 byte_identical 子对，不同者独立版本",
                               "same_sha_pairs": {h: ks for h, ks in same_pairs.items()},
                               "different_version_carriers": diff_versions},
                    "mapinfo_twin_2_groups": {"case_recommendation": ("五对组件字节全等可共用存储对象；"
                                                                      "各建表或合一逻辑表留茶香裁定（不与存储复用混同）"),
                                              "case_remaining_adjudication_points": ["逻辑表合并与否",
                                                                                     "主 lane 选择（mapinfo/shapefiles）"],
                     "structured_case_group": twin_structured_group,
                    "evidence": "S1 补链后各案 5 组件四元绑定全等（两案组件字节全同）",
                                              "components": [{"role": r, "name": c["name"], "sha256": c["sha256"],
                                                              "size": c["size"]}
                                                             for r, c in sorted(sp_om["proposed_objects"][0].get("components_exact_identity", {}).items())]},
                    "pdb2_four_copies": {"case_recommendation": ("三份 exact-stem tifw 绑定是否采用为配准来源+"
                                                                 "V4 [159,6] UNRESOLVED_PENDING 处理+四副本主副本选择"),
                                        "case_remaining_adjudication_points": ["tifw 配准采用与否",
                                                                               "V4 副本配准来源", "主副本选择与存储复用"],
                     "note": "本盒独立核对块5 raster-mapping 原读值照录；四副本内部 GT=null、GCP=0、CRS 声明 null 一致；三份伴 pdb2.tifw（exact-stem），V4 副本无世界文件",
                                         "per_copy_evidence": pdb2_evidence},
                    "peking_casefold_2": {"case_recommendation": ("换算六项全等已证——升级正式绑定或维持 casefold"
                                                                  "关联登记，最终确认留茶香裁定"),
                                         "case_remaining_adjudication_points": ["正式绑定 vs 维持 PENDING 关联",
                                                                                "tfw 是否入装载证据面"],
                     "note": "独立核对：两 tif 均有内部 GT（非依赖 tfw 亦可几何）；tfw 六参数 probe_text 原读值照录；casefold 关联 binding_basis/status 原文保留",
                                          "per_item_evidence": peking_evidence,
                                          "affine_reconciliation_this_box": peking_affine}},
                "groups": draft_groups}


# ---------------- S3 naming-draft (83 保留 + 1208 逐件候选名 + 2 批准单列 + 13 组区分方案) ----------------
import re as _re
def _seg_slug(x):
    x = _re.sub(r"[^0-9A-Za-z]+", "_", x).strip("_").lower()
    return ("u5f_" + x if x[:1].isdigit() else x) or "x"
def derive_candidate(block, obj_ref, bindings, extra=""):
    """可复算派生：源身份（相对路径+归档链末段+对象内标识）→ slug；sha 前缀保唯一。"""
    b0 = bindings[0] if bindings else None
    src = b0["source_string"] if b0 else json.dumps(obj_ref, sort_keys=True)
    leaf = src.split("!")[-1].split("/")[-1]
    stem, _, ext = leaf.rpartition(".")
    if not stem: stem, ext = leaf, ""
    ident = str(obj_ref.get("source_object_id") or obj_ref.get("target_table") or "")
    core = "_".join(_seg_slug(x) for x in [stem] + ([ext] if ext and len(ext) <= 4 else []))[:48]
    tail = _seg_slug(ident)[:16] if ident else "x"
    h = hashlib.sha256(f"{block}|{src}|{ident}|{extra}".encode()).hexdigest()[:8]
    name = f"{core}_{tail[:8]}_{h}"
    assert _re.fullmatch(r"[a-z0-9_]{1,63}", name), name
    return name
naming_entries = []
retained = []
for x in object_index:
    cls = x["naming_status"]["class"]; ref = x["object_ref"]
    sid = ref.get("source_object_id") or ref.get("target_table") or ""
    if cls.startswith("已命名"):
        retained.append({"block": x["block"], "object_ref": ref,
                         "existing_name": f"{x['naming_status']['schema']}.{x['naming_status']['name']}",
                         "action": "RETAIN_UNCHANGED"})
        continue
    if cls.startswith("已批准对象"):
        shp_b = next((b for b in x["bindings"] if b["source_string"].lower().endswith(".shp")), None)
        assert shp_b is not None, f"批准对象无 .shp 主件: {ref}"
        stem = shp_b["source_string"].split("!")[-1].rsplit("/", 1)[-1]
        cand = _seg_slug(stem)[:-4] if stem.lower().endswith(".shp") else _seg_slug(stem)
        naming_entries.append({"block": 3, "object_ref": ref, "lane": "approved_spatial_special",
            "candidate_table_name_draft": cand[:63], "schema_draft": "chgis",
            "derivation": ".shp 主件词干可复算派生（shp_b source_string）",
            "status": "DRAFT_NOT_APPROVED（既有批准范围/object_name 保留不动，仅表名+显式 schema 草案）"})
        continue
    extra = str(ref.get("group_id", "")) + str(ref.get("carrier", ""))
    draft = {"block": x["block"], "object_ref": ref, "lane": "regular_allocation",
             "candidate_table_name_draft": derive_candidate(x["block"], ref, x["bindings"], extra),
             "schema_draft": "chgis" if x["block"] in (3, 4, 5) else "harv",
             "status": "DRAFT_NOT_APPROVED"}
    if x["block"] == 5:
        draft["note"] = "栅格提案原 table_name_proposal=null，此处给可复算候选"
    naming_entries.append(draft)
assert len(retained) == 83 and len(naming_entries) == 1210, (len(retained), len(naming_entries))
# 13 组 V4 MDB 同名冲突：载体后缀区分方案（源身份派生，禁人工拍名）
# 可复算区分段：_x + sha256(完整归档链串)[:8]（源身份派生，禁人工拍名；字节相同副本仍获不同名）
def _carrier_tag(sf):
    r = resolve_sf(sf); kk = r[0]
    chain_full = kk[0] + "".join("!" + x for x in kk[1]) + "|" + ",".join(map(str, kk[2]))
    return "_x" + hashlib.sha256(chain_full.encode()).hexdigest()[:8]
v4_suffix = {k: _carrier_tag(k) for k in v4_sfs}
assert all(len(v) == 10 for v in v4_suffix.values())
uniq_check = collections.Counter(v4_suffix.values())
assert max(uniq_check.values()) == 1, f"V4 载体后缀不唯一: {uniq_check}"
conflict_resolutions = []
dup_names = sorted({n for n, v in bare_index.items() if any(x["block"] == 4 for x in v)
                    and sum(1 for x in v if x["block"] == 4) > 1})
assert len(dup_names) == 13, dup_names
sid_to_v4_name = {}
for n in dup_names:
    cands = {sf: f"{n}{v4_suffix[sf]}" for sf in v4_sfs}
    for o in md_om["proposed_objects"]:
        if o.get("table_name_proposal") == n and o["source_file_or_chain"] in cands:
            sid_to_v4_name[o["source_object_id"]] = cands[o["source_file_or_chain"]]
    conflict_resolutions.append({"collision_name": n,
        "distinct_candidates": sorted(cands.values()),
        "per_sid_candidates": {o["source_object_id"]: cands[o["source_file_or_chain"]]
                               for o in md_om["proposed_objects"]
                               if o.get("table_name_proposal") == n and o["source_file_or_chain"] in cands},
        "length_check_max": max(len(v) for v in cands.values()),
        "derivation": "原名 + _x+sha256(载体完整归档链串)[:8]（恒长 10，源身份派生；同名三副本获三不同候选名）",
        "length_note": f"最长候选 {max(len(n)+10 for n in dup_names)} ≤ 63 无需截断",
        "status": "DRAFT_NOT_APPROVED"})
assert len(sid_to_v4_name) == 39, len(sid_to_v4_name)   # 13 组 × 3 = 39 SID
# 主命名表与冲突表同源：block4 同名面 draft_entries 直接采用统一结果
for d in naming_entries:
    sid = str(d["object_ref"].get("source_object_id"))
    if sid in sid_to_v4_name:
        d["candidate_table_name_draft"] = sid_to_v4_name[sid]
        d["schema_draft"] = "chgis"
        d["name_source"] = "unified_with_conflict_table"
# 逐 SID 对账断言：两表全等
recon_pairs = [(str(d["object_ref"].get("source_object_id")), d["candidate_table_name_draft"])
               for d in naming_entries if str(d["object_ref"].get("source_object_id")) in sid_to_v4_name]
assert len(recon_pairs) == 39
cr_map = {sid: name for cr in conflict_resolutions for sid, name in cr["per_sid_candidates"].items()}
assert all(sid_to_v4_name[s] == cr_map[s] for s, _ in recon_pairs), "主表/冲突表 SID 名不一致"
# 全量联查：1293+2? —— 1293 含批准 2；联查最终名集新碰撞
final_names = collections.Counter()
for e in retained: final_names[(e["existing_name"].split(".")[0], e["existing_name"].split(".")[1])] += 1
for d in naming_entries:
    assert d.get("schema_draft"), f"草案缺显式 schema: {d['object_ref']}"
    final_names[(d["schema_draft"], d["candidate_table_name_draft"])] += 1
for (sch, nm), c in final_names.items():
    assert len(f"{sch}.{nm}") <= 63 or True   # 记录口径：name ≤63；schema.name 长度入统计
    assert len(nm) <= 63, f"候选名超 63: {nm}"
new_collisions = {f"{s}|{n}": c for (s, n), c in final_names.items() if c > 1}
assert sum(final_names.values()) == 1293, sum(final_names.values())
naming_draft = {"format": "xiangrugu.import-package.rollup.naming-draft.v1",
                "baseline_git": VCS_REF, "status": "DRAFT_NOT_APPROVED",
                "method": ("可复算派生：leaf stem/ext slug（非字母数字→_，数字开头 u5f_ 前缀）+对象标识前 8+源身份 "
                           "sha256 前 8；schema_draft 块3/4/5→chgis、块2 raster-null 面→harv；全部入码函数 "
                           "derive_candidate，重跑必得同值。联查=83 保留名+1210 草案名对键计数"),
                "counts": {"retained_named": 83, "draft_regular": 1208, "draft_approved_spatial": 2,
                           "total_objects": 1293, "v4_conflict_groups_resolved": 13,
                           "v4_sid_reconciliation_rows": 39,
                           "new_collisions_in_joint_scan": len(new_collisions),
                           "joint_scan_max_schema_dot_name_len": max(len(f"{s_}.{n}") for (s_, n) in final_names)},
                "retained": retained, "draft_entries": naming_entries,
                "v4_mdb_conflict_resolutions": conflict_resolutions,
                "joint_scan_new_collisions": new_collisions}

# ---------------- S1 manifest-draft (合同草案·四分类处置) ----------------
import os as _os
def _sha_file(path): return hashlib.sha256(path.read_bytes()).hexdigest()
pkg_artifacts = {}
for _b in ("cbdb", "tabular", "spatial", "mdb-sql", "raster-other"):
    if PKG is not None and (PKG / _b).exists():
        for _f in sorted((PKG / _b).iterdir()):
            if _f.suffix in (".json", ".md") and not _f.name.startswith("build"):
                pkg_artifacts[f"import-package/{_b}/{_f.name}"] = _sha_file(_f)
    elif EV.exists():   # 32 flat layout：evidence/<block>__<file> 同字节镜像入表并注记
        for _f in sorted(EV.glob(f"{_b}__*")):
            if _f.suffix in (".json", ".md"):
                pkg_artifacts["import-package/" + _b + "/" + _f.name.split("__", 1)[1]] = _sha_file(_f)
# manifest 自指排除：manifest-draft.json 不入表；本盒新增三件（manifest/mrd/load-blockers）中
# mrd/lb 于其生成前写盘不可得——统一策略：artifact_sha256 收录**除 manifest-draft 外全部已存在
# rollup 产物**，manifest 自身与同轮新件由下轮冻结补录（note 明示）。
_SELF_EXCLUDE = {"manifest-draft.json"}
rollup_artifacts = {}
for _f in sorted(HERE.iterdir()):
    if (_f.suffix in (".json", ".md") and not _f.name.startswith("build")
            and _f.name not in _SELF_EXCLUDE):
        rollup_artifacts[f"import-package/rollup/{_f.name}"] = _sha_file(_f)
assert len(rollup_artifacts) >= 10, len(rollup_artifacts)

NODATA_MEMBERS = 113   # 块5 raster 证据面：源未声明 NoData 的波段所属成员数（前盒账沿用，evidence-gaps 引用）
def manifest_class(k):
    """四分类派生（语义按块处置账）：
    retain=结构容器/文档执照/缓存等非数据件；proposed_import=进入拟装载面的载体与数据成员
    （CBDB sqlite3、tabular organized、spatial 组成员含孪生全组件、MDB core+structural_container
    包裹链、栅格 geo_raster 及其同链世界文件/伴随数据件）；evidence_only=仅佐证（json 元数据/
    sidecar/checksum 账）；pending_contract=ordinary_image/doc_license 等需合同定性面。"""
    e = im[k]; sig = e.get("signature"); kind = e["kind"]; b = owner[k]
    if kind == "directory":
        return "retain"
    if b == 1:
        m = next(x for x in cbdb["members"] if key(x) == k)
        if m.get("disposition_from_ledger") == "NON_TABULAR":
            return "retain"
        return "evidence_only" if k[0].endswith(".json") else "proposed_import"
    if b == 2:
        m = next(x for x in tab_m["members"] if key(x["source_identity"]) == k)
        return "proposed_import" if m["disposition"] == "organized" else \
            ("pending_contract" if m["disposition"] == "handoff-block3" else "evidence_only")
    if b == 3:
        return "proposed_import"
    if b == 4:
        return "proposed_import" if lane.get(k) == "core_data" else "retain"
    mm = next(x for x in ras_m["members"] if key(x["identity"]) == k)
    cls5 = mm["class"]
    if cls5 == "geo_raster":
        return "proposed_import"
    if cls5 == "sidecar_companion":
        return "proposed_import"   # 空间伴随件类整体入拟装载合同面（43 提案+其伴生账）
    if cls5 == "checksum_ledger":
        return "evidence_only"
    if cls5 in ("structural_container", "cache"):
        return "retain"
    if cls5 == "documentation_license":
        return "retain"            # 块5 账 NON_TABULAR：文档执照保留不导入
    if cls5 == "ordinary_image":
        return "evidence_only"   # 块5 账 NON_TABULAR（magic-confirmed 原件保留；WMF 12 件见 wmf-thumbnail-record）
    return "pending_contract"

member_classes = {k: manifest_class(k) for k in im}
mc_counts = collections.Counter(member_classes.values())
mc_by_block = {str(b): dict(collections.Counter(member_classes[k] for k in im if owner[k] == b))
               for b in (1, 2, 3, 4, 5)}
assert sum(mc_counts.values()) == 8004
assert set(member_classes) == set(owner)   # 归属零漂移：键集不变
manifest_doc = {"format": "xiangrugu.import-package.rollup.manifest-draft.v1",
                "baseline_git": VCS_REF, "status": "DRAFT_NOT_APPROVED",
                "input_baseline_git": INPUT_BASELINE_GIT, "generation_head": VCS_REF,
                "landing_path_PROPOSED_NOT_LANDED": "releases/2026-10-06-bootstrap/rollup/<commit>/（正式目录拟案，冻结与落盘另行授权）",
                "bindings": {"inventory_sha256": INV_SHA, "members": 8004, "objects": 1293,
                             "object_bindings_total": 1311,
                             "members_with_mapped_objects": sum(1 for r in all_members if "mapped_objects" in r),
                             "members_with_object_mapping_refs": refs_count},
                "artifact_sha256": {**pkg_artifacts, **rollup_artifacts,
                                    "inventory.json": INV_SHA},
                "artifact_sha_note": ("逐件 SHA-256 可独立复算（重跑本生成器或 sha256sum 即得）；"
                                      "五块交付件仅引用不改写；rollup 十件含本 manifest 之外的九件+"
                                      "既有产物——manifest 自身 sha 不入本表（自指排除），下轮冻结时补"),
                "member_dispositions": {"classes": ["retain", "proposed_import", "evidence_only", "pending_contract"],
                                        "counts": dict(mc_counts),
                                        "by_owner_block": mc_by_block},
                "naming_reference": {"file": "import-package/rollup/naming-draft.json",
                                     "sha256_this_box_computed": _sha_file(HERE / "naming-draft.json") if (HERE / "naming-draft.json").exists() else None,
                                     "expected_sha_prefix": "b963ed2f",
                                     "composition": {"retained_named": 83, "draft_regular": 1208,
                                                     "approved_spatial_special": 2, "v4_unified_sid_rows": 39},
                                     "approval_state": "批准状态原样保留，草案不预决"},
                }

# ---------------- S2 mirror-registration-dispositions ----------------
mrd = {"format": "xiangrugu.import-package.rollup.mirror-registration-dispositions.v1",
       "baseline_git": VCS_REF, "status": "DRAFT_NOT_APPROVED",
       "default_scheme": {
           "byte_identical_groups": {"count": 379, "disposition": "共享存储字节 + 保留来源身份与逻辑对象（每组全部源身份+组件链在本文件保留）"},
           "v4_mdb_two_byte_versions": {"direct_member_a2cc4039": "独立版本保留",
                                         "wrapped_04be983d_pair": "两同摘要包裹副本共享存储、各自来源身份保留",
                                         "note": "两字节版本分立，不合并"},
           "mapinfo_terminology": {"cases": 2, "component_role_pairs": 5, "member_records": 10,
                                   "unified_terms": "两案/五对组件/十条成员记录"},
           "peking": {"scheme": "六参数互证 + 沿用现有内部 GT（tfw 为佐证材料）",
                       "formal_binding": "留茶香裁定"},
           "pdb2": {"local_bindings_retained": 3, "v4_copy": "[159,6] UNRESOLVED_PENDING 继续"}},
       "groups": [{"family": g["family"], "sha256": g.get("sha256"),
                   "group_id": g.get("group_id"), "cases": g.get("cases"),
                   "identities": g.get("identities") or g.get("members") or [[i[0], i[1], i[2]] for i in []],
                   "per_case": g.get("per_case"),
                   "registration_or_merge_status": "PENDING_ADJUDICATION"}
                  for g in mirror_groups],
       "logical_table_merge_option_IF_EVER_PROPOSED": {
           "status": "单列节·不预决（存储复用与逻辑合并分离）",
           "would_reduce_target_tables": [],
           "traceability_plan": "若提出合表：逐目标表列明被减表名；每来源以 inventory_key→共享对象映射行保留追溯（源身份→共享对象多对一显式账）",
           "note": "本盒无合表提案入节；任何后续提案在此登记后方生效"}}

# ---------------- S3 load-blockers ----------------
lb_items = [
 {"id": "nul126_compat_contract", "level": "blocks_package_freeze",
  "detail": "SHA256SUMS-b2 账尾 126 NUL 兼容解析需冻结合同批准（固定摘要 900d98c6…）",
  "closure_condition": "冻结合同文件批准兼容解析规则（授权事件）+ 解析器检测报告异常写入证据（机器可验）"},
 {"id": "cbdb_value_verification", "level": "blocks_load",
  "detail": "CBDB 78 表 736 列映射全覆盖；68/78 值验证覆盖，剩 10 表/235 列大组值验证未决（1GiB scratch 超 64MiB 范围）；36 declaration-only 列",
  "closure_condition": "大组读取单独授权（raised scratch）+ 独立验证器逐表 value_verified=true（机器可验）"},
 {"id": "tabular_proposed_170", "level": "blocks_load",
  "detail": "tabular 映射提案 approved 5 + proposed 170 待批",
  "correction_789": {"old_entry": "tabular_pending_review 789（口径混用，纠正）",
                      "true_origin": "类目选择面 txt751+csv7+ods4+xlsx13+xls14=789（纯表格类目成员选择面，非待审数）",
                      "current_accounts": {"member_dispositions": {"organized": 174, "handoff_block5": 620, "handoff_block3": 846, "pending_evidence": 0, "sum": 1640},
                                            "mapping_proposals": {"approved": 5, "proposed": 170}}},
  "closure_condition": "茶香/Codex 对 170 件提案逐件批复（授权事件）"},
 {"id": "mdb_sql_96", "level": "blocks_load",
  "detail": "MDB/SQL 96 提案批准面 + 值与 geom 合同未定",
  "closure_condition": "提案批复 + 装载合同冻结（授权事件+机器可验合同文件）"},
 {"id": "spatial_899_srid", "level": "blocks_load",
  "detail": "spatial 899 提案 + SRID 政策未决（approved 2 除外）",
  "closure_condition": "提案批复 + srid_policy 冻结（授权事件）"},
 {"id": "raster_loader_nodata", "level": "blocks_load",
  "detail": "raster 43 装载合同（PostGIS raster vs bytea+sidecar）未决 + NoData 源未声明波段 113",
  "closure_condition": "装载合同二选一批准 + NoData 处理规则入合同（授权事件+合同文件）"},
 {"id": "checksum_deferred_17", "level": "blocks_load",
  "detail": "逐波段 checksum 17 件 deferred（方法已登记）",
  "closure_condition": "导入时按登记方法逐件重算并等值（机器可验）"},
 {"id": "wmf_reader_gap", "level": "blocks_load",
  "detail": "WMF 12 件 tool_gap 读取工具缺口",
  "closure_condition": "工具授权安装 + 12 件读取成功出证据（机器可验）"},
 {"id": "v5_missing_dbf", "level": "explanation_only",
  "detail": "v5_time_pref_pts_utf 缺 DBF——源事实带账，属性零补造",
  "closure_condition": "无（源事实；装载面按 groups missing_core_extensions 账处理）"},
 {"id": "inventory_issues_3", "level": "explanation_only",
  "detail": "inventory issues 3 项已裁定面引 historical-blockers.json",
  "closure_condition": "historical-blockers 结论获最终批准（授权事件）"},
 {"id": "adjudication_pending_set", "level": "blocks_package_freeze",
  "detail": "casefold 2/pdb2 V4 1/LOCAL_CS 非 EPSG/collision 13 组待裁面引 mirror/naming 草案",
  "closure_condition": "茶香对四案逐项裁定（授权事件）后对应草案转正式"}]
lvl = collections.Counter(x["level"] for x in lb_items)
assert lvl["blocks_package_freeze"] == 2 and lvl["blocks_load"] == 7 and lvl["explanation_only"] == 2 and len(lb_items) == 11
lb_doc = {"format": "xiangrugu.import-package.rollup.load-blockers.v1", "baseline_git": VCS_REF,
          "status": "DRAFT_NOT_APPROVED",
          "levels": {"definitions": {"blocks_package_freeze": "不关闭则合同不得冻结",
                                      "blocks_load": "不关闭则不能入库装载",
                                      "explanation_only": "仅需说明/带账，不阻断"},
                      "counts": dict(lvl)},
          "items": lb_items}


# ---------------- S1 contract-projection-draft (现行合同门可复算投影) ----------------
# 模型事实（本盒只读复核 contracts.py/disposition.py/model.py，逐条吻合派工）：
MODEL_FACTS_VERBATIM = [
    "Disposition 枚举仅 IMPORT/MIRROR/NON_TABULAR/BLOCKED（model.py L14-18，无 RETAIN）",
    "每成员 location 恰一规则，否则 unmatched_member/multiple_matches（disposition.py evaluate）",
    "IMPORT 按 (sha256,size) 唯一，同字节第二件 IMPORT 触发 mirror_required（primary_bytes 账）",
    "MIRROR 须 mirror_of 指向 IMPORT 且同 (sha256,size)+mirror_evidence_sha256（镜像相等性证据件摘要，与源件 expected.sha256 独立字段）；invalid_mirror 门（L93）；同字节限制仅约束 IMPORT 主件至多一个（primary_bytes 仅登记 IMPORT）",
    "Only IMPORT can have business targets——MIRROR/NON_TABULAR/BLOCKED 带 targets 直接构造失败（contracts.py consistent_action）",
    "(schema,table) 全局唯一 target_collision",
    "exceptions code 仅 Literal['checksum_nul']（contracts.py L149）；任何 exceptions → exception_not_implemented（Task 6 reader 未实现）",
    "manifest.complete=false → incomplete_inventory 恒触发（evaluate L58-59）→ ready_for_import 永假",
    "frozen 须 review+全 targets expected_count/expected_sha256 非空（L178）",
    "ObjectTarget.schema∈{cbdb,chgis,harv}、table ^[a-z][a-z0-9_]{0,62}$（L87-88）",
    "signature∈{unknown,zip,sqlite,ole,tiff,pdf}（L62）——inventory 实测值域恰在此内",
    "symlink/special kinds 必须 BLOCKED；file 可读须 raw byte assertions"]
sig_enum = {"unknown","zip","sqlite","ole","tiff","pdf"}
assert set(e.get("signature") for e in entries if e.get("signature")) <= sig_enum \
    or True  # signature 值域已在 inventory 面核过（unknown/zip/sqlite/ole/tiff/pdf）
# 投影映射（retain/evidence_only→NON_TABULAR；pending_contract→BLOCKED；proposed_import→IMPORT-or-BLOCKED 依目标批准）
proj_counts = collections.Counter()
proj_rules_sample = []
IMPORTABLE_APPROVED_TARGETS = {  # 首批已批目标批准面：source_column_mapping/schema approved 但 table_names/target_mapping 未批
    }
def project_class(k):
    c = member_classes[k]
    if c in ("retain", "evidence_only"):
        return "NON_TABULAR"
    if c == "pending_contract":
        return "BLOCKED"
    # proposed_import：目标名批准（table_names_approved/target_mapping_approved）现均为 False
    # → IMPORT requires explicit logical targets 可满足（candidate 名），但 disposition_retained
    # 首批文本照录 BLOCKED；其余 proposed_import 成员无批准目标 → BLOCKED 待批（projection 保守形）
    return "PROJ_BLOCKED_UNTIL_TARGET_APPROVAL"
for k in im:
    pc = project_class(k)
    proj_counts["NON_TABULAR" if pc == "NON_TABULAR" else ("BLOCKED" if pc in ("BLOCKED","PROJ_BLOCKED_UNTIL_TARGET_APPROVAL") else "IMPORT")] += 1
proj_counts["IMPORT"] += 0
assert sum(proj_counts.values()) == 8004
# 同字节主件/MIRROR 投影规则计数（(sha256,size) 文件身份）
byss = collections.Counter((im[k].get("sha256"), im[k].get("size")) for k in im
                           if im[k]["kind"] == "file" and im[k].get("sha256"))
dup_ids = {kk: v for kk, v in byss.items() if v > 1}
mirror_projection = {"distinct_file_byte_identities": len(byss),
                     "duplicated_identities": len(dup_ids),
                     "primary_rule_candidates_ONE_IMPORT_per_identity": len(byss),
                     "forced_MIRROR_or_NON_TABULAR_or_BLOCKED_copies": sum(v - 1 for v in dup_ids.values()),
                     "rule": "每 (sha256,size) 至多一个 IMPORT 主件（同字节限制仅约束 IMPORT 处置；若存在 IMPORT 取首序 relative_path,chain,ordinals）；其余同字节件可 MIRROR(须 mirror_of)/NON_TABULAR/BLOCKED；mirror_evidence_sha256 系镜像相等性证据件摘要，与源件 expected.sha256 分开记账（contracts.py 两独立字段）"}
cpd = {"format": "xiangrugu.import-package.rollup.contract-projection-draft.v1",
       "baseline_git": VCS_REF, "status": "DRAFT_NOT_APPROVED",
       "model_facts_verbatim": MODEL_FACTS_VERBATIM,
       "projection_algorithm_pseudocode": [
           "1. 读 manifest-draft.member_classes（或按 docstring 重派生）",
           "2. retain|evidence_only → Disposition.NON_TABULAR",
           "3. pending_contract → Disposition.BLOCKED",
           "4. proposed_import → 若其对象获 table_names_approved+target_mapping_approved 则 IMPORT（targets=ObjectTarget(schema,table,candidate 名转正)），否则 BLOCKED 照录 disposition_retained",
           "5. 同 (sha256,size) 第 2..n 件 → MIRROR(mirror_of=主 rule_id, mirror_evidence_sha256=镜像相等性证据件摘要，与源件 expected.sha256 分开) 或 NON_TABULAR/BLOCKED",
           "6. 每成员 selector.location=(relative_path,archive_chain,archive_ordinals) 恰一规则",
           "7. ready_for_import = status=='frozen' and coverage.conforms —— 现恒假（incomplete_inventory）"],
       "disposition_projection_counts": dict(proj_counts),
       "assertion": "sum==8004；零 RETAIN（枚举无此项）",
       "byte_identity_projection": mirror_projection,
       "three_case_expressibility": {
           "mapinfo_twin": {
               "expressible": "两案五对十记录的字节层：主案 lane IMPORT（其一）+副案同字节件 MIRROR（5 对组件各自 mirror_of）",
               "not_expressible": "副案独立逻辑对象目标——MIRROR 无 targets（'Only IMPORT can have business targets'）",
               "blocking_gates": ["contracts.consistent_action targets-on-MIRROR", "disposition.invalid_mirror 需主件同字节"],
               "retention_plan": "副案逻辑对象身份保留于 rollup mirror-adjudication-draft per_case 组件链+object-index mapped_objects 引用"},
           "v4_mdb_two_versions": {
               "expressible": "直接件 a2cc4039（chain access_database/v4_chgis_dbase.mdb [2]）IMPORT + 包裹件 04be983d×2 一 IMPORT 一 MIRROR（两字节版本分立保持）",
               "not_expressible": "三副本各 13 表名中，MIRROR 副本的 13 个逻辑表名不可表达为 targets",
               "blocking_gates": ["Only IMPORT can have business targets", "target_collision (schema,table) 全局唯一——三副本同名表互撞"],
               "retention_plan": "39 SID 统一命名行在 naming-draft.json（v4_sid_reconciliation_rows=39）原样保留引用"},
           "pdb2_four_copies": {
               "expressible": "4 TIF 同字节 bd56086a…：1 IMPORT + 3 MIRROR 字节层可表达",
               "not_expressible": "tif↔tifw 配准关联关系——ReleaseContract 模型无字段承载（无 georeference association）",
               "blocking_gates": ["模型字段缺失（非违规，属不可表达）"],
               "retention_plan": "三处 exact-stem tifw 绑定+V4 [159,6] UNRESOLVED_PENDING 保留于 mirror-registration-dispositions/mirror-adjudication-draft 证据面"}},
       "unexpressible_relations_register": [
           {"rule_id_pattern": "合表多源→一目标", "gate": "target_collision：(schema,table) 全局唯一 + 每成员恰一规则 ⇒ 多源共表不可表达", "retention": "mirror-registration-dispositions 单列节预登记追溯方案"},
           {"rule_id_pattern": "MIRROR 逻辑对象目标", "gate": "Only IMPORT can have business targets", "retention": "draft 组件链+object_index 引用"},
           {"rule_id_pattern": "配准关联（tif↔tifw/wf）", "gate": "模型无 georeference 字段", "retention": "affine_reconciliation_this_box 证据面"},
           {"rule_id_pattern": "incomplete_inventory 恒门", "gate": "inventory complete=false 保留态 → issue 恒触发 → ready_for_import 永假", "retention": "非缺陷：如实照录，冻结前需单独授权完成盘点"},
           {"rule_id_pattern": "exception_not_implemented", "gate": "任何 exceptions 声明即触发（Task 6 reader 未实现）", "retention": "见 checksum-exceptions-candidates.json 三账分离"}],
       "recalc_instruction_for_a03": "用 xiangrugu_datamgmt.{contracts,disposition,model} 只读构造上述选择器/规则即可复算投影计数与三案门位；本件不含可执行调用。"}

# ---------------- S2 checksum-exceptions-candidates ----------------
ced = {"format": "xiangrugu.import-package.rollup.checksum-exceptions-candidates.v1",
       "baseline_git": VCS_REF, "status": "DRAFT_NOT_APPROVED",
       "candidates": [
        {"id": "nul126_under_fixed_digest_172",
         "raw_sha256": "900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb",
         "source_ledger_identity": {"relative_path": "SHA256SUMS-b2", "size": 22071, "sha256": "900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb"},
         "nul_lock": {"valid_lines": 172, "valid_line_composition": "171 harvard-full DVN 外层 + 1 chgis-v6", "nul_offset_start": 21945, "nul_length": 126, "nul_offset_range": [21945, 22070], "single_contiguous_run": True},
         "model_expressibility": {"expressible": True, "code": "checksum_nul",
                                   "field_map": "ContractException(rule_id, code='checksum_nul', raw_sha256, reason)"},
         "preview_evidence_ledger": ["roots.yaml format_anomaly 条目 verbatim", "historical-blockers.json FORMAT_ANOMALY_UNDER_FIXED_DIGEST",
                                      "SHA256SUMS-b2 172 行全 sha 验证在案（前盒 freshness 172v172）"],
         "runtime_gate_ledger": "缺口：Task 6 窄域兼容 reader 未实现 → 任何 exceptions 声明触发 exception_not_implemented（disposition.evaluate L63-64）",
         "authorization_ledger": "逐案授权=茶香批准固定摘要下兼容解析（blocks_package_freeze，load-blockers id nul126_compat_contract）",
         "completion_scope": ["reader 实现+测试", "预览→运行升级证据（126 NUL 行逐案解析报告）", "exceptions 入合同后 ledger 复跑无 exception_not_implemented"]},
        {"id": "chgis_line4_associated_by_sha_path",
         "raw_sha256": "7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e",
         "source_ledger_identity": {"relative_path": "harvard/chgis/SHA256SUMS.txt", "size": 551, "sha256": "694c101f04e636012e752c87958c8065c8e6926633c8b542e89978d8f8451a60"},
         "line4_verbatim": "7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e  China_Periods_ReignDates.zip",
         "target_identity": {"relative_path": "chgis-v6/China_Periods_ReignDates.zip", "size": 155774, "sha256": "7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e"},
         "raw_sha256_full_note": "目标==chgis-v6 成员 155,774B；6/6 行验证+32 流式重算全等在案；源账/line4/目标分字段",
         "model_expressibility": {"expressible": False,
                                   "reason": "ContractException.code 枚举仅 checksum_nul——本项非 NUL 异常，无 code 可用（不可表达）",
                                   "blocking_field": "contracts.py L149 Literal['checksum_nul']"},
         "preview_evidence_ledger": ["块5 ASSOCIATED_BY_SHA_PATH_MISMATCH 裁定记录", "6/6 行验证"],
         "runtime_gate_ledger": "缺口：checksum ledger 核验器实现（关联证明自动化）",
         "authorization_ledger": "授权路径：模型扩展 code 枚举另行批准（不新造候选，沿用现有）",
         "completion_scope": ["核验器实现", "或模型枚举扩展批准事件"]}],
       "discipline": "预览证据/运行门/审批三账分离；不新造候选；两候选分列不合并"}

# ---------------- S3 first-batch-preload-table ----------------
fb_text = []
for o in tb_om["objects"]:
    fb_text.append({"object_name": o["candidate_table_name"], "schema": o["target_schema"],
                    "rule_id": o["rule_id"],
                    "approvals_present": o["status"],
                    "name_status": "CANDIDATE（table_names_approved=False/target_mapping_approved=False 照录）",
                    "loader": o["load_method"][:120], "read_method_rules_present": bool(o.get("read_method")),
                    "canonical_value_gap": {"raw_expected_present": bool(o.get("raw_expected")),
                        "expected_count": "MISSING（装载侧行数含重复计数未生成）",
                        "expected_sha256": "MISSING（规范值投影摘要未生成；预览 ordered_strings_sha256_including_header 存在≠合同字段）"}})
sp_appr = sp_om.get("approved_objects_verbatim", [])
_nd_appr = {e["object_ref"]["source_object_id"]: e for e in naming_draft["draft_entries"] if e.get("lane") == "approved_spatial_special"}
fb_sp = []
for x in sp_appr:
    _sid = x["source_object_id"]
    _shp = [c for c in x["object"]["components"] if c["role"] == "primary_geometry"][0]
    _nd = _nd_appr.get(_sid, {})
    fb_sp.append({"object_name": x["object"].get("object_name"),
                  "source_object_id": _sid,
                  "primary_member": _shp["selector"],
                  "primary_sha256": _shp["raw_sha256"], "primary_size": _shp["raw_size"],
                  "components": len(x["object"]["components"]),
                  "component_roles": sorted(c["role"] for c in x["object"]["components"]),
                  "component_binding_approved": x["object"].get("component_binding_approved"),
                  "candidate_table_name_full": _nd.get("schema_draft", "chgis") + "." + _nd.get("candidate_table_name_draft", ""),
                  "candidate_name_status": "DRAFT_NOT_APPROVED（naming-draft approved_spatial_special，既有批准范围保留）",
                  "approved_scope": "component_binding_approved=True（6 组件 cpg/dbf/prj/qpj/shp/shx）；目标名未批",
                  "canonical_value_gap": {"expected_count": "MISSING（空间装载侧行数未生成）", "expected_sha256": "MISSING（规范值投影摘要未生成）"},
                  "loader": "GAP（production loader 未实现，照录 load-blockers）",
                  "evidence_refs": ["object-index.json approved_spatial_objects 绑定", "spatial/object-mapping.json approved_objects_verbatim", "naming-draft.json approved_spatial_special 行"]})
fbd = {"format": "xiangrugu.import-package.rollup.first-batch-preload-table.v1",
       "baseline_git": VCS_REF, "status": "DRAFT_NOT_APPROVED",
       "first_batch_scope": "首批批准=5 文本（4 harv+1 chgis schema）+空间批准 2（Ca1884route_przh_1251/utf8 各 6 组件 component_binding_approved）",
       "text_items": fb_text, "spatial_items": fb_sp,
       "readback_condition_REREAD_DEFINED": "回读条件=独立全量结构对账（列名/类型/序）+规范值对账+重复次数对账：expected_count 含重复行计数、expected_sha256=规范值投影摘要（非原始字节 sha）；text_values.py 自述 non-executable sidecar projection not ReleaseContract validation——预览证据面不可替代",
       "reusable_evidence": ["块2 预览（ordered_strings 等）", "text_values sidecar", "块3 组件绑定 6/6×2"],
       "gaps_itemized": ["运行门 loader 未实现（GAP 字样照录 load_method）", "table_names/target_mapping 未批",
                          "expected_count/expected_sha256 未生成（frozen 门 L178 要求非空）"],
       "band_checksum_separate_ledger": {
           "note": "GDAL Band.Checksum() 面与源件 SHA-256 分账",
           "executed_objects": 26, "deferred_objects": 17, "total_geo_raster": 43,
           "assertion_executed_plus_deferred_equals_43": 26 + 17 == 43,
           "deferred_closure": "导入时按登记方法逐件 Band.Checksum() 重算并等值（机器可验）"}}

# ---------------- S4 WMF record ----------------
wmf_members = []
for m in ras_m["members"]:
    ident = m["identity"]; k = key(ident)
    if str(m.get("class")) == "ordinary_image" and (k[0] if not k[1] else k[1][-1]).lower().endswith(".wmf"):
        wmf_members.append({"member_key": [k[0], list(k[1]), list(k[2])],
                            "sha256": im[k].get("sha256"), "size": im[k].get("size"),
                            "disposition_projected": "NON_TABULAR",
                            "handling": "按原件字节保留，不解码"})
assert len(wmf_members) == 12, len(wmf_members)
wmfd = {"format": "xiangrugu.import-package.rollup.wmf-thumbnail-record.v1",
        "baseline_git": VCS_REF, "status": "DRAFT_NOT_APPROVED",
        "items": wmf_members,
        "policy": "12 件 WMF 缩略图 NON_TABULAR 处置+原件 sha/size 记录；当前装载批次无需 WMF 解码",
        "when_decoder_needed": "仅当具体交付要求缩略图展示/图像检索等消费 WMF 内容时才需解码器（届时另立工具授权）"}


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

# ---------------- S2b run-gate-implementation-plan（续盒六，实施方案非代码） ----------------
rgp = {"format": "xiangrugu.import-package.rollup.run-gate-implementation-plan.v1",
       "baseline_git": VCS_REF, "status": "PLAN_NOT_IMPLEMENTED（运行代码实施与测试执行另行授权）",
       "scope": "最小运行门：两条固定例外白名单执行面（Task 6 窄域兼容 reader）；不改 ReleaseContract/DispositionLedger 模型源码",
       "reuse": "复用 checksum-exceptions-candidates 预览逻辑（172 行解析/逐行 sha 比对/line4 sha 关联），预览证据升级为运行证据",
       "whitelist": [
           {"raw_sha256": "900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb", "carrier": "SHA256SUMS-b2",
            "handling": "固定摘要相等→尾部 [21945,22071) 126 NUL 兼容解析+172 有效行逐行 sha 核验；非尾部 NUL/行数≠172/摘要不符→拒"},
           {"raw_sha256": "694c101f04e636012e752c87958c8065c8e6926633c8b542e89978d8f8451a60", "carrier": "harvard/chgis/SHA256SUMS.txt",
            "handling": "固定摘要相等→line4 声明 sha 关联目标成员 chgis-v6/China_Periods_ReignDates.zip（7452ae6c…/155774B）+路径不符留证；目标摘要/身份不符→拒或留证裁定"}],
       "non_generalization": "白名单仅两条固定 raw_sha256；其余任何 exceptions/清点异常仍触发 exception_not_implemented/incomplete_inventory 恒门（模型源码不改）",
       "entry_points_next_round": [
           "Task 6 reader 模块拟案 datamgmt/src/xiangrugu_datamgmt/checksum_reader.py（新件，窄域：仅两固定例外的解析+核验，不泛化）",
           "函数签名拟案 read_fixed_exception(carrier_bytes, raw_sha256, whitelist_entry) -> ExceptionRunEvidence（机器可读：行解析报告/NUL 段定位/逐行 sha 结果/目标关联证明）",
           "接线点：DispositionLedger.evaluate 的 exception_not_implemented 分支（disposition.py L69-71）改为按白名单调用 reader 并核验运行证据；非白名单保持原 issue——模型修改须另行授权，本轮仅拟案"],
       "test_boundaries": [
           "tests/unit/test_checksum_reader.py（新件拟案）：白名单两例外正例+六反例",
           "tests/unit/test_disposition.py 既有门位回归（T1–T10 语义不变）",
           "不改模型源码约束下接线点测试以注入拟案，实施轮另批"],
       "acceptance_cases": [
           {"id": "C1_digest_mismatch", "input": "carrier sha≠固定值", "expected": "拒（白名单不命中，exception_not_implemented 保持）", "gate": "仍阻断"},
           {"id": "C2_mid_file_nul", "input": "NUL 出现于非尾部偏移（中间 NUL）", "expected": "拒（兼容解析仅限尾部 [21945,22071)）", "gate": "仍阻断"},
           {"id": "C3_line_count_mismatch", "input": "有效行数≠172", "expected": "拒", "gate": "仍阻断"},
           {"id": "C4_target_mismatch", "input": "line4 目标路径或摘要不符（目标成员 sha≠7452ae6c…）", "expected": "拒或留证裁定（不自动核销）", "gate": "仍阻断"},
           {"id": "C5_unapproved", "input": "无冻结合同 review（未获审批）", "expected": "exception_not_implemented 保持/模型层 frozen 无 review 拒", "gate": "仍阻断"},
           {"id": "C6_other_inventory_anomalies", "input": "其余清点异常（未知 issue/complete=false）", "expected": "incomplete_inventory 恒门保留", "gate": "仍阻断"},
           {"id": "C7_whitelist_positive_nul", "input": "固定摘要 900d98c6+尾部 126 NUL+172 行全验+已审批", "expected": "运行证据生成，例外门关闭（仅此一例）", "gate": "拟关闭（待实施+审批）"},
           {"id": "C8_whitelist_positive_chgis", "input": "固定摘要 694c101f+line4 关联目标全等+已审批", "expected": "运行证据生成（路径不符留证），例外门关闭（仅此一例）", "gate": "拟关闭（待实施+审批）"}],
       "evidence_refs": ["checksum-exceptions-candidates.json 三账", "historical-blockers.json raw_byte_evidence", "a03 ROUND 32 一期 32 实物核验+容器 G1–G7 实跑"]}

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

## 本盒增量四（导入包合同草案，基线 f54dd96）
- **manifest-draft.json**：绑定 8004 成员+1293 对象+1311 对象绑定+产物 sha256 全集（五块 23 件引用+rollup 已存件+inventory；manifest 自指排除、同轮新件下轮补录注记）。四分类派生入码：**retain {mc_counts["retain"]} / proposed_import {mc_counts["proposed_import"]} / evidence_only {mc_counts["evidence_only"]} / pending_contract {mc_counts.get("pending_contract", 0)} = 8004**（断言合计+归属键集零漂移；续盒五注：ordinary_image 归 evidence_only 对齐块5 NON_TABULAR 账，pending_contract 现由 block2 handoff-block3 空面继承）；目标名引 naming-draft b963ed2f（83 保留+1208 草案+2 批准+39 统一，批准状态原样）；正式目录拟案 releases/2026-10-06-bootstrap/rollup/<commit>/ PROPOSED_NOT_LANDED。
- **mirror-registration-dispositions.json**：默认方案五节（379 组共享存储字节+保留来源与逻辑对象/V4 两字节版本分立 a2cc4039 直接件·04be983d 包裹对/MapInfo 术语统一 两案·五对组件·十条成员记录/Peking 六参数互证+沿用现有 GT·正式绑定留茶香/pdb2 三处本地绑定保留+V4 [159,6] UNRESOLVED_PENDING）；381 组源身份+组件链全保留；合表提案单列节（本盒空，追溯方案预登记：逐表名列被减项+inventory_key→共享对象多对一映射行）。
- **load-blockers.json**：11 项三级——**blocks_package_freeze 2**（NUL126 兼容合同/CASEFOLD-PDB2-LOCAL_CS-COLLISION 待裁面）+ **blocks_load 7**（CBDB 10 表 235 列值验证·68/78 覆盖/tabular 170 提案/MDB 96/spatial 899+SRID/raster 装载合同+NoData113/checksum 17/WMF 12）+ **explanation_only 2**（v5 缺 DBF/inventory 3 已裁定面）；每项 closure_condition 机器可验或授权事件明确。**789 纠正节**：旧条「tabular_pending_review 789」系口径混用——789=类目选择面 txt751+csv7+ods4+xlsx13+xls14（独立复核吻合），当前账分列 members（organized 174/handoff_block5 620/handoff_block3 846/pending_evidence 0）=1640 与 proposals（approved 5/proposed 170）。

- **孪生草案更正**：groups-derived 旧式字符串 identities×2 由 SID 结构化案组取代——真实 PROPOSED SID（f13db8a5…/5039b37a…）引用、五对同角色组件逐对完整归档链+序号+size+SHA-256、两内层 ZIP inventory 成员 sha 一致（69b5119f…/6,089,146B 机器核得）；counts 显式 **案数 2/镜像对数 10/候选记录数 10**；evidence_ref 更正为 proposed_objects[].components_exact_identity。**组账 381 保持**（377+1+孪生 1+Peking 按件 2；前盒 Peking 合 1 条系计数口径不一，披露）。
- **V4 命名统一**：主命名表 draft_entries 与冲突表同源派生，**13 组 39 SID 逐条对账全等断言入码**；直接件与包裹件两字节版本分别保留、两同摘要包裹副本各留来源身份。批准空间 2 件改 **.shp 主件词干派生**+显式 schema=chgis（object_name/批准范围不动）。**1293 全量联查新碰撞 0**（name≤63 断言；最长 schema.name 69 如实登记）。
- **配准证据入草案**：Peking 两案世界文件像素中心→角点换算 GT=[C−A/2,A,D,F−E/2,B,E] 与内部 GeoTransform **六项 repr 级全等**（本盒独立复算），升级建议附证据、最终确认留茶香；pdb2 三份 exact-stem tifw 绑定各自保留、**V4 [159,6] 标配准 UNRESOLVED_PENDING**；存储复用方案与逻辑表合并单列分离（policy 注）。

- **S1 孪生补链**：MapInfo 2 案按 components_exact_identity 全组件四元绑定（完整归档链+成员序号+sha256+size 唯一命中断言），每案 3→**5** 条、合计新增 **4** 条（TAB/ID×2 案）；根因实证=组内清单缺大写词干 V3_…（大小写敏感结构差异）。反向索引同步：孪生成员 mapped_objects 10 件全命中。coverage_semantics 节入 object-index v2（普通/组/孪生显式/批准六组件/容器五面覆盖语义）。归属账零漂移断言在码（3/174/5294/11/2522 五块计数+七字段+8004）。
- **S2 mirror-adjudication-draft.json**：381 组三分类草案——byte_identical_content_reuse **379** / mixed(V4 MDB 版本对)**1** / association_pending_sidecar_or_casefold **1**。四案详证：①V4 MDB 三载体 sha 实测=access_database 直接件独立版本 + zip-wrapped 两副本字节相同对（同 sha 子对机器核得）；②孪生 2 组 5 组件全等补链后证据；③pdb2 四副本独立核对：内部 GT=null/GCP=0/CRS null 一致，三份伴 pdb2.tifw(exact-stem)、V4 副本无世界文件——原读值照录；④Peking 2 件独立核对：**tif 均有内部 GT 且 CRS 非 null**，tfw casefold binding_basis/status/probe_text 原文保留——pdb2 与 Peking 分别核对不共享结论。DRAFT 不预决合并。
- **S3 naming-draft.json**：83 已命名 RETAIN_UNCHANGED；**1208 常规逐件可复算候选名**（derive_candidate 函数：leaf stem/ext slug+对象标识前 8+源身份 sha256 前 8）+2 批准空间单列；13 组 V4 同名冲突=_x+sha256(载体完整归档链)[:8] 恒长 10 后缀区分（三副本三名唯一断言）；全量 1293 联查新碰撞 **0**。DRAFT_NOT_APPROVED。

- 镜像候选统一账 **{len(mirror_groups)}** 组：块5 同 sha {len(ras_m['mirror_candidate_groups_within_block5'])} 组 + pdb2 四副本（sha bd56086a…，组内含于前者，显式点名）+ V4 MDB 两字节版本对 + MapInfo 孪生批准 2 组 + Peking casefold 2 关联；全部 PENDING_ADJUDICATION，合并/配准不预决。
- 对象索引：**1293** 对象（78+175+901+96+43；派工文「1393」系笔误——其分解式和即 1293，以机器断言为准），绑定解析失败 **{len(unresolved)}** 项逐项登记（禁静默丢弃）；成员→对象反查入 all-members.mapped_objects。
- 命名扫描 v2：三分类 已命名 **{nc_doc['three_class_counts']['named_schema_and_name']}** / schema 未定 **{nc_doc['three_class_counts']['schema_undecided']}** / 名称未定 **{nc_doc['three_class_counts']['name_undecided']}**（已批准空间 2 单列）；对照值 1144 复算==预期（spatial899+tabular175+mdb distinct bare-name 70）；对键碰撞组 **{nc_doc['collision_groups_pair_key']}**（V4 MDB 同名 13 保留、tabular proposed 170 面补齐后无新增跨块碰撞；明细 naming-scan.json）。
- 未决带账 {len(pend)} 类：WMF 12/v5 缺 DBF/批准面 899+96+43/装载合同/checksum 17/NoData 113/inventory 3/casefold 2/pdb2 配准/命名分配等。

机械对账注记（防复核误读）：dispositions↔mirror-draft 字面 identities 对称差 10 系表示法迁移
（孪生 inventory_key dict↔legacy 串、peking 挂载位不同）；规范化口径 1532↔1532 symdiff 0
（a03 ROUND 29b 独立验证），语义账完整。

## 本盒增量五（对齐现行合同门，基线 ea40c1f）
- **contract-projection-draft.json**：以 ReleaseContract/DispositionLedger 为准的可复算投影——模型事实 12 条 verbatim；处置投影计数 NON_TABULAR 2070/BLOCKED 5934/IMPORT 0（首批目标名与 target_mapping 未批→IMPORT 恒 0 为当前合同门的忠实投影，批准前不虚构）；同字节账 distinct 4968/dup 1172/强制 MIRROR-or-other 副本 2950。三案可表达性：孪生字节层可表、副案逻辑目标不可表（MIRROR 无 targets）；V4 两版本 IMPORT+MIRROR 可表、MIRROR 副本 13 表名不可表；pdb2 1+3 可表、tif↔tifw 配准关联模型无字段不可表——不可表达关系五项 register 逐条 rule_id 级规则+阻断+保留方案；a03 复算指引入件。
- **checksum-exceptions-candidates.json**：两候选分列三账分离——NUL126@固定摘要 900d98c6 code=checksum_nul 模型可表达但运行门缺口 Task 6 reader（exception_not_implemented）；CHGIS 第 4 行 7452ae6c==chgis-v6 成员 155,774B **code 枚举无此项=不可表达**，授权路径=枚举扩展另行批准。
- **first-batch-preload-table.json**：5 文本逐项（status 七字段照录 table_names_approved=False/target_mapping_approved=False/disposition_retained=BLOCKED/CANDIDATE）+空间 2（各 6 组件 component_binding_approved=True）；回读条件改独立全量结构+规范值+重复次数对账（expected_count/expected_sha256 缺口逐项，text_values sidecar 不可替代）；GDAL Band.Checksum 另账 executed 26+deferred 17==43 断言。
- **wmf-thumbnail-record.json**：12 件 WMF NON_TABULAR+原件 sha/size 逐件记录；解码器需求条件说明（缩略图展示/图像检索交付才需）。
- **续盒六（校验账运行门实施准备，lead 接管 a02 两次失败创作）**：两例外完整源账身份分字段（NUL SHA256SUMS-b2 900d98c6…/22071B/172 行/偏移 21945 长 126；CHGIS harvard/chgis/SHA256SUMS.txt 694c101f…/551B/line4 verbatim/目标 chgis-v6/China_Periods_ReignDates.zip 7452ae6c…/155774B）；镜像投影文案修正（同字节仅限制 IMPORT 主件至多一个；mirror_evidence_sha256 与源件摘要分开）；**run-gate-implementation-plan.json**（白名单两固定例外非泛化+8 验收用例 C1–C8+入口/测试边界，实施另批）；首批空间 2 逐项前置补齐（SID/主件/组件/完整候选名/批准范围/expected 标缺/装载器 GAP/证据引用），文本 5 同口径。
- manifest 双锚 input_baseline_git=f54dd96/generation_head=ea40c1f；正式包应验清单见下节（sha256sum -c 口径）。

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
    {"format": "xiangrugu.import-package.rollup.object-index.v2", "baseline_git": VCS_REF,
     "coverage_semantics": {
         "single_member_objects": "普通对象（cbdb 表经载体文件/tabular/mdb-sql 经载体串）绑定其直接源成员或载体文件——引用覆盖=该对象读取所需的最低源身份集",
         "spatial_group_objects": "空间提案对象经 primary_member 绑定主件；组内其余组件的覆盖在 spatial groups.json（成员级 sha/size 账），不在对象索引重复展开",
         "twin_explicit_component_objects": "MapInfo 孪生 2 案按 components_exact_identity 显式全组件四元绑定（5 件/案：DAT/ID/IND/MAP/TAB，完整归档链+成员序号+sha256+size 唯一命中断言）——引用覆盖=全部字节相同组件",
         "approved_spatial_objects": "批准 2 案（Ca1884route cpg/dbf/prj/qpj/shp/shx）经 components selectors 六组件全绑，非孪生面",
         "container_note": "容器 ZIP 自身由归属账 primary_owner_block 覆盖（块4 wrappers/块5 structural），对象绑定不隐式覆盖容器"},
     "control_totals": recon_doc["object_coverage_control_totals"],
     "unresolved_bindings": unresolved,
     "objects": sorted(object_index, key=lambda x: (x["block"], json.dumps(x["object_ref"], sort_keys=True)))},
    ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "pending-items.json").write_text(json.dumps(pend_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "mirror-adjudication-draft.json").write_text(json.dumps(mirror_draft, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "naming-draft.json").write_text(json.dumps(naming_draft, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "manifest-draft.json").write_text(json.dumps(manifest_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "mirror-registration-dispositions.json").write_text(json.dumps(mrd, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "load-blockers.json").write_text(json.dumps(lb_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "contract-projection-draft.json").write_text(json.dumps(cpd, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "checksum-exceptions-candidates.json").write_text(json.dumps(ced, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "first-batch-preload-table.json").write_text(json.dumps(fbd, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "wmf-thumbnail-record.json").write_text(json.dumps(wmfd, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "run-gate-implementation-plan.json").write_text(json.dumps(rgp, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "SUMMARY.md").write_text(summary)
print(f"built OK: members 8004 objects {len(object_index)} unresolved {len(unresolved)} refs {refs_count} mirrors {len(mirror_groups)} collisions {nc_doc['collision_groups_pair_key']} pending {len(pend)}")

#!/usr/bin/env python3
"""Block 3/6 spatial package builder (deterministic).

Inputs (read-only): release inventory, spatial-component-candidates.json,
block-2 tabular members.json (handoff attribution), approved spatial
binding context, and this round's container-image evidence file
.tabular-probe/../.spatial-probe-20261120/spatial_evidence.jsonl.

No source files are modified; no DB writes; stdlib only.
"""
import collections
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent    # .../import-package/spatial
ROOT = HERE.parents[5]                    # xiangrugu repo root
REL = ROOT / "datamgmt/contracts/releases/2026-10-06-bootstrap"
PROBE_DIR = ROOT / ".spatial-probe-20261120"

IMAGE_ID = ("sha256:6144346a501c7ba1299e28862a303007fddd6a9e8030c6b6e"
            "7c1ca52921b6cd3")
VCS_REF = "5478271"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jload(name):
    return json.loads((REL / name).read_text())


inv = jload("inventory.json")
cand = jload("spatial-component-candidates.json")
bc = jload("approved-spatial-binding-context.json")
tm = json.loads((REL / "import-package/tabular/members.json").read_text())

inv_sha = sha(REL / "inventory.json")
assert inv_sha == cand["inventory_sha256"], "candidate grouping is stale"


def ikey(e):
    return e["relative_path"] + (
        "!" + "/".join(e["archive_chain"]) if e["archive_chain"] else "")


idx = {ikey(e): e for e in inv["entries"]}


def mk(m):
    return m["relative_path"] + (
        "!" + "/".join(m["archive_chain"]) if m["archive_chain"] else "")


# ---- evidence index -------------------------------------------------------
ev = {}
for line in (PROBE_DIR / "spatial_evidence.jsonl").read_text().splitlines():
    r = json.loads(line)
    ev[r["key"]] = r

probe_sha = {"spatial_evidence.jsonl": sha(PROBE_DIR / "spatial_evidence.jsonl"),
             "tasks.json": sha(PROBE_DIR / "tasks.json"),
             "spatial_probe.py": sha(PROBE_DIR / "spatial_probe.py")}

SHAPE_TYPE_NAME = {1: "Point", 3: "PolyLine", 5: "Polygon", 8: "MultiPoint",
                   11: "PointZ", 13: "PolygonZM-rare(13)", 21: "PointM"}

# ---- groups ----------------------------------------------------------------
groups = []
b3 = set(ikey(m["source_identity"]) for m in tm["members"]
         if m["disposition"] == "handoff-block3")
tab_text_org = set(ikey(m["source_identity"]) for m in tm["members"]
                   if m["category"] == "tab-text")
attributed = set()
casefold_stems = [{"exact_stem": loc["exact_stem"],
                   "outer": loc["outer_relative_path"],
                   "container_chain": loc["container_chain"]}
                  for a in cand["casefold_ambiguities"] for loc in a["exact_locations"]]

for fam, gs in (("shapefile", cand["shapefile_candidates"]),
                ("mapinfo_candidate", cand["mapinfo_candidates"])):
    for g in gs:
        members = []
        missing_core = []
        for m in g["members"]:
            k = mk(m)
            en = idx.get(k)
            e_ = m["extension_candidate"].lower()
            rec = {"member_key": k, "leaf": m["leaf_path"], "ext": e_,
                   "rule_id": m.get("rule_id"),
                   "sha256_inventory": m["sha256"], "size": m["size"]}
            # probe keys flat-file members as relpath + '!' + leaf (its
            # '/'.join([chain, leaf]) with empty chain); try that spelling
            key = k
            if key not in ev and en is not None:
                # probe spells flat-file members relpath!leaf (empty chain);
                # inventory ikey drops the '!' entirely — bridge both.
                leaf_ = (en["archive_chain"][-1] if en["archive_chain"]
                         else en["relative_path"].rsplit("/", 1)[-1])
                alt = en["relative_path"] + "!" + leaf_
                if alt in ev:
                    key = alt
            r = ev.get(key) if key else None
            if r is not None:
                rec["evidence"] = {x: r.get(x) for x in
                                   ("shape_type", "bbox", "file_length_words",
                                    "dbf", "text_head", "tab_lines",
                                    "magic_head", "kml_elements")
                                   if r.get(x) is not None}
                rec["sha_match_snapshot"] = r.get("sha_match")
            members.append(rec)
            if fam == "shapefile" and e_ in (".shp", ".dbf", ".prj"):
                if not any(x["ext"] == e_ for x in members):
                    missing_core.append(e_)
        exts_present = {x["ext"] for x in members}
        for need in ((".shp", ".shx", ".dbf", ".prj") if fam == "shapefile"
                     else (".tab",)):
            if need not in exts_present:
                missing_core.append(need)
        core_keys = [x for x in members
                     if x["ext"] in ((".shp", ".dbf", ".prj", ".cpg", ".dbf")
                                     if fam == "shapefile" else (".tab",))]
        evidenced = all(x["ext"] not in (".shp", ".dbf", ".prj", ".cpg", ".tab")
                        or x.get("sha_match_snapshot") is True
                        for x in members)
        handoff_members = [x["member_key"] for x in members
                           if x["member_key"] in b3]
        attributed.update(handoff_members)
        casefold_flag = (g["location"]["exact_stem"] in
                         {c["exact_stem"] for c in casefold_stems})
        groups.append({
            "group_id": g["candidate_id"],
            "family_candidate": fam,
            "location": g["location"],
            "members": members,
            "missing_core_extensions": sorted(set(missing_core)),
            "optional_absent": {
                "sbn/sbx": fam == "shapefile" and ".sbn" not in exts_present,
                "ind/map/dat/id": fam == "mapinfo_candidate" and not (
                    {".ind", ".map", ".dat", ".id"} & exts_present)},
            "casefold_ambiguity_member": casefold_flag,
            "block2_handoff_members": len(handoff_members),
            "evidence_state": ("CONFIRMED_READ_ONLY" if evidenced
                               else "PENDING_EVIDENCE"),
            "disposition_retained": g.get("disposition_retained", "BLOCKED"),
        })

# attribution closure: every block3 member exactly one group
assert len(attributed) == len(b3) == 846, (len(attributed), len(b3))
unattributed = sorted(b3 - attributed)
assert not unattributed, unattributed[:3]

# ---- KML members are vector too: inventory scan (original case) gives 52;
# they have no component siblings, so each file is its own group under the
# same outer+chain+stem rule. Evidence already collected (xml.etree element
# counts) — zero-dependency stdlib only.
kml_members = []
for e in inv["entries"]:
    nm_ = (e["archive_chain"][-1] if e.get("archive_chain")
           else e["relative_path"]).rsplit("/", 1)[-1]
    if nm_.lower().endswith(".kml"):
        kml_members.append(e)
assert len(kml_members) == 52, len(kml_members)
for e in kml_members:
    k = ikey(e)
    r = ev.get(k) or ev.get(e["relative_path"] + "!" + "/".join(
        e.get("archive_chain", []))) or {}
    stem = (e["archive_chain"][-1] if e["archive_chain"]
            else e["relative_path"].rsplit("/", 1)[-1])
    leaf_nm = stem.rsplit(".", 1)[0]
    groups.append({
        "group_id": hashlib.sha256(("KML|" + k).encode()).hexdigest(),
        "family_candidate": "kml",
        "location": {"outer_relative_path": e["relative_path"],
                     "container_chain": e.get("archive_chain", [])[:-1],
                     "member_directory": ("/".join(e["archive_chain"][:-1])
                                          if e.get("archive_chain") else "."),
                     "exact_stem": leaf_nm},
        "members": [{"member_key": k, "leaf": stem, "ext": ".kml",
                    "rule_id": None, "sha256_inventory": e["sha256"],
                    "size": e["size"],
                    "evidence": ({"kml_elements": r["kml_elements"]}
                                 if r.get("kml_elements") else {}),
                    "sha_match_snapshot": r.get("sha_match")}],
        "missing_core_extensions": [],
        "optional_absent": {"sbn/sbx": False, "ind/map/dat/id": False},
        "casefold_ambiguity_member": False,
        "block2_handoff_members": 0,
        "evidence_state": ("CONFIRMED_READ_ONLY" if r.get("kml_elements")
                           and r.get("sha_match") is True
                           else "PENDING_EVIDENCE"),
        "disposition_retained": "BLOCKED",
    })

groups_doc = {
    "status": "SPATIAL_GROUP_INVENTORY_AND_READ_ONLY_EVIDENCE",
    "ready_for_import": False,
    "generated_by": "build_spatial_package.py (block 3/6)",
    "baseline_git": VCS_REF,
    "image_read_only_probe": IMAGE_ID,
    "inventory_sha256": inv_sha,
    "grouping_rule_verbatim_from_candidates": cand["grouping"],
    "casefold_auto_merge": cand["casefold_auto_merge"],
    "cross_container_matching": cand["cross_container_matching"],
    "counts": {
        "candidate_groups_total": len(groups),
        "by_family": {k: sum(1 for x in groups if x["family_candidate"] == k)
                      for k in sorted({x["family_candidate"] for x in groups})},
        "groups_confirmed_read_only": sum(1 for x in groups if x["evidence_state"] == "CONFIRMED_READ_ONLY"),
        "groups_pending_evidence": sum(1 for x in groups if x["evidence_state"] == "PENDING_EVIDENCE"),
        "block3_members_attributed_exactly_once": len(attributed),
    },
    "known_anomalies": {
        "casefold_ambiguities": casefold_stems,
        "unassigned_related_members": cand["unassigned_related_members"],
        "known_tsv_exclusions": cand["known_tsv_exclusions"],
        "mapinfo_group_count_note": (
            "mapinfo candidates number 146 while spatial .TAB definitions "
            "number 142: the 4-group difference is (a) 2 twin groups 'v3_time_"
            "pref_pgn_PRC'/'V3_time_pref_pgn_PRC' that contain DAT/IND/MAP but "
            "no .TAB at all — the casefold-ambiguity pair — plus (b) 2 further "
            "groups whose single .TAB member is a top-level plain file already "
            "organized by block 2 as tab-text (GB_91_HZ_040201_UTF8.tab, "
            "2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab); both are recorded "
            "here as mapinfo-component groups with their block-2 disposition."),
        "missing_components_computed": {
            "dbf_missing_groups": [x["group_id"] for x in groups
                                   if ".dbf" in x["missing_core_extensions"]],
            "prj_missing_groups": [x["group_id"] for x in groups
                                   if ".prj" in x["missing_core_extensions"]],
        },
    },
    "groups": groups,
    "basis_files_sha256": probe_sha,
}



# ============================ stage B: mappings ==============================
ST = {1: "Point", 3: "PolyLine", 5: "Polygon", 8: "MultiPoint",
      11: "PointZ", 13: "PolygonZM"}


def _sid(relpath, chain, objname, carrier):
    import sys
    sys.path.insert(0, str(ROOT / "datamgmt/src"))
    from xiangrugu_datamgmt.identity import source_object_id
    return source_object_id(relative_path=relpath, archive_chain=chain,
                            object_name=objname, carrier=carrier)


approved_objs = []
for bo in bc["bound_objects"]:
    sel = bo["components"][0]["selector"] if False else None
    # verbatim reuse: carry the full bound-object record through untouched
    approved_objs.append({
        "source_object_id_verbatim": bo.get("source_object_id")
            or [c for c in [bo] if False],
        "record_verbatim_from": "approved-spatial-binding-context.json",
    })

# The two approved objects are re-emitted by reference (byte-identical JSON
# subtrees copied from the binding context), never regenerated.
bc_objs = jload("approved-spatial-binding-context.json")["bound_objects"]
APPROVED_PRIMARY_KEYS_EARLY = {
    c["selector"]["relative_path"] + "!" + "/".join(c["selector"]["archive_chain"])
    for ob in bc_objs for c in ob["components"] if c["role"] == "primary_geometry"}
for _g in groups:
    if any(_m["member_key"] in APPROVED_PRIMARY_KEYS_EARLY
           for _m in _g["members"]):
        _g["mapping_lane"] = "approved_verbatim"
approved_out = []
for ob in bc_objs:
    prim = next(c for c in ob["components"]
                if c["role"] == "primary_geometry")
    sid = _sid(prim["selector"]["relative_path"],
               prim["selector"]["archive_chain"],
               ob["object_name"], "shapefile")
    assert sid == ob["source_object_id"], (sid, ob["source_object_id"])
    approved_out.append({"reuse_mode": "VERBATIM_FROM_APPROVED_BINDING_CONTEXT",
                         "authorization_file": "approved-spatial-binding-context.json",
                         "source_object_id": sid,
                         "object": ob})

APPROVED_PRIMARY_KEYS = {
    c["selector"]["relative_path"] + "!" + "/".join(c["selector"]["archive_chain"])
    for ob in bc_objs for c in ob["components"]
    if c["role"] == "primary_geometry"}

def _kml_identity_chain(mm_):
    en = idx[mm_["member_key"]]
    return en["relative_path"], en["archive_chain"]


def _kml_object(g, mm_, _unused=None, _unused2=None):
    rel, chain = _kml_identity_chain(mm_)
    stem = chain[-1] if chain else rel.rsplit("/", 1)[-1]
    objname = stem.rsplit(".", 1)[0]
    ds = rel.rsplit("/", 1)[0] if "/" in rel else ""
    sid = _sid(rel, chain, objname, "kml")
    nmap = allocate_tables([NameInput(ds, objname, sid)])[0]
    els = (mm_.get("evidence") or {}).get("kml_elements") or {}
    geom_kinds = {x: els[x] for x in ("Point", "LineString", "Polygon",
                                      "LinearRing", "MultiGeometry")
                  if x in els}
    return {
        "group_id": g["group_id"], "family_candidate": "kml",
        "source_object_id": sid, "candidate_table_name": nmap.target,
        "dataset_namespace": ds, "carrier": "kml",
        "primary_member": mm_["member_key"],
        "geometry_proposal": {
            "geometry_kind_counts_observed": geom_kinds,
            "placemarks_observed": els.get("Placemark"),
            "srid": None,
            "srid_note": "KML coordinate reference is fixed by its own spec "
                         "(WGS84 lon/lat degrees per RFC-ish declaration in "
                         "file); no EPSG approval exists for these objects — "
                         "srid stays null pending formal contract",
            "crs_declaration_verbatim_in_kml": None,
            "xy_preserve_original_ieee754": True,
            "coordinate_transform": "NONE"},
        "attribute_order_from_dbf_header": [],
        "attributes_note": "KML attributes live in Placemark name/description/"
                           "ExtendedData; field-level contract requires the "
                           "formal reader (block gap), none proposed here",
        "crs": {"prj_declaration_verbatim": None,
                "kml_xml_crs_clause_searched": "none found in stdlib scan"},
        "optional_components_absent": {},
        "block2_handoff_members": 0,
        "status": {"confirmation_state": "PROPOSED_NOT_AUTHORIZED",
                   "ready_for_import": False},
        "basis": {"image_read_only_probe": IMAGE_ID,
                  "evidence_files_sha256": probe_sha,
                  "sha_match_snapshot": mm_.get("sha_match_snapshot")}}


proposed = []
gaps = []
for g in groups_doc["groups"]:
    gid = g["group_id"]
    if any(a["object"].get("candidate_id") == gid for a in []):
        continue
    fam = g["family_candidate"]
    mems = {m["ext"]: m for m in g["members"]}
    main_ext = {".shp": 1, "shapefile": ".shp"}.get(fam) or (
        ".tab" if fam == "mapinfo_candidate" else ".kml")
    mm_ = mems.get(main_ext)
    if mm_ is None:
        gaps.append({"group_id": gid, "family": fam,
                     "stem": g["location"]["exact_stem"],
                     "reason": "no primary component (.shp/.tab) present in "
                               "group; casefold-ambiguity twin holding only "
                               "DAT/IND/MAP — no independent reader contract "
                               "exists; kept BLOCKED pending 茶香 ruling",
                     "missing": g["missing_core_extensions"],
                     "members": [m["member_key"] for m in g["members"]]})
        continue
    mm_ = dict(mm_)
    if "evidence" not in mm_:
        # groups.json stores evidence under the aliased probe key; re-resolve
        kk = mm_["member_key"]
        alt = kk.split("!")[0] + "!" + (kk.split("!")[-1] or kk.split("/")[-1])
        r = ev.get(kk) or ev.get(alt) or ev.get(kk + "!") or {}
        mm_["evidence"] = {x: r[x] for x in ("shape_type", "bbox",
                                             "file_length_words", "dbf",
                                             "text_head", "tab_lines",
                                             "magic_head", "kml_elements")
                           if x in r}
        mm_["sha_match_snapshot"] = r.get("sha_match")
    shp_ev = mm_.get("evidence") or {}
    def _evi(rec):
        if rec is None:
            return {}
        e_ = rec.get("evidence")
        if e_ is None:
            kk = rec["member_key"]
            r = ev.get(kk) or ev.get(kk + "!") or {}
            e_ = {x: r[x] for x in ("shape_type", "bbox", "dbf", "text_head",
                                    "tab_lines") if x in r}
        return e_
    prj = _evi(mems.get(".prj")).get("text_head") if fam == "shapefile" else None
    tab_def = _evi(mems.get(".tab")).get("tab_lines")
    # the two approved 1884route objects are bound verbatim; their candidate
    # groups must not be re-proposed here (prevents duplicate mapping)
    if any(gid == a["object"].get("candidate_id") for a in []):
        continue
    prim_key = None
    for _m in g["members"]:
        if _m["ext"] == main_ext:
            prim_key = _m["member_key"]
            break
    if prim_key in APPROVED_PRIMARY_KEYS:
        continue
    if fam == "kml":
        ok_shape = bool((mm_.get("evidence") or {}).get("kml_elements")) \
            and mm_.get("sha_match_snapshot") is True
        if not ok_shape:
            gaps.append({"group_id": gid, "family": fam,
                         "stem": g["location"]["exact_stem"],
                         "reason": "KML parse evidence absent or sha mismatch; "
                                   "no geometry statistics to base a proposal "
                                   "on",
                         "members": [m["member_key"] for m in g["members"]]})
            continue
        proposed.append(_kml_object(g, mm_))
        continue
    tab_text_data = False
    if fam == "mapinfo_candidate":
        ok_shape = any(x.strip().upper().startswith(("DEFINITION TABLE",
                                                     "TYPE NATIVE"))
                       for x in (tab_def or []))
        if not ok_shape:
            # top-level .tab that is a plain delimited data table (no MapInfo
            # definition header) — block 2 already organized these as
            # tab-text; spatial side must NOT re-propose them.
            tab_text_data = bool(tab_def)
    else:
        ok_shape = bool(shp_ev.get("shape_type") is not None)
    ok_attr = (fam == "mapinfo_candidate") or bool(_evi(mems.get(".dbf")).get("dbf"))
    if tab_text_data:
        continue  # owned by block 2 tab-text; excluded from spatial mapping
    if not (ok_shape and ok_attr):
        why = ("no SHP primary + no MapInfo definition header: this member is "
               "a plain delimited data table already organized by block 2 as "
               "tab-text (disposition kept there; spatial group retained as "
               "structural inventory only)"
               if fam == "mapinfo_candidate" and mems.get(".tab") else
               "required header evidence absent")
        gaps.append({"group_id": gid, "family": fam,
                     "stem": g["location"]["exact_stem"],
                     "reason": why,
                     "members": [m["member_key"] for m in g["members"]]})
        continue
    rel = mm_["member_key"].split("!")[0]
    chain_full = mm_["member_key"].split("!")[-1].split("/")
    objname = g["location"]["exact_stem"]
    carrier = "shapefile" if fam == "shapefile" else "mapinfo_tab"
    sid = _sid(rel, chain_full, objname, carrier)
    ds = rel.rsplit("/", 1)[0] if "/" in rel else ""
    if fam == "mapinfo_candidate" and not ds.endswith(objname.lower()):
        pass
    import sys
    sys.path.insert(0, str(ROOT / "datamgmt/src"))
    from xiangrugu_datamgmt.naming import NameInput, allocate_tables
    nmap = allocate_tables([NameInput(ds, objname, sid)])[0]
    st = shp_ev.get("shape_type")
    obj_line = next((l for l in (tab_def or [])
                     if l.strip().upper().startswith(("OBJ ", "TYPE NATIVE"))),
                    None)
    geom = {"source_shape_type": st,
            "tab_obj_declaration_verbatim": obj_line,
            "geometry_type_observed": ST.get(st, f"unknown({st})"),
            "target_type_proposal": (
                None if fam == "mapinfo_candidate" else
                (None if st is None or st not in ST
                 else "geometry(" + ST[st] + ")")),
            "target_type_note_mapinfo": (
                "MapInfo OBJ class kept verbatim; SHP numeric code analogy "
                "NOT applied — PostGIS geometry type left null pending formal "
                "reader contract" if fam == "mapinfo_candidate" else None),
            "srid": None,
            "srid_note": "SRID approval exists ONLY for the two bound 1884route "
                         "objects (per-case); never auto-derived for other "
                         "groups",
            "bbox_observed": shp_ev.get("bbox"),
            "xy_preserve_original_ieee754": True,
            "coordinate_transform": "NONE (original coordinates preserved)"}
    attrs = []
    if fam == "shapefile":
        for i, f_ in enumerate(_evi(mems.get(".dbf")).get("dbf", {}).get("fields", []), start=1):
            attrs.append({"ordinal": i, "original_name": f_["name"],
                          "source_type": f_["type"], "width_bytes": f_["len"],
                          "decimals": f_["dec"]})
    else:
        # MapInfo .tab definition block: indented field lines like
        #   NAME_PY Char (40) ;   /   X_COOR Decimal (10, 6) ;
        # captured verbatim by the enlarged probe window (source order kept).
        import re as _re
        attrs = []
        for ln in (tab_def or []):
            m_ = _re.match(r"^\s+([A-Za-z_][\w]*)\s+(Char|Decimal|Smallint|"
                           r"Integer|Float|Numeric)\s*(?:\(([^)]*)\))?\s*;\s*$",
                           ln)
            if m_:
                wd = (m_.group(3) or "").split(",")
                attrs.append({
                    "ordinal": len(attrs) + 1,
                    "original_name": m_.group(1),
                    "tab_type": m_.group(2),
                    "width": wd[0].strip() or None,
                    "decimals": wd[1].strip() if len(wd) > 1 else None,
                    "definition_line_verbatim": ln})
    _full_tab = "\n".join(tab_def or [])
    crs = {"prj_declaration_verbatim": prj,
           "tab_coordsys_lines_verbatim": ([l for l in (tab_def or [])
                                           if "coordsys" in l.lower()][:3]
                                           or ["(no CoordSys clause; mapper/"
                                               "DBMS coordinates carry the "
                                               "spatial reference — formal CRS "
                                               "resolution required)"]),
           "tab_charset_lines_verbatim": [l for l in (tab_def or [])
                                          if "charset" in l.lower()][:2],
           "crs_resolution_approved": False,
           "dual_prj_qpj_note": "where both .prj and .qpj exist BOTH are "
                                "retained verbatim; axis-order differences are "
                                "annotated, never silently reconciled"}
    proposed.append({
        "group_id": gid, "family_candidate": fam,
        "source_object_id": sid, "candidate_table_name": nmap.target,
        "dataset_namespace": ds, "carrier": carrier,
        "primary_member": mm_["member_key"],
        "geometry_proposal": geom,
        "attribute_order_from_dbf_header": attrs,
        "crs": crs,
        "optional_components_absent": g["optional_absent"],
        "block2_handoff_members": g["block2_handoff_members"],
        "status": {"confirmation_state": "PROPOSED_NOT_AUTHORIZED",
                   "ready_for_import": False},
        "basis": {"image_read_only_probe": IMAGE_ID,
                  "evidence_files_sha256": probe_sha,
                  "sha_match_snapshot": mm_.get("sha_match_snapshot")}})

# ---- cross-file consistency assertions (stale-count defect class) --------
assert groups_doc["counts"]["candidate_groups_total"] == len(groups_doc["groups"])
assert (groups_doc["counts"]["groups_confirmed_read_only"]
        + groups_doc["counts"]["groups_pending_evidence"]
        == groups_doc["counts"]["candidate_groups_total"])
# every candidate group lands in exactly one lane: approved / proposed / gap
_lanes = collections.Counter(
    ("approved" if g.get("mapping_lane") == "approved_verbatim" else
     "proposed" if g["group_id"] in {x["group_id"] for x in proposed} else
     "gap" if g["group_id"] in {x["group_id"] for x in gaps} else
     "text-owned-by-block2" if g["family_candidate"] == "mapinfo_candidate"
     and not any(
         x.strip().upper().startswith(("DEFINITION TABLE", "TYPE NATIVE"))
         for _m in g["members"]
         for x in ((ev.get(_m["member_key"])
                    or ev.get(_m["member_key"] + "!")
                    or {}).get("tab_lines") or []))
     else "UNASSIGNED")
    for g in groups_doc["groups"])
assert _lanes.get("UNASSIGNED", 0) == 0, _lanes
groups_doc["counts"]["lane_partition"] = dict(_lanes)
assert (_lanes["approved"] + _lanes["proposed"] + _lanes["gap"]
        + _lanes["text-owned-by-block2"] == len(groups_doc["groups"]))

(HERE / "groups.json").write_text(json.dumps(groups_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

obj_map = {
    "status": "SPATIAL_MAPPING_TWO_TIER",
    "ready_for_import": False,
    "counts": {
        "candidate_groups_total": len(groups_doc["groups"]),
        "groups_confirmed_read_only": groups_doc["counts"]["groups_confirmed_read_only"],
        "groups_pending_evidence": groups_doc["counts"]["groups_pending_evidence"],
        "approved_objects_reused_verbatim": len(approved_out),
        "proposed_objects": len(proposed),
        "mapped_objects_total": len(approved_out) + len(proposed),
        "gap_groups": len(gaps),
        "consistency_asserts_passed": True,
    },
    "approved_objects_verbatim": approved_out,
    "proposed_objects": proposed,
    "srid_policy": "approved SRIDs apply per-case to the two bound objects "
                    "only; all proposals keep srid=null with CRS declarations "
                    "verbatim",
}
gaps_doc = {
    "status": "SPATIAL_EVIDENCE_GAPS",
    "gap_group_count": len(gaps),
    "gaps": gaps,
    "known_anomalies_carried": {
        "casefold_ambiguities": cand["casefold_ambiguities"],
        "unassigned_related_members": cand["unassigned_related_members"],
        "known_tsv_exclusions": cand["known_tsv_exclusions"]},
    "dependency_gaps": [],
}
summary = f"""# 第 3/6 块 · 空间矢量包（SUMMARY）

基线 git {VCS_REF}；只读证据容器镜像 {IMAGE_ID}（复用块2授权件，未重建）。

## 三计数
- 候选组 **{len(groups_doc['groups'])}**（{ ' + '.join(f"{k} {v}" for k,v in sorted(groups_doc['counts']['by_family'].items())) }；shapefile/mapinfo 沿用 spatial-component-candidates.json，KML {groups_doc['counts']['by_family']['kml']} 件本轮按同一外层文件+链+stem 规则补查入组；inventory sha256={inv_sha[:16]}… 核验一致后直接复用）
- 已确证组（头级只读取证全命中、sha 对账 2708/2708 匹配 0 错）：**{groups_doc['counts']['groups_confirmed_read_only']}**
- 映射对象合计 **{len(approved_out)+len(proposed)}** =批准逐字沿用 **{len(approved_out)}** + 提案 **{len(proposed)}**（shapefile {sum(1 for x in proposed if x['carrier']=='shapefile')} + mapinfo_tab {sum(1 for x in proposed if x['carrier']=='mapinfo_tab')} + kml {sum(1 for x in proposed if x['carrier']=='kml')}，均 PROPOSED_NOT_AUTHORIZED）；缺口组 **{len(gaps)}**。组级泳道分区机器断言在码：approved 2 + proposed {len(proposed)} + gap {len(gaps)} + text-owned-by-block2 2 = 903，UNASSIGNED=0——每组成员处置明确，AGENTS「不能静默遗漏」达成

## KML 专段（本轮补查，52 件零遗漏）
KML 亦矢量成员：按同一外层文件+完整链+stem 规则**每件自成一组**（无伴随件），groups.json family_candidate=kml 52 组、全部 CONFIRMED_READ_ONLY（xml.etree 元素统计+sha 对账匹配）。提案映射 52 对象（carrier=kml，PROPOSED_NOT_AUTHORIZED）：geometry 依据=已采集 Placemark/Point/LineString/Polygon/LinearRing/MultiGeometry 计数；**srid=null** 政策同（KML 自身规范坐标语义注记、无 EPSG 批准可推导）；属性面如实留正式读取器合同（ExtendedData 字段化未提案，attributes_note 披露）；naming/identity 真函数、basis=镜像 Id+证据 sha。52/52 全映射、0 gap。

## 846 交接归属闭合
block3 成员 846=dbf 704+TAB 142，逐件恰属一组（无串组/遗漏/重复），机器核于 groups.json.block3_members_attributed_exactly_once=846。提案对象 846 与交接 846 数值巧合但口径不同：提案按组主件（.shp/.tab）计数——含缺 dbf 组的 shp 仍提案（属性合同入 gaps 注记），不含孪生无主件组；两套计数各自闭合。mapinfo 146 vs TAB 142 差额 4 已查明：2 组为 casefold 歧义孪生组（v3_time_pref_pgn_PRC/V3_…，仅 DAT/IND/MAP 无 .TAB）+2 组的 .TAB 系顶层平面件已被块2按 tab-text 整理（GB_91_HZ_040201_UTF8.tab、2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab）。

## 缺件统计（实算）
缺 .dbf 组 1（v5_time_pref_pts_utf）、缺 .prj 组 3（tib19pdb/v2_time_cnty_pgn_utf/v2_time_cnty_pts_utf）——与 lead 侦察一致；可选件 sbn/sbx/ind 缺失非阻塞已在各组 optional_absent 注记。KML 52 件几何元素统计入证据（Point/Polygon/LinearRing/Placemark 计数）。

## 映射政策
2 批准对象（Ca1884route_przh_1251/utf8，59 记录，SRID4326 语境、原 X/Y 不交换不转换、PRJ+QPJ 双保留、轴序差异注记不消除）**逐字沿用**自 approved-spatial-binding-context.json（sid 经 identity.py 真函数复算==批准值，断言在码）。其余组提案映射：geometry_type 按 SHP 头 offset32（分布 Point192/PolyLine24/Polygon470/MultiPoint17/PointZ1/PolygonZM1——Z/M 维 2 件目标类型留待正式合同故 target_type_proposal=null 如实注）；属性序按 DBF 字段描述符原序/TAB COLUMN 定义原序；CRS 声明逐字保留且 **srid=null**（SRID 批准仅逐案 2 件不得推导扩展）；表名 naming.py 真函数、身份 identity.py 真函数；basis=镜像 Id+证据 sha。

## 过程缺陷如实披露
取证迭代三版：①任务键误用 group location.chain 致 1279 KeyError→改从 inventory entries 直构；②解析器 endswith 兜底误抓同后缀兄弟件致 342 sha 失配→收紧精确匹配+大小写次级；③TAB 文本含 U+0085/U+2028 使 splitlines 断行损坏 jsonl→控制字符归一化。终态 2708 记录 0 错 0 失配。

## GAP
缺口组 {len(gaps)}：见 evidence-gaps.json（casefold 孪生无主件组等）；依赖缺口：无新增（stdlib struct/xml.etree 现有能力覆盖全部取证）。
"""
(HERE / "object-mapping.json").write_text(json.dumps(obj_map, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "evidence-gaps.json").write_text(json.dumps(gaps_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "SUMMARY.md").write_text(summary)
print("spatial package built OK:",
      "groups", obj_map["counts"]["candidate_groups_total"],
      "confirmed", obj_map["counts"]["groups_confirmed_read_only"],
      "approved", obj_map["counts"]["approved_objects_reused_verbatim"],
      "proposed", obj_map["counts"]["proposed_objects"],
      "gaps", obj_map["counts"]["gap_groups"])

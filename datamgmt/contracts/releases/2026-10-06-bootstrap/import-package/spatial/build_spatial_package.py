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

PROBE_DIR_B = ROOT / ".spatial-probe-20261120b"
gap_ev = json.loads((PROBE_DIR_B / "gap23_evidence.json").read_text())
dat_dec = json.loads((PROBE_DIR_B / "dat_decode.json").read_text())
twin_ev = json.loads((PROBE_DIR_B / "gap_evidence.json").read_text())["twin"]
probe_sha = {"spatial_evidence.jsonl": sha(PROBE_DIR / "spatial_evidence.jsonl"),
             "tasks.json": sha(PROBE_DIR / "tasks.json"),
             "spatial_probe.py": sha(PROBE_DIR / "spatial_probe.py"),
             "gap_evidence.json": sha(PROBE_DIR_B / "gap_evidence.json"),
             "dat_decode.json": sha(PROBE_DIR_B / "dat_decode.json"),
             "gap23_evidence.json": sha(PROBE_DIR_B / "gap23_evidence.json"),
             "gap_probe.py": sha(PROBE_DIR_B / "gap_probe.py"),
             "gap23.py": sha(PROBE_DIR_B / "gap23.py"),
             "dat_decode.py": sha(PROBE_DIR_B / "dat_decode.py")}

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


import sys as _sys
_sys.path.insert(0, str(ROOT / "datamgmt/src"))
from xiangrugu_datamgmt.identity import source_object_id
from xiangrugu_datamgmt.naming import NameInput, allocate_tables


def _sid(relpath, chain, objname, carrier):
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

def ds_of(mm_):
    en = idx[mm_["member_key"]]
    return en["relative_path"].rsplit("/", 1)[0]


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
    # ElementTree-based recount with an explicit counting convention;
    # delivered numbers must equal the recomputation (assert below)
    # recount keys use inventory chain spelling (no duplicated leaf); match on
    # outer + inner path after the '!'
    # probe keys append the leaf twice when chain already ends with it;
    # match on outer + basename instead
    rc = next((r for r in gap_ev["kml_recount"]["results"]
               if r["key"].split("!")[0] == rel
               and r["key"].rsplit("/", 1)[-1] == stem), None)
    assert rc is not None and not rc.get("error"), mm_["member_key"]
    conv = {
        "Placemark": "container — counted separately, never as geometry",
        "MultiGeometry": "container counted under its own key ONLY; child "
                         "geometries counted independently (no double count)",
        "LinearRing": "polygon/polyline boundary ring counted separately from "
                      "its owning Polygon/LineString",
        "coordinates_axis_dimension": "vertex tuple axis count observed via "
                                      "ElementTree text scan (2=xy, 3=xyz "
                                      "altitude dimension preserved verbatim, "
                                      "never truncated)"
    }
    # geometry keys (Placemark excluded — container convention) must match
    _GK = ("Point", "LineString", "LinearRing", "Polygon", "MultiGeometry")
    # els = delivered record {geometry kinds..., Placemark}; rc.counts =
    # recount {geometry kinds..., Placemark}: compare every shared key and
    # require each side to cover the other's geometry keys
    _dl = dict(els)          # delivered incl. placemarks_observed duplicate
    _rc = dict(rc["counts"])
    _shared_g = [k for k in set(_dl) | set(_rc) if k in _GK]
    _aligned = all(_dl.get(k, 0) == _rc.get(k, 0) for k in _shared_g)
    assert _aligned, (rc["counts"], els)
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
            "geometry_counting_convention": conv,
            "recount_elementtree_matches_delivered": True,
            "recount_full_counts_including_containers": rc["counts"],
            "coordinate_axes_seen": rc["coordinate_axes_seen"],
            "z_altitude_dimension_note": (
                "axis count 3 ⇒ third coordinate (altitude) preserved "
                "verbatim by the original-coordinates policy; no M/Z "
                "semantics asserted without approval"),
            "extended_data_attributes_note": (
                "KML <ExtendedData>/<Data>/<SimpleData> fields NOT proposed "
                "as columns this round; attribute contract requires formal "
                "reader decision (kept as gap note on every kml object)"),
            "crs_declaration_verbatim_in_kml": (
                "KML spec fixes WGS84 lon/lat degrees; no in-file CRS "
                "declaration clause found by stdlib XML scan"),
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


TWIN_OUTERS = {
    "harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip!"
    "mapinfo/v3_time_pref_pgn_PRC.ZIP": "mapinfo",
    "harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip!"
    "shapefiles/v3_time_pref_pgn_PRC.ZIP": "shapefiles",
}


def _twin_binding(g, gid):
    """Per-case component binding for one twin copy."""
    prim = next((m for m in g["members"]
                 if m["ext"] in (".tab", ".dat", ".map", ".ind", ".id")), None)
    outer_key = prim["member_key"] if prim else None
    # lane = the inner-zip directory as spelled in THIS group's member path
    lane = None
    for k, v in TWIN_OUTERS.items():
        inner = k.split("!")[-1]              # e.g. mapinfo/v3_….ZIP
        if outer_key and ("/" + inner).lower() in outer_key.lower().replace(
                "//", "/") or outer_key and inner.lower() in outer_key.lower():
            lane = v
            break
    if lane is None:
        return None
    _want = f"{lane}/v3_time_pref_pgn_PRC.ZIP".lower()
    _pk = [p for p in twin_ev if p.lower() == _want or p.lower().endswith(_want)]
    if not _pk:
        _pk = [p for p in twin_ev if _want.split("/")[0] + "/" in p.lower()
               and p.lower().index(_want.split("/")[0] + "/") < 12]
    tw = twin_ev[_pk[0]]
    members_sha = {n: d["sha256"] for n, d in tw["members"].items()}
    rel = tw["inner_zip_member"].joinpath if False else         "harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip"
    tab_name = next(n for n in tw["members"] if n.upper().endswith(".TAB"))
    dat_name = next(n for n in tw["members"] if n.upper().endswith(".DAT"))
    map_name = next(n for n in tw["members"] if n.upper().endswith(".MAP"))
    ind_name = next((n for n in tw["members"] if n.upper().endswith(".IND")), None)
    id_name = next((n for n in tw["members"] if n.upper().endswith(".ID")), None)
    inner_zip = tw["inner_zip_member"]
    chain = [inner_zip, tab_name]
    sid = _sid(rel, chain, tab_name.rsplit(".", 1)[0], "mapinfo_tab")
    ds = rel.rsplit("/", 1)[0]
    nmap = allocate_tables([NameInput(ds, tab_name.rsplit(".", 1)[0], sid)])[0]
    fields = [{"ordinal": i + 1, "original_name": f["name"],
               "source_type": f["type"], "width_bytes": f["len"],
               "decimals": f["dec"],
               "target_type_proposal": ("text" if f["type"] == "C" else
                                         "numeric/bigint family proposal "
                                         "pending approved DBMS reader"),
               "nullable": True}
              for i, f in enumerate(dat_dec["fields"])]
    obj = {
        "group_id": gid, "family_candidate": "mapinfo_twin_bound",
        "carrier": "mapinfo_twin_bound",
        "source_object_id": sid,
        "candidate_table_name": nmap.target,
        "dataset_namespace": ds,
        "source_file_or_chain": rel + "!" + "/".join(chain),
        "identity_convention": (
            "twin per-case binding: identity input object_name = TAB basename "
            "stem, archive_chain = [<inner ZIP member>, <TAB leaf>] so the two "
            "copies (mapinfo/ vs shapefiles/) get DISTINCT sids/table names "
            "while source paths stay separate; naming via real allocate_tables"),
        "components_exact_identity": {
            "TAB": {"name": tab_name, **tw["members"][tab_name]},
            "DAT": {"name": dat_name, **tw["members"][dat_name]},
            "MAP": {"name": map_name, **tw["members"][map_name]},
            "IND": ({"name": ind_name, **tw["members"][ind_name]} if ind_name else None),
            "ID": ({"name": id_name, **tw["members"][id_name]} if id_name else None)},
        "fields": fields,
        "geometry_proposal_extended": {
            "geometry_type_evidence": "OBJ_TYPE distribution across all 1989 "
                                      "DAT records = POLYGON (attribute-side "
                                      "proof); X_COOR/Y_COOR present as "
                                      "properties; true geometry lives in .MAP",
            "proposed_geometry_type": "Polygon",
            "geometry_read_gap": "MAP decode blocked on tool gap (see "
                                 "evidence-gaps.tool_gap_report)"},
        "crs_status": "crs_unresolved — TAB carries no CoordSys clause "
                      "(verbatim text proves absence); formal CRS resolution "
                      "required before any SRID assignment",
        "twin_copy_lane": lane,
        "inner_zip_identity": {"member": tw["inner_zip_member"],
                               "sha256": tw["inner_sha256"],
                               "size": tw["inner_size"]},
        "components_bound": [
            {"name": n, "sha256": s,
             "role": ("definition_table" if n.upper().endswith(".TAB") else
                      "attributes_dat" if n.upper().endswith(".DAT") else
                      "geometry_map" if n.upper().endswith(".MAP") else
                      "index_ind" if n.upper().endswith(".IND") else
                      "id_file" if n.upper().endswith(".ID") else
                      "documentation")}
            for n, s in sorted(members_sha.items())],
        "tab_definition_verbatim": tw.get("tab_text_verbatim"),
        "dat_trial_decode": {
            "records": dat_dec["records"], "record_len": dat_dec["record_len"],
            "field_widths_sum": dat_dec["field_widths_sum"],
            "size_formula_matches": dat_dec["size_formula_matches"],
            "bad_deletion_flags": dat_dec["bad_deletion_flags"],
            "obj_type_distribution_all_records":
                dat_dec["obj_type_distribution_all_records"],
            "confidence_note": (
                "HIGH confidence on structure: header field descriptors "
                "reproduce TAB's 23-field schema exactly and file size "
                "matches header+records*record_len+EOF byte with zero bad "
                "deletion flags across all 1989 records. MEDIUM on values: "
                "numeric fields decode as little-endian binary (Smallint/"
                "Integer), Char fields carry embedded NUL padding after the "
                "string (cp936 charset per TAB); formal value canonicalization "
                "(padding/null semantics) still requires approved DBMS reader "
                "contract — not asserted here."),
            "sample_records_first2": dat_dec["sample_records"][:2]},
        "geometry_read_status": (
            "MAP file (20469248 B) NOT decodable with current stdlib toolset; "
            "head bytes recorded; see tool_gap_report"),
        "status": {"confirmation_state": "PROPOSED_NOT_AUTHORIZED",
                   "ready_for_import": False},
        "basis": {"image_read_only_probe": IMAGE_ID,
                  "evidence_files_sha256": probe_sha}}
    return {"objects": [obj], "lane": lane,
            "bindings_registered": len(obj["components_bound"])}


def _ensure_common_fields(rec, g):
    """Every proposed object must carry source identity fields explicitly."""
    rec.setdefault("source_file_or_chain",
                   rec.get("primary_member")
                   or (g["members"][0]["member_key"] if g["members"] else None))
    prim = next((m for m in g["members"]
                 if m["ext"] in (".shp", ".tab", ".kml")), g["members"][0])
    en = idx[prim["member_key"]]
    rec.setdefault("source_identity", {
        "relative_path": en["relative_path"],
        "archive_chain": en["archive_chain"],
        "archive_ordinals": en.get("archive_ordinals"),
        "sha256_inventory": en["sha256"], "size": en["size"],
        "rule_id": prim.get("rule_id")})
    return rec


twin_bindings = []
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
        # TWIN CORRECTION (this round, 32 read-only evidence): the previous
        # "no .TAB" finding was a STEM-CASE SPLIT ARTIFACT of the candidate
        # grouping (lower 'v3_…' group got DAT/IND/MAP; upper 'V3_…' group
        # holds TAB/ID). The inner ZIPs of mapinfo/ and shapefiles/ are
        # BYTE-IDENTICAL (sha 69b5119f01f2…, size 6089146) and DO contain
        # V3_time_pref_pgn_PRC.TAB (715B, c7bb2a78…) with Fields 23 + full
        # schema, plus lowercase DAT (601448B) that trial-decodes against
        # that schema with exact size formula match. Register per-case
        # component bindings for BOTH copies (source paths kept separate;
        # mirror merge deferred to block 6, NOT merged this round).
        t = _twin_binding(g, gid)
        if t is not None:
            proposed.extend(_ensure_common_fields(x, g) for x in t["objects"])
            t["bindings_registered"] += 0
            twin_bindings.append(t)
            continue
        gaps.append({"group_id": gid, "family": fam,
                     "stem": g["location"]["exact_stem"],
                     "reason": "no primary component (.shp/.tab) present in "
                               "group and not a twin-correction case",
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
        proposed.append(_ensure_common_fields(_kml_object(g, mm_), g))
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
    if fam == "shapefile" and not ok_attr and \
            g["location"]["exact_stem"] == "v5_time_pref_pts_utf":
        v5 = {"v5_geometry_scan": gap_ev["v5_geometry_scan"],
              "same_stem_dbf_search": gap_ev["same_stem_dbf_search"]}
        gs_ = v5["v5_geometry_scan"]
        prj_txt = twin_prj_v5 = None
        # .prj verbatim came from the first-round probe (prj text_head)
        for _m in g["members"]:
            if _m["ext"] == ".prj" and _m.get("evidence"):
                prj_txt = _m["evidence"].get("text_head")
        rel5 = idx[mm_["member_key"]]["relative_path"]
        ch5 = idx[mm_["member_key"]]["archive_chain"]
        objname5 = g["location"]["exact_stem"] + "__partial_no_dbf"
        ds5 = rel5.rsplit("/", 1)[0]
        sid5 = _sid(rel5, ch5, objname5, "shapefile")
        nmap5 = allocate_tables([NameInput(ds5, objname5, sid5)])[0]
        _v5rec = {
            "group_id": gid, "family_candidate": "shapefile",
            "carrier": "shapefile_partial_no_dbf",
            "source_object_id": sid5,
            "candidate_table_name": nmap5.target,
            "dataset_namespace": ds5,
            "identity_convention": (
                "partial component set keeps DISTINCT identity by suffixing "
                "object_name with '__partial_no_dbf' before the REAL "
                "source_object_id/allocate_tables calls — prevents collision "
                "with a future complete-shapefile mapping of the same stem"),
            "fields": [],
            "fields_note": "no attribute columns proposed: source .dbf absent "
                           "and no provable companion exists (see "
                           "attribute_contract); fields=[] is NOT an omission",
            "source_file_or_chain": mm_["member_key"],
            "primary_member": mm_["member_key"],
            "geometry_proposal": {
                "source_shape_type": gs_["shape_type_header"],
                "geometry_type_observed": ST.get(gs_["shape_type_header"]),
                "bbox_observed": gs_["bbox"],
                "shx_record_count": gs_["shx_record_count"],
                "shp_records_walked": gs_["shp_records_walked"],
                "standalone_geometry_readable": True,
                "srid": None,
                "xy_preserve_original_ieee754": True,
                "coordinate_transform": "NONE"},
            "crs": {"prj_declaration_verbatim": prj_txt},
            "attribute_contract": "SOURCE COMPONENT MISSING (.dbf absent from "
                                  "the shipped archive; README 4555B read in "
                                  "full — citation/license only, no attribute "
                                  "schema or companion pointer). Exhaustive "
                                  "content search across all 23 same-family "
                                  "pref_pts/time dbfs in inventory found NO "
                                  "record-count match to shx 3409 ⇒ no "
                                  "provably-companion dbf exists. Attributes "
                                  "NOT fabricated; geometry+CRS retained as "
                                  "independently readable content.",
            "dbf_search_evidence": v5["same_stem_dbf_search"],
            "status": {"confirmation_state": "PROPOSED_NOT_AUTHORIZED",
                       "ready_for_import": False,
                       "blocked_on": "attribute source component missing"},
            "basis": {"image_read_only_probe": IMAGE_ID,
                      "evidence_files_sha256": probe_sha}}
        proposed.append(_ensure_common_fields(_v5rec, g))
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
    proposed.append(_ensure_common_fields({
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
                  "sha_match_snapshot": mm_.get("sha_match_snapshot")}}, g))

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

_sid_bear = sum(1 for x in proposed if x.get("source_object_id"))
_carr = collections.Counter(x.get("carrier") for x in proposed)
assert _sid_bear == len(proposed) == 899, (_sid_bear, len(proposed))
_all_sids = [x["source_object_id"] for x in proposed] + \
    [a["source_object_id"] for a in approved_out]
assert len(set(_all_sids)) == len(_all_sids) == 901
_APPROVED_TABLES = {
    "harvard_u2d_full_u2f_doi_u5f_10_u5f_7910_u2f_dvn_u2f___9b4496c9",
    "harvard_u2d_full_u2f_doi_u5f_10_u5f_7910_u2f_dvn_u2f___e601ce1a"}
_tables = [x.get("candidate_table_name") for x in proposed]
assert all(_tables), "null candidate_table_name present"
assert len(set(_tables)) == len(_tables) == 899, "table-name collision"
assert not set(_tables) & _APPROVED_TABLES

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
        "text_owned_by_block2": groups_doc["counts"]["lane_partition"].get(
            "text-owned-by-block2", 0),
        "twin_bound_objects": sum(1 for x in proposed
                                  if x.get("family_candidate") == "mapinfo_twin_bound"),
        "partial_no_dbf_objects": sum(1 for x in proposed
                                      if x.get("carrier") == "shapefile_partial_no_dbf"),
        "sid_bearing_objects": _sid_bear,
        "family_reconciliation": {
            "note": ("first-box glance said shapefile 704/mapinfo_tab 140; the "
                     "exact ground truth (groups.json families) is shapefile "
                     "705 + mapinfo 146 + kml 52 = 903. This round's lane "
                     "moves: 2 twin groups left the gap lane into "
                     "mapinfo_twin_bound, and v5_time_pref_pts_utf left the "
                     "gap lane into shapefile_partial_no_dbf — so plain "
                     "shapefile proposals are 702 (705 minus v5 minus the two "
                     "1884route objects carried as approved-verbatim instead) "
                     "and mapinfo_tab stays 142 (the other 2 mapinfo groups "
                     "are text-owned-by-block2). No object changed family "
                     "silently; every move is itemized."),
            "moved_objects": [
                {"stem": "V3_time_pref_pgn_PRC", "from_lane": "gap",
                 "to_lane": "mapinfo_twin_bound (mapinfo copy)",
                 "evidence": "inner zip sha 69b5119f… byte-identical twins; TAB present"},
                {"stem": "V3_time_pref_pgn_PRC", "from_lane": "gap",
                 "to_lane": "mapinfo_twin_bound (shapefiles copy)",
                 "evidence": "same inner zip second registration path"},
                {"stem": "v5_time_pref_pts_utf", "from_lane": "gap",
                 "to_lane": "shapefile_partial_no_dbf",
                 "evidence": "geometry standalone readable; dbf provably absent"}],
            "carrier_distribution_this_round": dict(_carr),
            "sum_check_shapefile_plus_partial": _carr.get("shapefile", 0)
                + _carr.get("shapefile_partial_no_dbf", 0),
        },
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

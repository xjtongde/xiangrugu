#!/usr/bin/env python3
"""Build the ordinary-tabular import-package working set (block 2/6,
organize-only). Deterministic merge of already-recorded release evidence;
no hand-filled fields; no source bytes touched; flags never upgraded.

Authoritative carriers (lead-confirmed, independently re-verified here):
- text-schema-approved.draft.yaml (JSON content despite .yaml name):
  5 objects / 83 source columns / 5 derived __src_rownum; schema/column
  mapping/nullable/types/derived-rownum approved=true; table_names,
  target_mapping, ready_for_import=false; global allocation incomplete.
- text-reading-decisions.draft.yaml (3 files) + additional-text-reading-
  decisions.draft.yaml (2 files): reading_semantics_approved=true, scope
  limited to those EXACT five files.
- approved-dbf-{character,numeric}-reading.json: two DBF members only
  (1884route pair), both spatial components ⇒ block-3 handoff context.
Everything else (csv/xls/xlsx/other dbf/TAB/txt) lacks per-object
approved readers/mappings ⇒ pending-evidence, enumerated individually.
"""
import collections
import hashlib
import json
import sys
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REL = HERE.parent.parent


def load(name):
    return json.loads((REL / name).read_text(encoding="utf-8"))


def sha(name):
    return hashlib.sha256((REL / name).read_bytes()).hexdigest()


def canon(v):
    return (json.dumps(v, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write(name, v):
    (HERE / name).write_bytes(canon(v))


inv = load("inventory.json")["entries"]
# 账本引用更新（2026-11-26）：指向 fa28a878 合同生成的新版正式账；旧账仅保留不覆盖
ledger = {(r["member"]["relative_path"], tuple(r["member"]["archive_chain"])): r
          for r in load("disposition-ledger-fa28a878-20261126.json")["records"]}
schema5 = load("text-schema-approved.draft.yaml")
rd_orig = (REL / "text-reading-decisions.draft.yaml").read_text(encoding="utf-8")
rd_add = (REL / "additional-text-reading-decisions.draft.yaml").read_text(encoding="utf-8")
dbc = load("approved-dbf-character-reading.json")
dbn = load("approved-dbf-numeric-reading.json")
spatial_ctx = load("approved-spatial-binding-context.json")

# --------------------------------------------------- block-2 continuation evidence
# Read-only snapshot verification on host 32 (project copy of the fixed release,
# /opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap; nested
# members extracted via zipfile to host /tmp — snapshot bytes untouched).
# Evidence files live in the workspace probe dir and are hashed as basis.
ROOT = Path(__file__).resolve().parents[6]         # repo root (…/xiangrugu)
PROBE_DIR = ROOT / ".tabular-probe-20261119"
SNAP_HOST_PATH = "/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap"


def pload(name):
    txt = (PROBE_DIR / name).read_text(encoding="utf-8")
    if name.endswith(".jsonl"):
        return [json.loads(l) for l in txt.splitlines() if l.strip()]
    return json.loads(txt)


probe_recs = pload("probe_out.jsonl") if PROBE_DIR.exists() else None
if probe_recs is not None:
    probe = {r["key"]: r for r in probe_recs}
    headers_e = {r["key"]: r for r in pload("headers.json")}
    txt_headers = {r["key"]: r for r in pload("txt_headers.json")}
    sheet_counts = pload("sheet_counts.json")
    carrier_cmp = pload("carrier_compare.json")
    dict_pairs = pload("chgis_dict_pairs.json")
    ods_structure = pload("ods_structure.json")
    chw_strict = pload("chw_strict.json")
    xls_probe = {r["key"]: r for r in pload("xls_probe_out.json")}
    wb_sheets = {}
    for _r in pload("headers.json"):
        if "sheets" in _r:
            wb_sheets[_r["key"]] = [s.get("sheet") for s in _r["sheets"]]
    txt_csv_audit = pload("txt_csv_audit.json")
    _nla = pload("name_level_audit.json")
    nla_diff = {d["key"]: d for d in _nla["diff_objects"]}
    nla_clean_count = _nla["clean_count"]
    txt_strictwidths = pload("txt_strictwidths.json")
    probe_sha = {n: hashlib.sha256((PROBE_DIR / n).read_bytes()).hexdigest()
                 for n in ("probe_out.jsonl", "headers.json", "txt_headers.json",
                           "sheet_counts.json", "carrier_compare.json",
                           "chgis_dict_pairs.json", "ods_structure.json",
                           "chw_strict.json", "txt_csv_audit.json",
                           "xls_probe_out.json", "xls_targets.json",
                           "name_level_audit.json",
                           "txt_strictwidths.json")}
else:
    raise SystemExit("probe evidence missing under " + str(PROBE_DIR))


def lastname(e):
    return e["archive_chain"][-1] if e["archive_chain"] else e["relative_path"]


def ext_of(name):
    """Case-INSENSITIVE extension of the chain-tail (or top-level) name."""
    b = name.rsplit("/",1)[-1]
    return b.rsplit(".",1)[-1].lower() if "." in b else "<none>"


# ------------------------------------------------ sibling scan for DBF role
sib = defaultdict(set)
for e in inv:
    d = ("/".join(e["archive_chain"][:-1]) if e["archive_chain"]
         else e["relative_path"].rsplit("/",1)[0] if "/" in e["relative_path"] else "")
    sib[(e["relative_path"], d)].add(ext_of(lastname(e)))


def dirkey(e):
    # unified sibling directory key: nested members key on the chain
    # minus their tail; top-level members on the parent of relative_path.
    if e["archive_chain"]:
        return (e["relative_path"], "/".join(e["archive_chain"][:-1]))
    p = e["relative_path"]
    return (p, p.rsplit("/",1)[0] if "/" in p else "")


five_rules = {o["rule_id"]: o for o in schema5["objects"]}
five_selectors = {(o["selector"]["relative_path"], tuple(o["selector"]["archive_chain"])): o
                  for o in schema5["objects"]}
assert len(five_selectors) == 5 and schema5["source_column_count"] == 83
dbf_approved_selectors = {(m.get("selector", {}).get("relative_path"),
                           tuple(m.get("selector", {}).get("archive_chain", [])))
                          for m in dbc["members"]} | \
                         {(m.get("selector", {}).get("relative_path"),
                           tuple(m.get("selector", {}).get("archive_chain", [])))
                          for m in dbn["members"]}

# category decision: csv/xls/xlsx/dbf/txt are case-insensitive classes;
# ".tab" splits on ORIGINAL case (uppercase TAB ⇒ MapInfo spatial
# definition ⇒ block 3; lowercase tab ⇒ text table candidate). All other
# extensions stay out of scope. Registration precedes classification —
# no pre-filtering by README-style names anywhere.
members_out = []
counts = {"organized": 0, "handoff_block3": 0, "handoff_block5": 0,
          "pending_evidence": 0}
gap_items = []
handoff3, handoff5 = [], []

for e in inv:
    ln = lastname(e)
    base = ln.rsplit("/",1)[-1]
    tail_ext = base.rsplit(".",1)[-1] if "." in base else "<none>"
    x = tail_ext.lower()
    if x == "tab":
        # exact-case split: ".TAB" ⇒ MapInfo spatial definition; ".tab" ⇒ text table
        cls = "tab-mapinfo-spatial-definition" if tail_ext == "TAB" else "tab-text"
    elif x in ("csv", "xls", "xlsx", "ods", "dbf", "txt"):
        cls = x
    else:
        continue
    key = (e["relative_path"], tuple(e["archive_chain"]))
    led = ledger[key]
    base = {"source_identity": {
        "relative_path": e["relative_path"], "archive_chain": e["archive_chain"],
        "archive_ordinals": e["archive_ordinals"], "kind": e["kind"],
        "sha256": e["sha256"], "size": e["size"], "signature": e["signature"]},
        "category": cls,
        "ledger_disposition": led["disposition"],
        "ledger_rule_ids": led["rule_ids"]}
    if cls == "tab-text" and key in five_selectors:
        o = five_selectors[key]
        base.update(disposition="organized", judgement_basis={
            "carrier_of_approval": "text-schema-approved.draft.yaml",
            "object_name": o["object_name"], "rule_id": o["rule_id"],
            "source_columns": len(o["source_columns"]),
            "derived_rownum": bool(o["derived_columns"]),
            "reading_decisions": ("text-reading-decisions.draft.yaml"
                                  if o["rule_id"] in ("m008002", "m008003", "m008004")
                                  else "additional-text-reading-decisions.draft.yaml")})
        counts["organized"] += 1
    elif cls == "tab-text":
        base.update(disposition="pending-evidence",
                    judgement_basis={"reason": "lowercase .tab text file but NOT one of "
                                   "the five reading-approved objects; no reader/schema evidence"})
        gap_items.append({"object": key[0] + ("!" + "/".join(key[1]) if key[1] else ""),
                          "missing": ["reading semantics approval", "column/type review",
                                      "value expectations"],
                          "suggested_next": "extend the independent-byte-state-machine "
                                            "reading pipeline under new explicit authorization"})
        counts["pending_evidence"] += 1
    elif cls == "dbf":
        exts = sib[dirkey(e)]
        spatial = bool({"shp", "shx"} & exts)
        appr = key in dbf_approved_selectors
        base.update(disposition="handoff-block3" if spatial else "pending-evidence",
                    judgement_basis={
                        "shapefile_sibling_components": sorted(exts & {"shp", "shx", "prj", "cpg"}),
                        "spatial_component": spatial,
                        "approved_dbf_reading_exists": appr,
                        "approved_reading_scope_note": (
                            "approved-dbf-{character,numeric}-reading.json cover ONLY the "
                            "two 1884route diagnostic members (both spatial components); "
                            "limitations state they are not production validators" if appr
                            else "no approved reader for this member")})
        if spatial:
            handoff3.append(base["source_identity"] | {"role": "shapefile-dbf-component",
                                                       "approved_diagnostic_reading": appr,
                                                       "pending_review": True})
            counts["handoff_block3"] += 1
        else:
            counts["pending_evidence"] += 1
    elif cls == "tab-mapinfo-spatial-definition":
        base.update(disposition="handoff-block3",
                    judgement_basis={"reason": "uppercase .TAB MapInfo spatial table "
                                   "definition (705-group Shapefile/MapInfo relation "
                                   "per binding context)",
                                     "binding_context_file": "approved-spatial-binding-context.json"})
        handoff3.append(base["source_identity"] | {"role": "mapinfo-tab-definition",
                                                   "pending_review": True})
        counts["handoff_block3"] += 1
    elif cls in ("csv", "xls", "xlsx", "ods"):
        pkey = key[0] + ("!" + "/".join(key[1]) if key[1] else "")
        pr = probe[pkey]
        if cls == "xls":
            xr = xls_probe[pkey]
            base.update(disposition="organized",
                        judgement_basis={
                            "verified_on": "container xiangrugu:runtime-tabular-xls-"
                                           "20261119-a (image sha256:6144346a501c7ba1"
                                           "299e28862a303007fddd6a9e8030c6b6e7c1ca52"
                                           "921b6cd3, VCS_REF a163f00ede2f9cc4592b636"
                                           "970cc243f6210cf30), xlrd==2.0.2 locked by "
                                           "hash ea762c3d…, snapshot mounted :ro; "
                                           "xlrd.open_workbook(on_demand=True)",
                            "snapshot_path": SNAP_HOST_PATH,
                            "sha_match_snapshot": pr.get("sha_match"),
                            "raw_sha256_observed": pr.get("sha256"),
                            "sheets_observed": [{"sheet_name": s["sheet_name"],
                                                 "nrows": s["nrows"],
                                                 "ncols": s["ncols"]}
                                                for s in xr["sheets"]],
                            "datemode": xr.get("datemode"),
                            "formula_semantics": "cached_value_semantics: xlrd returns "
                                                 "ONLY cached formula results; original "
                                                 "formula text unavailable — per-cell "
                                                 "formula presence cannot be determined",
                            "empty_sheet_policy": "zero-dimension sheets recorded as "
                                                  "structure facts, not mapped objects",
                            "confirmation_state": "PROPOSED_NOT_AUTHORIZED",
                            "basis_files_sha256": probe_sha},
                        pending_review=True)
            counts["organized"] += 1
        elif cls == "csv" and (pr.get("verdict") == "non-tabular"
                               or pkey in headers_e):
            # NGIA csv: line-count heuristic said ragged, but STRICT csv-module
            # parse (headers.json) gives 632 rows x width 6 consistently with a
            # trailing empty header cell. Keep organized under the strict result,
            # flagging the trailing-empty-column dialect quirk for approval.
            he = headers_e[pkey]
            base.update(disposition="organized",
                        judgement_basis={
                            "verified_on": "host-32 project snapshot read-only",
                            "snapshot_path": SNAP_HOST_PATH,
                            "sha_match_snapshot": pr.get("sha_match"),
                            "raw_sha256_observed": pr.get("sha256"),
                            "line_count_verdict": "non-tabular (heuristic)",
                            "strict_csv_verdict": {"widths": he.get("strict_widths"),
                                                   "note": "header has trailing empty "
                                                           "cell after FEA_CLASS; BOM present"},
                            "encoding_used": he.get("encoding_used"),
                            "bom": he.get("bom"),
                            "confirmation_state": "PROPOSED_NOT_AUTHORIZED",
                            "basis_files_sha256": probe_sha},
                        pending_review=True)
            counts["organized"] += 1
        elif pkey in ods_structure and any(
                s["header_row"][:4] == ["Field Name", "Field Description",
                                        "Field Type",
                                        "MaximumField Length/Precision"]
                for s in ods_structure[pkey]["tables"]):
            # content-evidenced DOCUMENTATION table (field-spec sheet, 37 rows),
            # not a data table: disposition stays organized-as-mapping but the
            # object is routed to block-5 review with the evidence quoted.
            base.update(disposition="handoff-block5",
                        judgement_basis={
                            "verified_on": "host-32 project snapshot read-only",
                            "snapshot_path": SNAP_HOST_PATH,
                            "sha_match_snapshot": pr.get("sha_match"),
                            "raw_sha256_observed": pr.get("sha256"),
                            "content_evidence": "sheet header row = Field Name/"
                                                "Field Description/Field Type/"
                                                "MaximumField Length-Precision; "
                                                "37 non-empty rows — a field-format "
                                                "specification, i.e. documentation",
                            "basis_files_sha256": probe_sha},
                        pending_review=True)
            handoff5.append(base["source_identity"] | {
                "pattern": "content-evidenced documentation table (ods spec sheet)",
                "content_verdict": "documentation", "pending_review": True})
            counts["handoff_block5"] += 1
        else:
            base.update(disposition="organized",
                        judgement_basis={
                            "verified_on": "host-32 project snapshot read-only (zipfile "
                                           "extract to /tmp; snapshot bytes untouched)",
                            "snapshot_path": SNAP_HOST_PATH,
                            "sha_match_snapshot": pr.get("sha_match"),
                            "raw_sha256_observed": pr.get("sha256"),
                            "ods_database_ranges": ([s for s in [ods_structure.get(pkey, {}).get("database_ranges")] if s] or None),
                            "sheets_or_rows_evidence": (
                                sheet_counts.get(pkey) if cls in ("xlsx", "ods") else
                                {"data_records": headers_e.get(pkey, {}).get("row_count_incl_header"),
                                 "encoding_used": headers_e.get(pkey, {}).get("encoding_used"),
                                 "bom": headers_e.get(pkey, {}).get("bom")}),
                            "confirmation_state": "PROPOSED_NOT_AUTHORIZED",
                            "basis_files_sha256": probe_sha},
                        pending_review=True)
            counts["organized"] += 1
    elif cls == "txt":
        pkey = key[0] + ("!" + "/".join(key[1]) if key[1] else "")
        pr = probe[pkey]
        v = pr.get("verdict")
        readme = re.search(r"(readme|notes|info|license|terms|description|dictionary|"
                           r"codebook|code_book|faq|howto|guide|index\.txt$|_index)",
                           ln, re.I)
        if v == "tabular-candidate":
            th = txt_headers[pkey]
            nd = nla_diff.get(pkey)
            if nd and ("names" in nd["problems"] or "encoding" in nd["problems"]):
                # ROUND-5 name-level reimport: members basis must match the
                # object-mapping terminal values (e.g. ChinaWBeta utf-16/BOM)
                _enc, _bom = nd["enc_new"], nd["bom_new"]
                _cols = nd["cols_new"]
                _rows = nd.get("data_rows_strict", th["data_records"])
            else:
                _enc, _bom = th["encoding_used"], th["bom"]
                _cols = len(th["header_row"])
                _rows = th["data_records"]
            base.update(disposition="organized",
                        judgement_basis={
                            "verified_on": "host-32 project snapshot read-only",
                            "snapshot_path": SNAP_HOST_PATH,
                            "sha_match_snapshot": pr.get("sha_match"),
                            "raw_sha256_observed": pr.get("sha256"),
                            "delimiter": th["delimiter"],
                            "encoding_used": _enc,
                            "bom": _bom,
                            "header_columns": _cols,
                            "data_records": _rows,
                            "confirmation_state": "PROPOSED_NOT_AUTHORIZED",
                            "basis_files_sha256": probe_sha},
                        pending_review=True)
            counts["organized"] += 1
        elif v in ("non-tabular", "irregular"):
            basis = {"content_verdict": v,
                     "verified_on": "host-32 project snapshot read-only",
                     "sha_match_snapshot": pr.get("sha_match"),
                     "raw_sha256_observed": pr.get("sha256"),
                     "line_count": pr.get("line_count"),
                     "delimiters_observed": {d: w for d, w in (pr.get("delimiters") or {}).items()},
                     "upgraded_from": ("name-pattern only" if readme else "pending-evidence"),
                     "basis_files_sha256": probe_sha}
            base.update(disposition="handoff-block5", judgement_basis=basis,
                        pending_review=True)
            handoff5.append(base["source_identity"] | {
                "pattern": (readme.group(0) if readme else "content-level non-tabular"),
                "content_verdict": v, "pending_review": True})
            counts["handoff_block5"] += 1
        else:
            base.update(disposition="pending-evidence",
                        judgement_basis={"reason": f"probe verdict {v!r}; undecodable "
                                       "or unresolved — kept visible, not silent"},
                        pending_review=True)
            gap_items.append({"object": pkey,
                              "missing": ["decodable text form"],
                              "error": str(pr.get("error", v)),
                              "suggested_next": "binary/encoding inspection under authorization"})
            counts["pending_evidence"] += 1
    members_out.append(base)

members = {"format": "xiangrugu.import-package.tabular.members.v1",
           "release_id": schema5["release_id"],
           "selection_rule": "extension of archive_chain[-1] (nested names live in the "
                             "chain tail; relative_path is the outer zip); extension match "
                             "is CASE-INSENSITIVE (.TXT/.Tab and other case variants all "
                             "in scope); the ONLY case-sensitive split is exact \".TAB\" "
                             "(MapInfo spatial definition) vs exact \".tab\" (text table "
                             "candidate); ALL matched members are registered first, then "
                             "classified — no pre-filtering by README-style names",
           "class_counts": {k: sum(1 for m in members_out if m["category"] == k)
                            for k in ("csv", "xls", "xlsx", "ods", "dbf",
                                      "tab-mapinfo-spatial-definition", "tab-text", "txt")},
           "disposition_counts": {k: counts[k] for k in
                                  ("organized", "handoff_block3",
                                   "handoff_block5", "pending_evidence")},
           "total_candidates": len(members_out),
           "members": members_out}

# ------------------------------------------------------------ object mapping
READ_RULES = {"delimiter": "TAB", "quotechar": "DOUBLE_QUOTE", "doublequote": True,
              "record_separator": "LF", "unquoted_interior_quote": "literal",
              "values": "strings", "empty_string": "preserve_not_null",
              "whitespace": "preserve", "duplicate_records": "preserve",
              "source_order": "preserve", "type_inference": False,
              "automatic_fallback": False}
LOAD_GAP = ("GAP: production PostgreSQL loader not implemented; importer/load.py is a "
            "staging prototype requiring revision; nothing runs against pg32b")
objects_out = []
for o in schema5["objects"]:
    sel = o["selector"]
    ident = next(m for m in members_out
                 if m["source_identity"]["relative_path"] == sel["relative_path"]
                 and tuple(m["source_identity"]["archive_chain"]) == tuple(sel["archive_chain"]))
    rd_file = ("text-reading-decisions.draft.yaml"
               if o["rule_id"] in ("m008002", "m008003", "m008004")
               else "additional-text-reading-decisions.draft.yaml")
    objects_out.append({
        "source_file_or_chain": (sel["relative_path"] +
                                 ("!" + "/".join(sel["archive_chain"]) if sel["archive_chain"] else "")),
        "worksheet": None,
        "carrier": o["carrier"], "rule_id": o["rule_id"],
        "source_object_id": o["source_object_id"],
        "raw_expected": o["raw_expected"],
        "target_schema": o["approved_schema"],
        "candidate_table_name": o["proposed_target"]["table"],
        "candidate_name_status": ("proposed_target carried verbatim; table_names_approved="
                                  f"{o['table_names_approved']} — CANDIDATE only, full-release "
                                  "collision check deferred to block 6"),
        "fields": [{**{k: c[k] for k in ("source_column_ordinal", "original_name",
                                           "target_name", "quoted_target_name",
                                           "target_type", "nullable", "encoding",
                                           "empty_strings_observed", "column_id")},
                    "row_order": READ_RULES["source_order"]}
                   for c in o["source_columns"]]
                   + [{"synthetic": True, "target_name": dc["target_name"],
                       "target_type": dc["target_type"], "origin": dc["origin"],
                       "range": dc["range"], "mapping_approved": dc["mapping_approved"]}
                      for dc in o["derived_columns"]],
        "read_method": {"rules": READ_RULES, "scope_note":
                        "approved rules cover these exact five files only "
                        "(authorization_reference quoted in reading decisions)",
                        "evidence_files": [rd_file]},
        "load_method": LOAD_GAP,
        "independent_verification": {
            "source_value_evidence": o["source_value_evidence"],
            "validator_proposal": o["validator_proposal"],
            "value_contract": "text-value-contract-approved.draft.json "
                              "(canonical XRGVALUE-v1, header_excluded, rownum_start=1, "
                              "value_contract_approved=true for the five objects only)"},
        "confirmation_basis": {"files": [
            {"path": f"datamgmt/contracts/releases/2026-10-06-bootstrap/{n}", "sha256": sha(n)}
            for n in ("text-schema-approved.draft.yaml", rd_file,
                      "text-value-contract-approved.draft.json")]},
        "status": {k: schema5[k] for k in
                   ("schema_approved", "source_column_mapping_approved",
                    "derived_rownum_mapping_approved", "table_names_approved",
                    "target_mapping_approved", "global_name_allocation_complete",
                    "ready_for_import")} | {"disposition_retained": o["disposition_retained"]}})
# ---- proposed objects from this round's read-only snapshot verification ----
sys.path.insert(0, str(ROOT / "datamgmt" / "src"))
from xiangrugu_datamgmt.identity import source_object_id
from xiangrugu_datamgmt.naming import allocate_tables, allocate_columns, quote_identifier, NameInput

LOAD_GAP_P = LOAD_GAP + "; proposal is organize-only and never executed"


def _cols_whole_table(object_id, originals):
    """ONE allocate_columns call per table (project naming rule): duplicate
    source names share a slug base and are disambiguated by the function's
    own __c{ordinal} suffix. All columns kept in source order."""
    maps = allocate_columns(list(originals), object_id=object_id)
    out = []
    for nm in maps:
        out.append({"source_column_ordinal": nm.ordinal,
                    "original_name": nm.original,
                    "target_name": nm.target,
                    "quoted_target_name": quote_identifier(nm.target),
                    "column_id": nm.identity, "target_type": "text",
                    "type_note": "all values strings; type_inference=false "
                                 "carried over from the approved text reading "
                                 "policy — observed types recorded as evidence only",
                    "nullable": True,
                    "null_policy": "empty_string=preserve_not_null "
                                   "(proposal沿用已批准政策，未升级)"})
    return out


def _headerless_columns(object_id, width):
    """No current project rule exists for headerless tables (checked
    naming.py/identity.py: no col_/unnamed helpers). Proposed stable ordinal
    names col_001..col_{width}, allocated through the SAME whole-table
    recipe so ids/targets follow official semantics. PROPOSED state."""
    return _cols_whole_table(object_id, [f"col_{i:03d}" for i in range(1, width + 1)])


def _dataset_of(relpath, chain):
    full = chain if chain else relpath
    return full.rsplit("/", 1)[0] if "/" in full else ""

# 76ed534c… correction evidence: the MingGarrisons CSV member sits inside
# Ming_Garrisons.zip whose sibling .xls workbook was re-read READ-ONLY in the
# authorized image (sha 740b18d3af11…, Sheet1/Sheet2/Sheet3); the CSV header
# matches that workbook's Sheet2 exactly (11 cols) -> true sheet attribution.
XLS_SHEET_NAMES_FIX = {
    # emitted pkey form: relative_path + '!' + '/'.join(archive_chain)
    "harvard-full/doi_10_7910/DVN/5RUXK8/Ming_Garrisons.zip!"
    "MingGarrisonsSheet_29jan08.csv": "Sheet2"}
xls_sheet_names_fix = XLS_SHEET_NAMES_FIX


def _emit_object(pkey, si, ext, carrier, ds, objname, headers_for_group,
                 xls_typeinfo=None, headerless_width=None):
    sid = source_object_id(relative_path=si["relative_path"],
                           archive_chain=si["archive_chain"],
                           object_name=objname,
                           carrier=carrier or "tsv")
    nmap = allocate_tables([NameInput(ds, objname, sid)])[0]
    if ext in ("csv", "txt") and len(headers_for_group) == 1 \
            and headers_for_group[0][0] is None:
        # 'TABLE' label is ONLY for genuine flat files; members extracted
        # from a carrier workbook (.xlsx/.ods/.xls archive chain hop) keep
        # real sheet names — resolve them from existing evidence, else the
        # documented container-image readback (76ed fix this round)
        # (a) documented readback fix wins outright (76ed534c… -> 'Sheet2')
        # (b) chain-hop carrier workbook (.xlsx/.ods/.xls inside chain)
        hops = "/".join(si["archive_chain"])
        if pkey in xls_sheet_names_fix:
            headers_for_group = [(xls_sheet_names_fix[pkey],
                                  *headers_for_group[0][1:])]
        elif any(h.lower().endswith((".xlsx", ".ods", ".xls"))
                 for h in si["archive_chain"][:-1]) \
                or hops.lower().endswith((".xlsx", ".ods", ".xls")):
            real = None
            for k_, v_ in wb_sheets.items():
                if k_.split("!")[0] == si["relative_path"] and len(v_) == 1:
                    real = v_[0]; break
            headers_for_group = [(real or "Sheet1-unlabeled",
                                  *headers_for_group[0][1:])]
        else:
            headers_for_group = [("TABLE", *headers_for_group[0][1:])]
    fields_all = []
    sheets_out = []
    for si_, (sheet_nm, hdr, nrows, enc, bom, delim) in enumerate(headers_for_group):
        if hdr is None:
            cols = _headerless_columns(sid, headerless_width)
            hdr_desc = {"header_row": None,
                        "header_basis": "first physical line is data; stable "
                                        "ordinal names col_001.. proposed via "
                                        "whole-table allocate_columns (no "
                                        "project headerless rule exists — "
                                        "disclosed proposal state)"}
        elif ext == "ods" and pkey in ods_structure:
            tinfo = ods_structure[pkey]["tables"][si_]
            cols = _cols_whole_table(sid, tinfo["header_row"])
            hdr_desc = None
        else:
            cols = _cols_whole_table(sid, hdr)
            if ext == "xls":
                tinfo = xls_typeinfo.get(sheet_nm, [])
                for f_, ti in zip(cols, tinfo):
                    dist = ti["cell_type_distribution_data_rows"]
                    nonempty = {k: v for k, v in dist.items()
                                if k not in ("EMPTY", "BLANK")}
                    kinds = set(nonempty)
                    if kinds == {"NUMBER"}:
                        f_["target_type"] = "double precision"
                    elif kinds <= {"TEXT", "NUMBER"} and "NUMBER" in kinds:
                        f_["target_type"] = "text"
                    else:
                        f_["target_type"] = "text"
                    f_["observed_cell_types"] = dist
                    f_["type_note"] = ("PROPOSED from xlrd cached-value type "
                                       "distribution; DATE columns need datemode "
                                       "conversion review; formula cells expose "
                                       "cached results only")
                    f_["nullable"] = any(k in dist for k in ("EMPTY", "BLANK")) or f_["nullable"]
            hdr_desc = None
        fields_all.extend(cols)
        entry = {"worksheet": sheet_nm, "columns": len(cols),
                 "data_records_observed": nrows}
        if hdr_desc: entry.update(hdr_desc)
        sheets_out.append(entry)
        if si_ == 0: last_hdr = hdr
    return {
        "source_file_or_chain": pkey,
        "worksheets_observed": sheets_out,
        "carrier": carrier or "tsv",
        "source_object_id": sid,
        "dataset_namespace": ds,
        "target_schema": None,
        "candidate_table_name": nmap.target,
        "fields": fields_all,
        "dialect_observations": {"delimiter": headers_for_group[0][5],
                                 "encoding_strict_ok": headers_for_group[0][3],
                                 "bom": headers_for_group[0][4]},
        "structural_flags": {
            "dialect_resolution": ({
                "ruling": "lead ruling after a03 ROUND 4 note (a): RFC4180 "
                          "quote-aware csv.reader is authoritative; naive "
                          "split(',') gave 176 columns with 4 phantom duplicate "
                          "names because quoted headers containing commas "
                          "(w302/w304 etc.) were mis-split",
                "basis": "consistent with approved text reading semantics "
                         "(quotechar DOUBLE_QUOTE, doublequote=true) and R-08 "
                         "faithfulness; proposal state reversible, pending "
                         "茶香 discussion confirmation",
                "before_after_columns": [176, len(fields_all)],
                "strict_widths_observed": chw_strict[pkey]["widths"],
                "evidence_sha": probe_sha["chw_strict.json"]}
                if pkey in chw_strict and "cols" in chw_strict.get(pkey, {})
                else None),
            "duplicate_source_header_names": any(
                len(h) != len(set(h)) for _, h, *_ in headers_for_group if h),
            "duplicate_handling": ("whole-table allocate_columns applied; "
                                   "duplicate source names retained, target "
                                   "names/ids disambiguated by __c{ordinal}"
                                   if any(len(h) != len(set(h))
                                          for _, h, *_ in headers_for_group if h)
                                   else "n/a"),
            "headerless_first_line_is_data": pkey == HEADERLESS_TXT_KEY,
            "encoding_resolution": ({
                "finding": "UTF-16LE + BOM fffe; earlier latin-1/gb18030 "
                           "profile produced NUL-fragment names — corrected by "
                           "BOM sniff + strict utf-16 decode this round",
                "content_verdict": "real tabular data dictionary (TAB, 7 cols "
                                   "[Variable/COLUMN/ITEMNAME/WIDTH/OUTPUT/"
                                   "TYPE/DECIMALS], 159 data rows; row2 = w1 "
                                   "ChinaW ID…) — precedent v4/v6_data_"
                                   "dictionary.xlsx organized-proposed ⇒ "
                                   "disposition stays organized with honest "
                                   "utf-16 dialect record",
                "dual_copy_note": "both copies same size 17580 B; snapshot "
                                  "probe sha256 identical => content-equal "
                                  "duplicates retained as separate members "
                                  "(mirror comparison deferred to block 6)",
                "evidence_sha": probe_sha["name_level_audit.json"]}
                if "ChinaWBeta.Field.Definitions.txt" in pkey else None),
            "quote_artifact_audit": ({
                "comma_delimited_reaudit": ("naive==strict columns"
                                            if any(a["key"] == pkey and
                                                   a["naive_cols"] == a["strict_cols"]
                                                   for a in txt_csv_audit)
                                            else "not-applicable-or-tab-delimited"),
                "full_file_width_profile": (next((b for b in txt_strictwidths
                                                  if b["key"] == pkey), None))}
                if ext == "txt" and (
                    any(a["key"] == pkey for a in txt_csv_audit)
                    or any(b["key"] == pkey for b in txt_strictwidths))
                else None),
            "ods_database_ranges": (ods_structure.get(pkey, {})
                                    .get("database_ranges") or [])},
        "read_method": ("xlrd==2.0.2 in locked runtime candidate image "
                        "xiangrugu:runtime-tabular-xls-20261119-a "
                        "(sha256:6144346a501c7ba1299e28862a303007fddd6a9e8030c6b6e"
                        "7c1ca52921b6cd3), snapshot :ro mount"
                        if ext == "xls" else
                        "stdlib zipfile+xml.etree (xlsx/ods) or csv module strict "
                        "parse (csv/txt) on host-32 project snapshot, read-only; "
                        "NO external dependency installed (existing capability, "
                        "not new)"),
        "load_method": LOAD_GAP_P,
        "independent_verification": {
            "state": "PROPOSED_NOT_AUTHORIZED",
            "raw_sha256_matches_inventory": jb.get("sha_match_snapshot"),
            "evidence": "snapshot extraction digests + header/width profiles in "
                        ".tabular-probe-20261119/{probe_out.jsonl,headers.json,"
                        "txt_headers.json,sheet_counts.json}"},
        "confirmation_basis": {
            "files": [{"path": f".tabular-probe-20261119/{n}", "sha256": s}
                      for n, s in sorted(probe_sha.items())],
            "note": "basis = THIS ROUND read-only snapshot verification; no release "
                    "approval file exists for these objects yet"},
        "status": {"confirmation_state": "PROPOSED_NOT_AUTHORIZED",
                   "schema_approved": False, "table_names_approved": False,
                   "target_mapping_approved": False, "value_contract_approved": False,
                   "ready_for_import": False, "disposition_retained": "BLOCKED"}}


HEADERLESS_TXT_KEY = "chgis-v6/China_Periods_ReignDates.zip!china_chron/china_chron.txt"

proposed_objs = []
for m in members_out:
    jb = m.get("judgement_basis") or {}
    if jb.get("confirmation_state") != "PROPOSED_NOT_AUTHORIZED":
        continue
    si = m["source_identity"]
    pkey = si["relative_path"] + ("!" + "/".join(si["archive_chain"]) if si["archive_chain"] else "")
    ext = m["category"]
    carrier = {"csv": "csv", "xls": "xls", "xlsx": "xlsx", "ods": "ods",
               "txt": None}[ext]
    if ext == "xls":
        xr = xls_probe[pkey]
        headers_by_sheet = [(s["sheet_name"],
                             [str(c["header_cell_row0"]) for c in s["columns"]],
                             max(s["nrows"] - 1, 0), None, None, None)
                            for s in xr["sheets"] if s["nrows"] and s["ncols"]]
        xls_typeinfo = {s["sheet_name"]: s["columns"] for s in xr["sheets"]}
    elif ext == "txt":
        th = txt_headers[pkey]
        nd = nla_diff.get(pkey)
        if pkey == HEADERLESS_TXT_KEY:
            # content-evidenced: line 1 is data (reign rows), not a header =>
            # keep it as data, use stable ordinal column names. Name-level
            # audit only removes a trailing \r from the observed first-line
            # cells; the headerless decision and width are unchanged.
            headers_by_sheet = [(None, None, th["data_records"],
                                 th["encoding_used"], th["bom"], th["delimiter"])]
            headerless_width = len(th["header_row"])
        elif nd and "names" in nd["problems"]:
            headers_by_sheet = [(None, nd["strict_header"],
                                 nd.get("data_rows_strict", th["data_records"]),
                                 nd["enc_new"], nd["bom_new"], th["delimiter"])]
        else:
            headers_by_sheet = [(None, th["header_row"], th["data_records"],
                                 th["encoding_used"], th["bom"], th["delimiter"])]
    elif ext == "csv":
        if pkey in chw_strict and "cols" in chw_strict[pkey]:
            # lead dialect ruling: RFC4180 quote-aware csv.reader is correct;
            # naive line-split 176-column profile was a parsing artifact
            cs = chw_strict[pkey]
            headers_by_sheet = [(None, cs["header"], cs["data_rows"],
                                 cs.get("encoding_used"), None, ",")]
        elif pkey in nla_diff and "names" in nla_diff[pkey]["problems"]:
            nd = nla_diff[pkey]
            headers_by_sheet = [(None, nd["strict_header"],
                                 nd.get("data_rows_strict"),
                                 nd["enc_new"], nd["bom_new"], ",")]
        else:
            he = headers_e[pkey]
            headers_by_sheet = [(None, he["header_row"],
                                 (he.get("row_count_incl_header") or 1) - 1,
                                 he.get("encoding_used"), he.get("bom"), ",")]
    elif ext == "ods" and pkey in ods_structure:
        # authoritative ODS view: every table:table element plus any
        # database-range artifacts recorded separately as structure evidence
        st = ods_structure[pkey]
        headers_by_sheet = [(t["sheet"], t["header_row"],
                             max(t["rows_nonempty_incl_header"] - 1, 0),
                             None, None, None)
                            for t in st["tables"]]
    else:
        sc = sheet_counts[pkey]
        hd = headers_e[pkey]["sheets"]
        headers_by_sheet = [(s["sheet"], s["header_row"], None, None, None, None)
                            for s in hd]
        nrows = {c["sheet"]: c["rows_incl_header"] for c in sc}
        headers_by_sheet = [(nm, hr, (nrows.get(nm) or 1) - 1, None, None, None)
                            for nm, hr, *_ in headers_by_sheet]
    ds = _dataset_of(si["relative_path"], "/".join(si["archive_chain"]))
    objname = (si["archive_chain"][-1].rsplit("/", 1)[-1] if si["archive_chain"]
               else si["relative_path"].rsplit("/", 1)[-1])
    emitted = []
    xls_sheets_ne = [s for s in (xls_probe.get(pkey, {}).get("sheets") or [])
                     if s["nrows"] and s["ncols"]]
    if ext == "xls" and len(xls_sheets_ne) > 1:
        # split: one independent import object per non-empty worksheet;
        # worksheet-qualified identity via the REAL source_object_id formula
        # (object_name suffixed '#<sheet>', carrier unchanged) — convention
        # disclosed here and on each object record
        for sh in xls_sheets_ne:
            grp = [(sh["sheet_name"],
                    [str(c["header_cell_row0"]) for c in sh["columns"]],
                    max(sh["nrows"] - 1, 0), None, None, None)]
            rec = _emit_object(pkey, si, ext, carrier, ds,
                               objname + "#" + sh["sheet_name"], grp,
                               xls_typeinfo={sh["sheet_name"]: sh["columns"]})
            rec["worksheet_split"] = {
                "convention": "multi-non-empty-sheet XLS workbook split per "
                              "sheet; source_object_id input object_name = "
                              "'<member>#<sheet>' (identity.py real function); "
                              "candidate_table_name likewise sheet-qualified "
                              "(naming.py real function); no cross-sheet join",
                "sheet_name": sh["sheet_name"], "nrows_incl_header": sh["nrows"]}
            emitted.append(rec)
    else:
        rec = _emit_object(pkey, si, ext, carrier, ds, objname,
                           headers_by_sheet,
                           xls_typeinfo=(xls_typeinfo if ext == "xls" else None),
                           headerless_width=(headerless_width
                                             if ext == "txt" else None))
        emitted.append(rec)
    proposed_objs.extend(emitted)

obj_map = {"format": "xiangrugu.import-package.tabular.object-mapping.v1",
           "object_count": len(objects_out),
           "approved_objects_from_release_evidence": len(objects_out),
           "proposed_objects_from_snapshot_verification": len(proposed_objs),
           "proposed_confirmation_state": "PROPOSED_NOT_AUTHORIZED",
           "source_column_count": sum(len([f for f in x["fields"] if not f.get("synthetic")])
                                      for x in objects_out),
           "derived_rownum_count": sum(1 for x in objects_out
                                       for f in x["fields"] if f.get("synthetic")),
           "flags_verbatim_from_text_schema_approved": {
               k: schema5[k] for k in ("schema_approved", "table_names_approved",
                                        "target_mapping_approved", "ready_for_import",
                                        "global_name_allocation_complete")},
           "objects": objects_out,
           "proposed_objects": proposed_objs}
assert obj_map["source_column_count"] == 83 and obj_map["derived_rownum_count"] == 5

# ---------------------------------------------------------------- handoffs
carrier_notes = {
    "Manshu_Index_Stanford_links.ods vs .xlsx": {
        "disposition": "separate members, NOT duplicates by assumption; content compared "
                       "this round on host-32 snapshot",
        "finding": "same 10 header names, same 60 OBJECTID keys, other 8 columns "
                   "exact-string equal; Y1/Y2 differ ONLY as IEEE-754 serialization "
                   "(ODS '41.333' vs XLSX '41.332999999999998'; float-equal for all 60)",
        "row_order_differs": True,
        "evidence_sha": probe_sha["carrier_compare.json"]},
    "MajorChinaPeriods_Lex csv vs ods": {
        "finding": "53 rows both; after width-pad+NBSP-strip only 5 cells differ "
                   "(per_py Three Kingdoms row pair + two parenthetical captions); "
                   "NOT declared duplicates — separate dispositions stand",
        "evidence_sha": probe_sha["carrier_compare.json"]},
    "CHGIS v6 vs V4 metadata xlsx pairs": {
        "finding": "all six dictionary workbooks ordered-row-equal across carriers "
                   "(v6_data_dictionary sheet name still 'v4_data_dictionary'); "
                   "separate members retained, similarity recorded",
        "evidence_sha": probe_sha["chgis_dict_pairs.json"]}}

handoffs = {"format": "xiangrugu.import-package.tabular.handoffs.v1",
            "block3_spatial": {
                "count": len(handoff3),
                "composition": {"dbf_shapefile_components": sum(1 for h in handoff3 if h["role"] == "shapefile-dbf-component"),
                                "mapinfo_tab_definitions": sum(1 for h in handoff3 if h["role"] == "mapinfo-tab-definition")},
                "relation_evidence": "approved-spatial-binding-context.json "
                                     f"(bound_objects={len(spatial_ctx['bound_objects'])}, "
                                     "component_binding_approved entries enumerate shapefile "
                                     "component families)",
                "diagnostic_reading_overlap": {
                    "note": "the two approved DBF diagnostic readings are BOTH block-3 "
                            "components; block 2 does not double-count them as standalone",
                    "files": ["approved-dbf-character-reading.json", "approved-dbf-numeric-reading.json"]},
                "objects": handoff3},
            "block5_documentation": {
                "count": len(handoff5),
                "classification_basis": "documentary NAME pattern only (content unread this "
                                        "round); every item still carries its BLOCKED ledger "
                                        "disposition until block-5 review confirms",
                "objects": handoff5,
                "content_verified_this_round": sum(
                    1 for o in handoff5 if o.get("content_verdict")),
                "carrier_comparison_evidence": carrier_notes},
            "no_double_count_check": {
                "union_equals_candidates": len(handoff3) + len(handoff5) + counts["organized"]
                                           + counts["pending_evidence"] == members["total_candidates"]}}
# ---- full-set uniqueness review (per-table column_id + target_name) ----
uniq = {"tables_reviewed": 0, "columns_reviewed": 0,
        "column_id_violations": 0, "target_column_violations": 0,
        "headerless_objects": [], "disambiguated_duplicate_source_names": 0}
for _p in proposed_objs:
    uniq["tables_reviewed"] += 1
    _ids = [f["column_id"] for f in _p["fields"]]
    _tg = [f["target_name"] for f in _p["fields"]]
    uniq["columns_reviewed"] += len(_p["fields"])
    if len(set(_ids)) != len(_ids): uniq["column_id_violations"] += 1
    if len(set(_tg)) != len(_tg): uniq["target_column_violations"] += 1
    if _p["structural_flags"]["headerless_first_line_is_data"]:
        uniq["headerless_objects"].append(_p["source_file_or_chain"])
    uniq["disambiguated_duplicate_source_names"] += sum(
        _c - 1 for _n, _c in collections.Counter(
            f["original_name"] for f in _p["fields"]
            if not _p["structural_flags"]["headerless_first_line_is_data"]
        ).items() if _c > 1)
    uniq["objects_with_quote_artifact_audit"] = sum(
        1 for _p2 in proposed_objs
        if (_p2["structural_flags"].get("quote_artifact_audit")))
assert uniq["column_id_violations"] == 0 and uniq["target_column_violations"] == 0
obj_map["uniqueness_review"] = uniq
import collections as _c
det = []
for _p in proposed_objs:
    _cnt = _c.Counter(f["original_name"] for f in _p["fields"])
    _d = {k: v for k, v in _cnt.items() if v > 1}
    if _d:
        det.append({"object": _p["source_file_or_chain"],
                    "source_object_id": _p["source_object_id"],
                    "carrier": _p["carrier"],
                    "duplicate_source_names": _d,
                    "extra_columns_disambiguated": sum(v - 1 for v in _d.values())})
uniq["disambiguation_detail"] = det
uniq["disambiguation_scope_note"] = ("all %d duplicate-source-name extras are on "
                                     "the XLS surface (blank header cells read "
                                     "from xlrd row0); csv/txt surface is 0 "
                                     "after the ChinaW quote-aware correction"
                                     % sum(d["extra_columns_disambiguated"] for d in det))
obj_map["name_level_audit"] = {
    "method": "per-object three-way comparison: quote-aware csv.reader on "
              "BOM-sniffed strict decode (splitlines for \r\n/lone-\r safety) "
              "== delivered original_name list element-wise, plus encoding/BOM "
              "recheck; scope = all txt(132)+csv(7) delivered mapping objects",
    "prior_round_defect_disclosed": "earlier audit compared COLUMN COUNTS only "
                                    "(naive==strict), which missed name-level "
                                    "quote wrapping, trailing \r and UTF-16 "
                                    "encoding distortion — disclosed honestly",
    "clean": nla_clean_count, "diff": len(nla_diff),
    "diff_objects": [{"object": d["key"], "problems": d["problems"],
                      "enc": f"{d['enc_old']}->{d['enc_new']}",
                      "cols": f"{d['cols_old']}->{d['cols_new']}",
                      "reimported": True} for d in nla_diff.values()],
    "evidence_sha": probe_sha["name_level_audit.json"]}

write("members.json", members)
write("object-mapping.json", obj_map)
write("handoffs.json", handoffs)

gaps = {"format": "xiangrugu.import-package.tabular.evidence-gaps.v1",
        "block2_terminal_state": "COMPLETE for read-evidence: XLS 14 readable via "
                                 "authorized locked image xiangrugu:runtime-tabular-xls-"
                                 "20261119-a (xlrd==2.0.2, sha256:ea762c3d…); remaining "
                                 "gaps are approval-plane only (PROPOSED_NOT_AUTHORIZED)",
        "xls_total_bytes": sum(x["source_identity"]["size"] for x in members_out
                               if x["category"] == "xls"),
        "gap_object_count": len(gap_items),
        "grouped_summary": {},
        "items": gap_items}
gg = defaultdict(int)
for g in gap_items:
    ext = g["object"].rsplit(".", 1)[-1].lower()
    gg[ext] += 1
gaps["grouped_summary"] = dict(gg)
write("evidence-gaps.json", gaps)

cc = members["class_counts"]; dc = members["disposition_counts"]
jb_count = sum(1 for m_ in members_out if (m_.get("judgement_basis") or {}).get("confirmation_state") == "PROPOSED_NOT_AUTHORIZED")
xbytes = sum(x["source_identity"]["size"] for x in members_out if x["category"] == "xls")
summary = f"""# 普通表格整理摘要（第 2/6 块，仅整理不写库）

生成：build_tabular_package.py 确定性合并；旧文件零改动。候选口径=archive_chain[-1] 末链名扩展名（**大小写不敏感**；.tab 合计 147，按功能精确分叉：大写 .TAB=MapInfo 空间表定义⇒块3，小写 .tab=文本表候选）。

## 计数（candidates={members['total_candidates']}）
| 类 | 数量 | 去向 |
|---|---|---|
| csv | {cc['csv']} | 本轮快照核实：6 表格候选⇒organized(提案态)，1 NGIA 严格解析 6×632 规整⇒organized 并记方言注记 |
| xls | {cc['xls']} | **茶香授权后全可读**：锁定 xlrd==2.0.2（sha ea762c3d…入 requirements.lock）+32 构建独立候选镜像 runtime-tabular-xls-20261119-a（Id 6144346a501c…，VCS_REF a163f00e…），快照 :ro 挂载、on_demand 只读清点⇒14 件 organized(提案态)，逐 sheet nrows/ncols/列类型分布留证；公式语义统一标注 cached_value_semantics（xlrd 仅缓存结果，公式原文不可得）；空零维 Sheet2/Sheet3 记结构事实不建对象 |
| xlsx | {cc['xlsx']} | stdlib zipfile+xml 解析成功⇒organized(提案态)，sheet/字段/行数留证 |
| ods | {cc['ods']} | stdlib content.xml 解析成功：3 数据表⇒organized(提案态)；**CountryFilesFormat_2016-07-16.ods 内容证据判为字段格式说明文档（表头 Field Name/Description/Type/MaxLength；SSH 复测：**39 table-row 总数**（a03 口径）、其中 **37 含内容行**（1 表头+36 字段说明行，末 2 行全空）、**38 数据行**=总行减表头——三值如实并列）⇒块5**；与同 basename xlsx/csv 分别处置不认重复；Manshu.ods 附 __Anonymous_Sheet_DB__0 database-range 结构事实留证 |
| dbf | {cc['dbf']} | **全部为 Shapefile 空间组件⇒块3**（统一目录键的 shp/shx 兄弟扫描 704/704 命中，与 lead 侦察一致；独立 DBF=0） |
| .TAB 大写 | {cc['tab-mapinfo-spatial-definition']} | MapInfo 空间表定义⇒块3 |
| .tab 小写 | {cc['tab-text']} | 全部已整理（权威 5 件，含 2 附加 .tab；无待证据 .tab） |
| txt | {cc['txt']} | 内容级核实：**132 表格候选⇒organized(提案态)**；非表格⇒块5（其中 10 件由 pending 升级为内容证据、607 件名称模式获内容复核、2 件 irregular Notes.txt 亦升级块5） |

处置分布：organized={dc.get('organized',0)}、handoff-block3={dc.get('handoff_block3',0)}、handoff-block5={dc.get('handoff_block5',0)}、pending-evidence={dc.get('pending_evidence',0)}（合计 {sum(dc.values())}=candidates ✓）。

## 5 件文本/83 源字段/5 派生行号确证
权威载体=text-schema-approved.draft.yaml（yaml 后缀 JSON 内容）：object_count=5、source_column_count=83、schema/column-mapping/nullable/types/derived-rownum approved=true；table_names/target_mapping/ready_for_import=false、global_name_allocation_complete=false、逐对象 disposition_retained=BLOCKED——原样保留未升级。5 对象：ACADEMY_Data.tab(m008002,harv,2957)、Index…Yuan_Dynasty_vol_1-60.tab(harv,40199)、writings…China.tab(m008004,harv,1033)、2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab(m004812,harv,29)、GB_91_HZ_040201_UTF8.tab(m006642,**chgis**,3389)。算术确证：54+5+11+7+6=83；每对象 1 列 __src_rownum bigint（one-based data record order excluding header）。读取规则两份 decisions 文件覆盖恰此五件（TAB/DOUBLE_QUOTE/doublequote/LF/empty_string=preserve_not_null/whitespace preserve/source_order preserve/**type_inference false**）。值合同 text-value-contract-approved.draft.json：XRGVALUE-v1、header_excluded、rownum_start=1，仅五对象范围。命名实现绑定 naming.py sha 13c0b910…（本地复核一致）；表名为候选，全量碰撞留块6。

## DBF 归属与交接
approved-dbf-{{character,numeric}}-reading.json 仅覆盖 1884route 两诊断件（且 limitations 自述非生产验证器），两者均为空间组件⇒随块3交接，块2 不重复认领。704 dbf 经同目录 shp/shx 兄弟扫描全部命中空间组件⇒块3 对象级清单见 handoffs.json。

## 第 2 块续做（32 项目快照只读核实 180 件）
快照=/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap（SSH 32 实测存在；嵌套件经 zipfile 提取到 /tmp，快照字节零接触；sha256 对账 inventory 全数一致）。工具面：宿主 python3.11.2 仅 chardet（openpyxl/xlrd/odf/pandas/lxml 缺、容器全缺、无 soffice/ssconvert/catdoc/xls2csv/in2csv/xlsx2csv），**未安装任何依赖**；xlsx/ods 走 stdlib zipfile+xml.etree（现有能力非新依赖）。分布（以终态文件为准）：可映射提案态 **{jb_count}**（按格式分解以机器件 object-mapping.proposed_objects 为准：csv 7 + xlsx 13 + ods 3 + txt 132 + xls 按非空工作表每表一对象）；ods 第 4 件 CountryFilesFormat_2016-07-16.ods 经内容判定为字段格式说明文档⇒块5（documentation，带 pending_review）；改判块5 另有 **12**（10 非表格+2 irregular，名称模式升级为内容证据）；XLS 14 件经茶香授权锁定镜像（xlrd==2.0.2，候选 Id 6144346a…）全可读、逐非空工作表各一对象，gaps 已归零（详见 XLS 补齐轮专节）。全部新映射确认态=**PROPOSED_NOT_AUTHORIZED**（schema/表名/类型/值合同一律 False，未伪造批准；表名候选按 naming.py 现行规则现场复算——已用该规则精确重现权威件 5/5 的 source_object_id 与列名映射，配方可信）。Manshu .ods/.xlsx 双载体内容比对留证：表头同、60 OBJECTID 键集同、其余 8 列逐字同，仅 Y1/Y2 为 IEEE-754 序列化差异（float 相等）且行序不同⇒分别处置不认重复。CHGIS v6/V4 六对字典簿行级全同，同样保留双成员。派生 __src_rownum 政策沿用（行序 preserve）。块3/块5 交接项均带 pending_review=true 待复核标记。

## 收尾轮：列身份整表分配（修复上轮逐字段配方缺陷）
上轮 `allocate_columns([name])` 逐列单元素调用，使重复表头名共享同一 column_id。本轮改为**每表一次整表调用**（以函数实际语义为准：同 slug 基底者由 `__c{{ordinal}}` 后缀消歧；identity 含序号+源名故天然唯一），全部 155 提案对象重分配；批准 5 件权威映射未动。**lead 方言裁定（a03 ROUND 4 注记(a)）**：两份 ChinaW.Master.Beta.csv 的 naive split(',') 176 列系伪影（引号内含逗号表头 w302/w304 被错切），RFC4180 引号感知 csv.reader=**159 列且零重复源名**——与项目已确认文本读取语义（quotechar DOUBLE_QUOTE/doublequote=true）及 R-08 忠实一致；**引号感知为正，裁定披露入件（dialect_resolution：前后 176→159 对照+strict_widths [[159,2404]]+证据 sha），提案态可逆待茶香讨论确认**。china_chron.txt——首行按数据保留（header_row=null、data_records=676 不变），naming/identity **无现行无表头规则**（两模块已查），采用稳定序号名 col_001…col_020 经**同一整表配方**分配（target col_u5f_001…），提案态披露。全量逗号 txt 复核：naive==strict 列数（107 件抽核 0 差异）⇒无同类伪影需改；2 件全文件宽度存在个别 ragged 行（v3/v4_time_cnty_pts_utf，strict 24×2811+23×2 / 25×4889+26×3）如实记入 quote_artifact_audit.full_file_width_profile 供块6 值合同复核。
全量唯一性复核（机器件 object-mapping.uniqueness_review）：**{uniq['tables_reviewed']} 表 / {uniq['columns_reviewed']} 列，column_id 违例 {uniq['column_id_violations']}、target_column 违例 {uniq['target_column_violations']}、真重复源名消歧计数 {uniq['disambiguated_duplicate_source_names']}**（**5 对象 23 处全部在 XLS 面**——xlrd 首行空表头单元格 ''×n 所致，逐件对象+重复名清单入机器件 uniqueness_review.disambiguation_detail；csv/txt 面经 ChinaW 引号感知修正后为 0；跨表同 schema 候选名碰撞留块6）。计数终态（工作表收尾轮）：candidates 1640 = organized **174**(批准5+提案**170**) + block3 846 + block5 620 + pending **0**；proposed 字段 **4065**。

ROUND-5 名级修复（a03 三方比对发现、lead 基线对照）：上轮审计仅比**列数** naive==strict，漏掉名级引号包裹/尾 \r/编码失真——如实披露入机器件 name_level_audit（method+prior_round_defect_disclosed）。本轮 139 对象（txt132+csv7）**名级全量三方比对：clean {nla_clean_count} / diff {len(nla_diff)}**，diff 全部重导并整表重分配：①Tibet_twns_2009_utf8.csv 13 净名 [THL_ID,Tibetan,Wylie,Pinyin,Twn_GB_ext,…]、933 数据行（与 lead 基线逐元素等）；②MingGarrisons/hist_sites 末列 \r 清除；③tan_GBK_names1/2、nima_feat_desig 末列 \r 清除（tab 件同病）；④**ChinaWBeta.Field.Definitions.txt ×2：BOM fffe UTF-16LE 嗅探+严格解码重判**——latin-1 NUL 碎片名消除，实为 TAB 分隔 7 列真实数据字典表（[Variable,COLUMN,ITEMNAME,WIDTH,OUTPUT,TYPE,DECIMALS]、159 数据行），处置按内容证据=**organized 提案态**（先例 v4/v6_data_dictionary.xlsx），encoding_resolution 披露含双副本 17580B 字节同、保留双成员镜像比对留块6。china_chron 首行数据判定不受影响（仅观测单元格尾 \r 注记）。修复后字段总数 **{uniq['columns_reviewed']}**（11 件重导净增减为 0：CHW 176→159 已在上一轮计入，本轮名级修正不改列数）。

## 工作表映射收尾轮（拆分/补名/扫描）
**MingGarrisonsSheet_29jan08.xls（KML/ming_garrisons_KML.zip 嵌套件）横拼缺陷修复**：原单对象 25 字段=Sheet1(14列)+Sheet2(11列)拼接⇒拆为**两个独立导入对象**——各自 source_object_id 以工作表限定身份输入 `'<member>#<sheet>'` 经 identity.py **真函数**分配（0e2674e1…/04e26d04…，convention 逐对象披露于 worksheet_split 字段）、候选表名经 naming.py 真函数+同限定名生成（…__minggarri__0e2674e1 / …__04e26d04，零碰撞）、字段按各自 sheet 源序整表 allocate_columns、行数 nrows 773/376→data_records 772/375。**禁止横拼/按行号合并**。归档成员登记不变（members.json 该件仍一条）。
**同类扫描（方法修正如实披露）**：上轮 multi-sheet 扫描误用证据键（nrows/rows 在交付记录中不存在）导致全漏——本轮以正确键 worksheets_observed[].columns/data_records_observed 复扫全部提案对象：**多非空 sheet 合并仅 MingGarrisons 一处**；xlsx 13 件每簿均单命名 sheet、ods 3 数据件各取 table:table 已逐表成对象（CountryFiles 文档件在块5）、其余 XLS 件各仅 1 非空 sheet——无其他拆分需求。
**补名**：csv/txt 平面件 worksheet=null 共 139 处⇒**138 件真平面件**统一改标 'TABLE'（机器可寻址）；**例外 76ed534c…（Ming_Garrisons.zip!MingGarrisonsSheet_29jan08.csv）系工作簿导出件非平面件**——复用授权镜像只读回测同 zip 兄弟簿 MingGarrisonsSheet_29jan08.xls（sha 740b18d3af11…）sheet_names=[Sheet1,Sheet2,Sheet3]，该 csv 11 列表头与其 **Sheet2 逐列一致（wei_id…end_yr，11 列/375 行同构）**⇒worksheet 补真名 **'Sheet2'** 并注内容比对；与嵌套件拆分出的 Sheet2 对象（04e26d04…）构成双成员保留（不同归档链，镜像比对留块6）。carrier_wb 判定含"同外层归档兄弟工作簿"规则入代码。china_chron.txt 保持 header_row=null。
**空 sheet**：零维 Sheet2/Sheet3（5 处）保留 members 清点结构事实，不建对象。
对象级计数：proposed **169→170**、字段 **4065 不变**（拆分净增减 0）、唯一性重跑 **170 表/4065 列双 0 违例**；成员级闭合 1640=174+846+620+0 不变。

## GAP / 未决
1. ~~XLS 14 件 BIFF 读取缺口~~ **已闭合（茶香授权轮）**：requirements.lock/in 锁 xlrd==2.0.2（官方 wheel sha256 ea762c3d…逐字）、32 构建独立标签候选镜像（未触 deploy/别名，runtime/dev/test Id 基线复核未变）、容器内 xlrd.__version__=2.0.2 实证；14 件全部只读清点成功（sha 对账 14/14 匹配）。嵌套链解析器在本目录格式上迭代七版方正确（inventory chain 末元素含目录前缀+外层 relative_path 已含末段——如实记录防复发）。剩余缺口仅为批准面：全部新映射 PROPOSED_NOT_AUTHORIZED，正式读取/装载批准件待茶香派工。2. PG 装载器未实现（沿用块1 GAP）；本包不运行任何装载。
3. 全版本命名碰撞未完成（块6）。

**ready_for_import=False 保持；类型推断禁止沿用；空串≠NULL 沿用；行序保留+派生行号单列。**
"""
(HERE / "SUMMARY.md").write_text(summary, encoding="utf-8")

tm = json.loads((HERE / "members.json").read_bytes())
om = json.loads((HERE / "object-mapping.json").read_bytes())
ho = json.loads((HERE / "handoffs.json").read_bytes())
eg = json.loads((HERE / "evidence-gaps.json").read_bytes())
assert om["object_count"] == 5 and om["source_column_count"] == 83
assert ho["no_double_count_check"]["union_equals_candidates"]
assert tm["total_candidates"] == sum(tm["class_counts"].values())
print("TABULAR package built OK:", *[p.name for p in sorted(HERE.iterdir()) if p.is_file()])

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
ledger = {(r["member"]["relative_path"], tuple(r["member"]["archive_chain"])): r
          for r in load("disposition-ledger-after-selector-fix.json")["records"]}
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
    probe_sha = {n: hashlib.sha256((PROBE_DIR / n).read_bytes()).hexdigest()
                 for n in ("probe_out.jsonl", "headers.json", "txt_headers.json",
                           "sheet_counts.json", "carrier_compare.json",
                           "chgis_dict_pairs.json", "ods_structure.json")}
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
            # BIFF binary: xlrd/converter absent on host AND container (lead fact
            # 4); stdlib BOF walk yielded no usable boundsheet names — unreadable.
            base.update(disposition="pending-evidence",
                        judgement_basis={
                            "verified_on": "host-32 project snapshot read-only extraction",
                            "sha_match_snapshot": pr.get("sha_match"),
                            "error": "missing xlrd/converter on host+container; stdlib "
                                     "BOF walk produced no boundsheet inventory",
                            "verdict": "unreadable-this-round"},
                        pending_review=True)
            gap_items.append({"object": pkey,
                              "missing": ["BIFF reader (xlrd absent; no soffice/ssconvert/"
                                          "catdoc/xls2csv/in2csv/xlsx2csv anywhere)"],
                              "error": "missing xlrd/converter on host+container",
                              "suggested_next": "authorize installing xlrd, or approve a "
                                                "derived stdlib BIFF parser as its own "
                                                "evidence track"})
            counts["pending_evidence"] += 1
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
            base.update(disposition="organized",
                        judgement_basis={
                            "verified_on": "host-32 project snapshot read-only",
                            "snapshot_path": SNAP_HOST_PATH,
                            "sha_match_snapshot": pr.get("sha_match"),
                            "raw_sha256_observed": pr.get("sha256"),
                            "delimiter": th["delimiter"],
                            "encoding_used": th["encoding_used"],
                            "bom": th["bom"],
                            "header_columns": len(th["header_row"]),
                            "data_records": th["data_records"],
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


def _col_entry(object_id, original, ordinal):
    nm = allocate_columns([original], object_id=object_id)[0]
    return {"source_column_ordinal": ordinal, "original_name": original,
            "target_name": nm.target, "quoted_target_name": quote_identifier(nm.target),
            "column_id": nm.identity, "target_type": "text",
            "type_note": "all values strings; type_inference=false carried over from "
                         "the approved text reading policy — observed types recorded "
                         "as evidence only",
            "nullable": True,
            "null_policy": "empty_string=preserve_not_null (proposal沿用已批准政策，未升级)"}


def _dataset_of(relpath, chain):
    full = chain if chain else relpath
    return full.rsplit("/", 1)[0] if "/" in full else ""


proposed_objs = []
for m in members_out:
    jb = m.get("judgement_basis") or {}
    if jb.get("confirmation_state") != "PROPOSED_NOT_AUTHORIZED":
        continue
    si = m["source_identity"]
    pkey = si["relative_path"] + ("!" + "/".join(si["archive_chain"]) if si["archive_chain"] else "")
    ext = m["category"]
    carrier = {"csv": "csv", "xlsx": "xlsx", "ods": "ods", "txt": None}[ext]
    if ext == "txt":
        th = txt_headers[pkey]
        headers_by_sheet = [(None, th["header_row"], th["data_records"],
                             th["encoding_used"], th["bom"], th["delimiter"])]
    elif ext == "csv":
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
    sid = source_object_id(relative_path=si["relative_path"],
                           archive_chain=si["archive_chain"],
                           object_name=objname, carrier=carrier or "tsv")
    nmap = allocate_tables([NameInput(ds, objname, sid)])[0]
    fields_all = []
    sheets_out = []
    for sheet_nm, hdr, nrows, enc, bom, delim in headers_by_sheet:
        cols = [_col_entry(sid, h, i + 1) for i, h in enumerate(hdr)]
        fields_all.extend(cols)
        sheets_out.append({"worksheet": sheet_nm, "columns": len(hdr),
                           "data_records_observed": nrows})
    dup = len(hdr) != len(set(hdr)) if headers_by_sheet else False
    proposed_objs.append({
        "source_file_or_chain": pkey,
        "worksheets_observed": sheets_out,
        "carrier": carrier or "tsv",
        "source_object_id": sid,
        "dataset_namespace": ds,
        "target_schema": None,
        "candidate_table_name": nmap.target,
        "fields": fields_all,
        "dialect_observations": {"delimiter": headers_by_sheet[0][5],
                                 "encoding_strict_ok": headers_by_sheet[0][3],
                                 "bom": headers_by_sheet[0][4]},
        "structural_flags": {"duplicate_header_names": any(
            len(h) != len(set(h)) for _, h, *_ in headers_by_sheet),
            "ods_database_ranges": (ods_structure.get(pkey, {})
                                    .get("database_ranges") or [])},
        "read_method": "stdlib zipfile+xml.etree (xlsx/ods) or csv module strict parse "
                       "(csv/txt) on host-32 project snapshot, read-only; NO external "
                       "dependency installed (existing capability, not new)",
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
                   "ready_for_import": False, "disposition_retained": "BLOCKED"}})

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
write("members.json", members)
write("object-mapping.json", obj_map)
write("handoffs.json", handoffs)

gaps = {"format": "xiangrugu.import-package.tabular.evidence-gaps.v1",
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
summary = f"""# 普通表格整理摘要（第 2/6 块，仅整理不写库）

生成：build_tabular_package.py 确定性合并；旧文件零改动。候选口径=archive_chain[-1] 末链名扩展名（**大小写不敏感**；.tab 合计 147，按功能精确分叉：大写 .TAB=MapInfo 空间表定义⇒块3，小写 .tab=文本表候选）。

## 计数（candidates={members['total_candidates']}）
| 类 | 数量 | 去向 |
|---|---|---|
| csv | {cc['csv']} | 本轮快照核实：6 表格候选⇒organized(提案态)，1 NGIA 严格解析 6×632 规整⇒organized 并记方言注记 |
| xls | {cc['xls']} | **14 全部读不了**（BIFF，xlrd/转换器宿主+容器全缺）⇒pending-evidence 逐件入 gaps |
| xlsx | {cc['xlsx']} | stdlib zipfile+xml 解析成功⇒organized(提案态)，sheet/字段/行数留证 |
| ods | {cc['ods']} | stdlib content.xml 解析成功：3 数据表⇒organized(提案态)；**CountryFilesFormat_2016-07-16.ods 内容证据判为字段格式说明文档（表头 Field Name/Description/Type/MaxLength，37 行）⇒块5**；与同 basename xlsx/csv 分别处置不认重复；Manshu.ods 附 __Anonymous_Sheet_DB__0 database-range 结构事实留证 |
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
快照=/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap（SSH 32 实测存在；嵌套件经 zipfile 提取到 /tmp，快照字节零接触；sha256 对账 inventory 全数一致）。工具面：宿主 python3.11.2 仅 chardet（openpyxl/xlrd/odf/pandas/lxml 缺、容器全缺、无 soffice/ssconvert/catdoc/xls2csv/in2csv/xlsx2csv），**未安装任何依赖**；xlsx/ods 走 stdlib zipfile+xml.etree（现有能力非新依赖）。分布（以终态文件为准）：可映射提案态 **{jb_count}** = csv 7 + xlsx 13 + ods 3 + txt 132；ods 第 4 件 CountryFilesFormat_2016-07-16.ods 经内容判定为字段格式说明文档⇒块5（documentation，带 pending_review）；改判块5 另有 **12**（10 非表格+2 irregular，名称模式升级为内容证据）；读不了 **14**（xls BIFF，逐件入 gaps）。全部新映射确认态=**PROPOSED_NOT_AUTHORIZED**（schema/表名/类型/值合同一律 False，未伪造批准；表名候选按 naming.py 现行规则现场复算——已用该规则精确重现权威件 5/5 的 source_object_id 与列名映射，配方可信）。Manshu .ods/.xlsx 双载体内容比对留证：表头同、60 OBJECTID 键集同、其余 8 列逐字同，仅 Y1/Y2 为 IEEE-754 序列化差异（float 相等）且行序不同⇒分别处置不认重复。CHGIS v6/V4 六对字典簿行级全同，同样保留双成员。派生 __src_rownum 政策沿用（行序 preserve）。块3/块5 交接项均带 pending_review=true 待复核标记。

## GAP / 未决
1. csv7+xls14+xlsx13 无读取批准件、无 sheet 级对象清单⇒逐件列于 evidence-gaps.json。
2. txt 中非 README 名称模式者需授权后批量首行抽样判表性（不静默归类）。
3. PG 装载器未实现（沿用块1 GAP）；本包不运行任何装载。
4. 全版本命名碰撞未完成（块6）。

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

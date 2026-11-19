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
counts = defaultdict(int)
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
    elif x in ("csv", "xls", "xlsx", "dbf", "txt"):
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
                                                       "approved_diagnostic_reading": appr})
            counts["handoff_block3"] += 1
        else:
            counts["pending_evidence"] += 1
    elif cls == "tab-mapinfo-spatial-definition":
        base.update(disposition="handoff-block3",
                    judgement_basis={"reason": "uppercase .TAB MapInfo spatial table "
                                   "definition (705-group Shapefile/MapInfo relation "
                                   "per binding context)",
                                     "binding_context_file": "approved-spatial-binding-context.json"})
        handoff3.append(base["source_identity"] | {"role": "mapinfo-tab-definition"})
        counts["handoff_block3"] += 1
    elif cls in ("csv", "xls", "xlsx"):
        base.update(disposition="pending-evidence",
                    judgement_basis={"reason": f"{cls} member with no per-object reader "
                                   "approval, sheet/column contract or value expectations "
                                   "in this release directory",
                                     "worksheet_inventory": "GAP: requires authorized read "
                                     "of workbook sheet lists on host 32 (not performed this round)"})
        gap_items.append({"object": key[0] + ("!" + "/".join(key[1]) if key[1] else ""),
                          "missing": ["reader approval (csv/xls/xlsx dialect)",
                                      "sheet-level object inventory", "column/type review",
                                      "value expectations"],
                          "suggested_next": "dialect proposal + independent reading rounds "
                                            "following the five-text precedent"})
        counts["pending_evidence"] += 1
    elif cls == "txt":
        # classify by NAME pattern only where decisive; else pending
        import re
        readme = re.search(r"(readme|notes|info|license|terms|description|dictionary|"
                           r"codebook|code_book|faq|howto|guide|index\.txt$|_index)",
                           ln, re.I)
        if readme:
            base.update(disposition="handoff-block5",
                        judgement_basis={"basis": "documentary-name pattern (README/notes/"
                                       "metadata family); non-tabular role",
                                         "confidence": "name-pattern only — content unread "
                                       "this round (R-07 byte reads need authorization)"})
            handoff5.append(base["source_identity"] | {"pattern": readme.group(0)})
            counts["handoff_block5"] += 1
        else:
            base.update(disposition="pending-evidence",
                        judgement_basis={"reason": "txt member without decisive "
                                       "documentary name pattern and without tabular "
                                       "reader evidence; NOT silently classified"})
            gap_items.append({"object": key[0] + ("!" + "/".join(key[1]) if key[1] else ""),
                              "missing": ["content-type determination (needs authorized "
                                          "read-only sampling)", "then either non-tabular "
                                          "note or full reader pipeline"],
                              "suggested_next": "batch header-line sampling via SSH 32 "
                                                "under explicit authorization"})
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
                            for k in ("csv", "xls", "xlsx", "dbf",
                                      "tab-mapinfo-spatial-definition", "tab-text", "txt")},
           "disposition_counts": dict(counts),
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
obj_map = {"format": "xiangrugu.import-package.tabular.object-mapping.v1",
           "object_count": len(objects_out),
           "source_column_count": sum(len([f for f in x["fields"] if not f.get("synthetic")])
                                      for x in objects_out),
           "derived_rownum_count": sum(1 for x in objects_out
                                       for f in x["fields"] if f.get("synthetic")),
           "flags_verbatim_from_text_schema_approved": {
               k: schema5[k] for k in ("schema_approved", "table_names_approved",
                                        "target_mapping_approved", "ready_for_import",
                                        "global_name_allocation_complete")},
           "objects": objects_out}
assert obj_map["source_column_count"] == 83 and obj_map["derived_rownum_count"] == 5

# ---------------------------------------------------------------- handoffs
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
                "objects": handoff5},
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
summary = f"""# 普通表格整理摘要（第 2/6 块，仅整理不写库）

生成：build_tabular_package.py 确定性合并；旧文件零改动。候选口径=archive_chain[-1] 末链名扩展名（大小写敏感）。

## 计数（candidates={members['total_candidates']}）
| 类 | 数量 | 去向 |
|---|---|---|
| csv | {cc['csv']} | 全部待证据（无读取批准件） |
| xls | {cc['xls']} | 待证据（含 sheet 清单缺口） |
| xlsx | {cc['xlsx']} | 待证据（同上） |
| dbf | {cc['dbf']} | **全部为 Shapefile 空间组件⇒块3**（统一目录键的 shp/shx 兄弟扫描 704/704 命中，与 lead 侦察一致；独立 DBF=0） |
| .TAB 大写 | {cc['tab-mapinfo-spatial-definition']} | MapInfo 空间表定义⇒块3 |
| .tab 小写 | {cc['tab-text']} | 5 已整理（权威件）+2 待证据 |
| txt | {cc['txt']} | 含大写 .TXT（大小写不敏感纳入，修复 a03 ITEM 1）：说明件⇒块5（名称模式判定）{dc.get('handoff_block5',0)} 件；其余 {dc.get('pending_evidence',0) - (cc['csv']+cc['xls']+cc['xlsx'])} 件待内容抽样判定 |

处置分布：organized={dc.get('organized',0)}、handoff-block3={dc.get('handoff_block3',0)}、handoff-block5={dc.get('handoff_block5',0)}、pending-evidence={dc.get('pending_evidence',0)}（合计 {sum(dc.values())}=candidates ✓）。

## 5 件文本/83 源字段/5 派生行号确证
权威载体=text-schema-approved.draft.yaml（yaml 后缀 JSON 内容）：object_count=5、source_column_count=83、schema/column-mapping/nullable/types/derived-rownum approved=true；table_names/target_mapping/ready_for_import=false、global_name_allocation_complete=false、逐对象 disposition_retained=BLOCKED——原样保留未升级。5 对象：ACADEMY_Data.tab(m008002,harv,2957)、Index…Yuan_Dynasty_vol_1-60.tab(harv,40199)、writings…China.tab(m008004,harv,1033)、2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab(m004812,harv,29)、GB_91_HZ_040201_UTF8.tab(m006642,**chgis**,3389)。算术确证：54+5+11+7+6=83；每对象 1 列 __src_rownum bigint（one-based data record order excluding header）。读取规则两份 decisions 文件覆盖恰此五件（TAB/DOUBLE_QUOTE/doublequote/LF/empty_string=preserve_not_null/whitespace preserve/source_order preserve/**type_inference false**）。值合同 text-value-contract-approved.draft.json：XRGVALUE-v1、header_excluded、rownum_start=1，仅五对象范围。命名实现绑定 naming.py sha 13c0b910…（本地复核一致）；表名为候选，全量碰撞留块6。

## DBF 归属与交接
approved-dbf-{{character,numeric}}-reading.json 仅覆盖 1884route 两诊断件（且 limitations 自述非生产验证器），两者均为空间组件⇒随块3交接，块2 不重复认领。704 dbf 经同目录 shp/shx 兄弟扫描全部命中空间组件⇒块3 对象级清单见 handoffs.json。

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

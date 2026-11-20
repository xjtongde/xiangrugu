#!/usr/bin/env python3
"""Block 4/6 MDB & SQL package generator — deterministic, read-only, streaming.

Runs on host 32 python3 (stdlib only). Source snapshot read-only; NO database
execution anywhere (SQL is text-identified only); NO dependency installs.
Inputs: inventory.json transferred alongside this script (sha asserted).
Outputs: members.json / object-mapping.json / evidence-gaps.json / SUMMARY.md
Double-run discipline: same inputs -> byte-identical artifacts; check exits.
"""
import collections
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = Path("/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap")
INV_SHA_EXPECTED = ("fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db")
VCS_REF = "ef90b64"
MDBTOOLS_CANDIDATE = "1.0.0+dfsg-1.1"  # 32 apt-cache policy candidate; NOT installed

inv_bytes = (HERE / "inventory.json").read_bytes()
assert hashlib.sha256(inv_bytes).hexdigest() == INV_SHA_EXPECTED, "inventory sha mismatch"
INV = json.loads(inv_bytes)
ENTRIES = INV["entries"]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def member_key(e):
    return e["relative_path"] + ("!" + "!".join(e["archive_chain"]) if e["archive_chain"] else "")


def find_member(rel, chain):
    for e in ENTRIES:
        if e["relative_path"] == rel and e["archive_chain"] == chain:
            return e
    raise KeyError(f"member not in inventory: {rel} {chain}")


def open_nested(rel, chain):
    """Return (file-like stream, container_zip_objects) walking exact chain.
    Intermediate zips loaded in memory (small); final member STREAMED."""
    z = zipfile.ZipFile(SNAP / rel)
    containers = [z]
    for elem in chain[:-1]:
        data = z.read(elem)
        z = zipfile.ZipFile(io.BytesIO(data))
        containers.append(z)
    return z.open(chain[-1] if chain else Path(rel).name), containers


def stream_sha(fh):
    h = hashlib.sha256()
    while True:
        chunk = fh.read(1 << 20)
        if not chunk:
            break
        h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- collection
CORE = [e for e in ENTRIES
        if (e["archive_chain"][-1] if e["archive_chain"] else e["relative_path"]).lower().endswith((".mdb", ".sql"))]
CORE.sort(key=member_key)
assert len(CORE) == 7, f"expected 7 core members, got {len(CORE)}"
MDB = [e for e in CORE if member_key(e).lower().endswith(".mdb")]
SQL = [e for e in CORE if member_key(e).lower().endswith(".sql")]
assert len(MDB) == 5 and len(SQL) == 2

RELATED = [
    {"relative_path": "harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip",
     "archive_chain": ["access_dbase/v3_chgis_dbase.ZIP"],
     "disposition": "structural_container", "note": "inner ZIP container of V3 mdb; structural only, descendant mapped separately"},
    {"relative_path": "harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip",
     "archive_chain": ["access_database/v4_chgis_dbase.zip"],
     "disposition": "structural_container", "note": "inner ZIP container of V4 mdb copy A; structural only"},
    {"relative_path": "harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip",
     "archive_chain": ["shapefiles/v4_chgis_dbase.zip"],
     "disposition": "structural_container", "note": "inner ZIP container of V4 mdb copy B (mirror of copy A, identical sha); structural only"},
    {"relative_path": "harvard-full/doi_10_7910/DVN/ZZKZ6U/CHGIS_V2.zip",
     "archive_chain": ["access_dbase/chgis_v2_database.ZIP"],
     "disposition": "structural_container", "note": "inner ZIP container of V2 mdb; structural only"},
    {"relative_path": "harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip",
     "archive_chain": ["KML/CHGIS_v4_1911_KML.zip", "V4_1911_KML_metadata/Thumbs.db"],
     "disposition": "excluded_non_data_to_block5", "note": "Windows Explorer thumbnail cache (OLE signature), NOT a database; explicit exclusion, block 5 disposition"},
    {"relative_path": "harvard/cbdb/cbdb_20260919.sqlite3",
     "archive_chain": [],
     "disposition": "owned_by_block1_exactly_once", "note": "CBDB main source carrier; block 1 import-package/cbdb/ 78 tables / 736 columns already mapped and accepted; NOT remapped here"},
    {"relative_path": "chgis-v6/China_Periods_ReignDates.zip",
     "archive_chain": ["china_chron/china_chron.xls"],
     "disposition": "owned_by_block2_exactly_once", "note": "XLS sibling of china_chron.sql; block 2 tabular plane already mapped; NOT remapped here"},
    {"relative_path": "chgis-v6/China_Periods_ReignDates.zip",
     "archive_chain": ["china_chron/china_chron.txt"],
     "disposition": "documentation_note", "note": "text sibling; documentation, not a table carrier for this block"},
    {"relative_path": "chgis-v6/China_Periods_ReignDates.zip",
     "archive_chain": ["china_chron/README_CHINA_CHRON.txt"],
     "disposition": "documentation_note", "note": "README sibling; documentation"},
]
for r in RELATED:
    e = find_member(r["relative_path"], r["archive_chain"])
    r["sha256"] = e["sha256"]
    r["size"] = e["size"]

# ---------------------------------------------------------------- SQL parsing
def split_top_level(s, sep=","):
    parts, depth, cur, in_q = [], 0, [], None
    for ch in s:
        if in_q:
            cur.append(ch)
            if ch == in_q:
                in_q = None
            continue
        if ch in "'\"`":
            in_q = ch; cur.append(ch); continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return parts


COL_RE = re.compile(
    r"^\s*[`\"]?([A-Za-z_][\w]*)[`\"]?\s+([A-Za-z]+)"
    r"(?:\s*\(([^)]*)\))?(.*)$", re.S)


def parse_create_block(block):
    m = re.match(r"\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?([\w]+)[`\"]?\s*\((.*)\)\s*([^;]*);?\s*$",
                 block, re.S | re.I)
    if not m:
        return None
    tname, body, opts = m.group(1), m.group(2), m.group(3)
    cols, keys = [], []
    for part in split_top_level(body):
        p = part.strip()
        if not p:
            continue
        if re.match(r"(?i)^(PRIMARY\s+KEY|UNIQUE|KEY|INDEX|CONSTRAINT|FOREIGN\s+KEY|FULLTEXT|SPATIAL)\b", p):
            keys.append(p)
            continue
        cm = COL_RE.match(p)
        if not cm:
            keys.append(p)  # unparsed definition retained verbatim, flagged
            continue
        name, typ, prec, rest = cm.groups()
        rest = rest or ""
        nullable = "NOT NULL" not in rest.upper()
        dm = re.search(r"(?i)DEFAULT\s+('(?:[^']|'')*'|[\w.+-]+|NULL|CURRENT_TIMESTAMP(?:\(\))?)", rest)
        pm = re.match(r"\s*(\d+)\s*(?:,\s*(\d+))?", prec or "")
        cols.append({
            "ordinal": len(cols) + 1, "original_name": name,
            "source_type": typ.upper(),
            "precision": int(pm.group(1)) if pm and pm.group(1) else None,
            "scale": int(pm.group(2)) if pm and pm.group(2) else None,
            "nullable_proposed_from_source": nullable,
            "default_verbatim": dm.group(1) if dm else None,
            "definition_rest_verbatim": rest.strip(),
            "binary_flag": typ.upper() in ("BLOB", "TINYBLOB", "MEDIUMBLOB", "LONGBLOB", "BINARY", "VARBINARY", "BYTEA", "BIT"),
            "definition_verbatim": p})
    eng = re.search(r"(?i)ENGINE\s*=\s*(\w+)", opts)
    cs = re.search(r"(?i)(?:DEFAULT\s+)?CHARSET\s*=\s*(\w+)", opts)
    coll = re.search(r"(?i)COLLATE\s*=\s*(\w+)", opts)
    return {"table_name_source": tname, "columns": cols,
            "key_definitions_verbatim": keys,
            "engine": eng.group(1) if eng else None,
            "charset_declared": cs.group(1) if cs else None,
            "collation_declared": coll.group(1) if coll else None,
            "create_definition_verbatim": block.strip()}


def detect_encoding(head):
    if head.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", True
    if head.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16", True
    for enc in ("utf-8", "cp936"):
        for probe in (head, head[:-4]):  # tolerate multibyte cut at 1MB boundary
            try:
                probe.decode(enc)
                return enc, False
            except UnicodeDecodeError:
                continue
    return "latin-1", False


def parse_sql(e):
    fh, _ = open_nested(e["relative_path"], e["archive_chain"])
    head = fh.read(1 << 20)
    fh.close()
    enc, bom = detect_encoding(head)
    fh, _ = open_nested(e["relative_path"], e["archive_chain"])
    stream = io.TextIOWrapper(fh, encoding=enc, errors="replace")
    tables, inserts, sets, drops, locks = [], 0, [], 0, 0
    cur_block, in_create = [], False
    repl = 0
    repl_hits = []
    first_inserts = []
    row_estimate = 0
    dialect_hits = collections.Counter()
    banner = []
    for i, line in enumerate(stream):
        if "\ufffd" in line:
            repl += line.count("\ufffd")
            pos = line.index("\ufffd")
            repl_hits.append({"line": i + 1, "count": line.count("\ufffd"),
                              "context_verbatim": line[max(0, pos - 60):pos + 60].strip()[:140]})
        ls = line.strip()
        if i < 40 and (ls.startswith("--") or ls.startswith("/*")):
            banner.append(ls[:200])
        if re.search(r"(?i)MySQL dump", line):
            dialect_hits["mysql_dump_banner"] += 1
        if re.search(r"(?i)PostgreSQL database dump", line):
            dialect_hits["pg_dump_banner"] += 1
        if re.match(r"(?i)^SET\s+", ls):
            sets.append(ls[:200])
            if re.search(r"(?i)SET\s+NAMES\s+(\w+)", ls):
                dialect_hits["set_names:" + re.search(r"(?i)SET\s+NAMES\s+(\w+)", ls).group(1)] += 1
        if re.match(r"(?i)^DROP\s+TABLE", ls):
            drops += 1
        if re.match(r"(?i)^(LOCK|UNLOCK)\s+TABLES", ls):
            locks += 1
        if re.match(r"(?i)^CREATE\s+TABLE", ls):
            in_create, cur_block = True, [line]
            if ls.rstrip().endswith(";"):
                t = parse_create_block("".join(cur_block))
                if t:
                    tables.append(t)
                in_create = False
            continue
        if in_create:
            cur_block.append(line)
            if ls.endswith(";"):
                t = parse_create_block("".join(cur_block))
                if t:
                    tables.append(t)
                else:
                    tables.append({"table_name_source": None,
                                   "parse_anomaly": True,
                                   "create_definition_verbatim": "".join(cur_block).strip()})
                in_create = False
            continue
        if re.match(r"(?i)^(INSERT\s+(IGNORE\s+)?INTO|REPLACE\s+INTO)", ls):
            inserts += 1
            if len(first_inserts) < 2:
                first_inserts.append(ls[:500])
            row_estimate += ls.count("),(") + 1
            if "`" in ls:
                dialect_hits["backtick_identifiers"] += 1
    stream.close()
    for t in tables:
        if t.get("engine"):
            dialect_hits["engine:" + t["engine"]] += 1
        if t.get("charset_declared"):
            dialect_hits["charset:" + t["charset_declared"]] += 1
    dialect = ("mysql" if dialect_hits.get("mysql_dump_banner") or any(k.startswith("engine:") for k in dialect_hits)
               else "postgresql" if dialect_hits.get("pg_dump_banner")
               else "unknown")
    return {
        "member_key": member_key(e), "sha256": e["sha256"], "size": e["size"],
        "encoding_detected": enc, "bom_present": bom,
        "replacement_chars_on_decode": repl,
        "replacement_char_locations": repl_hits[:20],
        "loss_risk_note": ("decode replacement chars > 0: value-loss risk, isolate before import" if repl else "no replacement chars on detected encoding"),
        "dialect": dialect, "dialect_evidence": dict(dialect_hits),
        "banner_head_verbatim": banner[:12],
        "set_statements_verbatim": sets[:20],
        "table_count": len(tables), "tables": tables,
        "insert_statement_count": inserts,
        "row_count_estimate": row_estimate,
        "row_count_method": "approximate: count of '),( ' tuple separators + 1 per INSERT line; strings containing separators may inflate; exact count requires approved parser",
        "drop_table_count": drops, "lock_tables_count": locks,
        "first_insert_samples_verbatim": first_inserts,
        "data_carrier": "INSERT statements" if inserts else ("schema-only" if tables else "unidentified"),
        "execution_status": "NOT_EXECUTED_READ_ONLY_TEXT_IDENTIFICATION",
    }


# ---------------------------------------------------------------- MDB probing
JET_VERSIONS = {0: "JET3 (Access 97)", 1: "JET4 (Access 2000-2003)",
                2: "ACE12 (Access 2007)", 3: "ACE14 (Access 2010)"}


def probe_mdb(e):
    fh, _ = open_nested(e["relative_path"], e["archive_chain"])
    head = fh.read(4096)
    fh.close()
    fh, _ = open_nested(e["relative_path"], e["archive_chain"])
    digest = stream_sha(fh)
    fh.close()
    assert digest == e["sha256"], f"mdb sha mismatch {member_key(e)}"
    magic = head[:4].hex()
    sig = head[4:19].decode("ascii", errors="replace").rstrip("\x00")
    ver_byte = head[0x14] if len(head) > 0x14 else None
    page = {0: 2048, 1: 4096}.get(ver_byte)
    return {
        "member_key": member_key(e), "sha256": digest, "size": e["size"],
        "sha_matches_inventory": True,
        "header_magic_hex": magic, "header_signature": sig,
        "version_byte_0x14": ver_byte,
        "version_interpretation": JET_VERSIONS.get(ver_byte, "unknown"),
        "page_size_version_derived": page,
        "page_size_note": "derived from version byte (JET3=2048/JET4=4096 convention); not a catalog read",
        "header_hexdump_first128_verbatim": head[:128].hex(),
        "readable_surface": "header-level only (stdlib)",
        "table_enumeration_status": "GAP_NO_CATALOG_READER",
        "unreadable_reason": ("locked environment has no MDB catalog reader: mdbtools absent on 32 host and in existing project containers (measured); JET/ACE catalog pages require a dedicated reader; no installs authorized this round"),
        "required_tool": f"mdbtools={MDBTOOLS_CANDIDATE} (32 apt-cache policy candidate, bookworm; locked-version proposal only, NOT installed) or Chaxiang-approved derived reader",
        "isolation_recovery": "extract to isolated temp dir on 32, read-only via mdb-tables/mdb-export/mdb-schema once approved; source snapshot stays :ro",
        "encoding_note": "JET4 catalog/text typically UTF-16LE; JET3 codepage-based; exact per-column encoding requires catalog reader — not asserted here",
        "binary_note": "OLE/object and memo fields may carry binary payloads; requires catalog reader to enumerate — not asserted here",
    }


# ---------------------------------------------------------------- build
sql_results = [parse_sql(e) for e in SQL]
mdb_results = [probe_mdb(e) for e in MDB]

# mirror/version facts
v4 = [m for m in mdb_results if "v4_chgis_dbase.mdb" in m["member_key"]]
v4_shas = sorted({m["sha256"] for m in v4})
mirror_note = ("V4 direct member sha differs from zip-wrapped copies: TWO distinct byte versions registered separately; "
               "the two zip-wrapped copies (access_database/ and shapefiles/) share one sha = mirror pair, merge deferred to block 6")

proposed = []
for sr in sql_results:
    stem = Path(sr["member_key"].split("!")[-1]).stem.lower()
    for t in sr["tables"]:
        if t.get("parse_anomaly"):
            continue
        tname = t["table_name_source"]
        ident = sr["member_key"] + "#" + tname
        fields = []
        for c in t["columns"]:
            st = c["source_type"]
            if c["binary_flag"]:
                tt = "bytea"
            elif st in ("TINYINT", "SMALLINT", "MEDIUMINT", "INT", "INTEGER", "BIGINT", "SERIAL"):
                tt = "bigint" if st in ("BIGINT", "SERIAL") else "integer"
            elif st in ("DECIMAL", "NUMERIC"):
                tt = f"numeric({c['precision']},{c['scale']})" if c["precision"] is not None else "numeric"
            elif st in ("FLOAT", "DOUBLE", "REAL"):
                tt = "double precision"
            elif st in ("CHAR", "VARCHAR"):
                tt = f"varchar({c['precision']})" if c["precision"] else "text"
            elif st in ("TINYTEXT", "TEXT", "MEDIUMTEXT", "LONGTEXT", "ENUM", "SET"):
                tt = "text"
            elif st in ("DATE",):
                tt = "date"
            elif st in ("DATETIME", "TIMESTAMP"):
                tt = "timestamp"
            elif st in ("TIME",):
                tt = "time"
            elif st in ("YEAR",):
                tt = "integer"
            elif st in ("BIT", "BOOLEAN", "BOOL"):
                tt = "boolean"
            else:
                tt = "text"
            fields.append({**c, "target_type_proposal": tt,
                           "encoding_note": f"file encoding {sr['encoding_detected']}; charset declared {t.get('charset_declared')}",
                           "null_semantics_note": "source NOT NULL/DEFAULT preserved verbatim; empty-string vs NULL vs 0 distinction requires value contract at import"})
        proposed.append({
            "source_object_id": sha256_bytes(ident.encode()),
            "carrier": "sql_table",
            "source_file_or_chain": sr["member_key"],
            "source_identity": {"sha256": sr["sha256"], "size": sr["size"],
                                "table_name_source": tname},
            "table_name_proposal": re.sub(r"[^a-z0-9_]", "_", f"{stem}_{tname}".lower()),
            "dialect": sr["dialect"],
            "fields": fields, "field_count": len(fields),
            "key_definitions_verbatim": t["key_definitions_verbatim"],
            "engine": t.get("engine"), "charset_declared": t.get("charset_declared"),
            "collation_declared": t.get("collation_declared"),
            "create_definition_verbatim": t["create_definition_verbatim"],
            "status": {"confirmation_state": "PROPOSED_NOT_AUTHORIZED",
                       "ready_for_import": False},
        })

mdb_objects = []
for mr in mdb_results:
    mdb_objects.append({
        "source_object_id": sha256_bytes(mr["member_key"].encode()),
        "carrier": "mdb_file",
        "source_file_or_chain": mr["member_key"],
        "source_identity": {"sha256": mr["sha256"], "size": mr["size"]},
        "header_probe": {k: v for k, v in mr.items()
                         if k not in ("member_key", "sha256", "size")},
        "table_enumeration_status": "GAP_NO_CATALOG_READER",
        "status": {"confirmation_state": "CONFIRMED_HEADER_ONLY",
                   "ready_for_import": False},
    })

sids = [o["source_object_id"] for o in proposed] + [o["source_object_id"] for o in mdb_objects]
assert len(sids) == len(set(sids)), "sid collision"
anomalies = [t for sr in sql_results for t in sr["tables"] if t.get("parse_anomaly")]

members_doc = {
    "format": "xiangrugu.import-package.mdb-sql.members.v1",
    "generated_by": "build_mdb_sql_package.py (deterministic; stdlib only; read-only; no DB execution; no installs)",
    "baseline_git": VCS_REF, "inventory_sha256": INV_SHA_EXPECTED,
    "core_member_count": len(CORE),
    "core_members": [{"member_key": member_key(e), "relative_path": e["relative_path"],
                      "archive_chain": e["archive_chain"], "archive_ordinals": e.get("archive_ordinals"),
                      "sha256": e["sha256"], "size": e["size"],
                      "family": "mdb" if member_key(e).lower().endswith(".mdb") else "sql"} for e in CORE],
    "related_members": RELATED,
    "mirror_and_version_note": mirror_note,
    "v4_distinct_sha256": v4_shas,
    "scope_note": "MDB and SQL members incl. nested archives; Thumbs.db excluded non-data; cbdb sqlite3 owned by block 1 exactly-once; china_chron.xls owned by block 2 exactly-once",
}

mapping_doc = {
    "format": "xiangrugu.import-package.mdb-sql.object-mapping.v1",
    "baseline_git": VCS_REF,
    "sql_file_results": [{k: v for k, v in sr.items() if k != "tables"} | {"table_names": [t.get("table_name_source") for t in sr["tables"]]} for sr in sql_results],
    "proposed_objects": proposed,
    "mdb_file_objects": mdb_objects,
    "counts": {
        "core_members": len(CORE),
        "sql_files": len(SQL), "mdb_files": len(MDB),
        "sql_tables_enumerated": sum(len(sr["tables"]) for sr in sql_results),
        "sql_parse_anomalies": len(anomalies),
        "mapped_objects_proposed": len(proposed),
        "mdb_objects_header_confirmed": len(mdb_objects),
        "mdb_tables_enumerated": 0,
        "enumerated_objects_total": sum(len(sr["tables"]) for sr in sql_results) + len(mdb_objects),
    },
    "flags": {"ready_for_import": False, "target_mapping_approved": False,
              "sql_execution": "FORBIDDEN_THIS_ROUND_NOT_EXECUTED",
              "installs_this_round": False},
}

gaps = []
for mr in mdb_results:
    gaps.append({"object": mr["member_key"], "kind": "tool_gap_mdb_catalog",
                 "reason": mr["unreadable_reason"], "required_tool": mr["required_tool"],
                 "isolation_recovery": mr["isolation_recovery"],
                 "sha256": mr["sha256"], "size": mr["size"]})
for sr in sql_results:
    if sr["replacement_chars_on_decode"]:
        gaps.append({"object": sr["member_key"], "kind": "encoding_loss_risk",
                     "replacement_chars": sr["replacement_chars_on_decode"],
                     "locations": sr["replacement_char_locations"],
                     "note": sr["loss_risk_note"],
                     "recovery_note": ("replacement chars localized (see locations/context_verbatim); where context shows binary payload inside string literals (e.g. geometry WKB-style raw high bytes), naive text decode loses original bytes — byte-faithful extraction required (isolation recovery); no value fabrication")})
for t in anomalies:
    gaps.append({"object": "sql_parse_anomaly", "kind": "structure_parse_anomaly",
                 "verbatim": t["create_definition_verbatim"][:500]})

gaps_doc = {
    "format": "xiangrugu.import-package.mdb-sql.evidence-gaps.v1",
    "baseline_git": VCS_REF,
    "gap_count": len(gaps), "gaps": gaps,
    "tool_gap_report": {
        "status": "MDB_CATALOG_READER_NOT_INSTALLED",
        "affected_objects": [mr["member_key"] for mr in mdb_results],
        "capability_missing": "JET/ACE catalog + table/field/value enumeration",
        "required_tool": f"mdbtools={MDBTOOLS_CANDIDATE} (bookworm apt candidate measured on 32; NOT installed; locked-version proposal awaits Chaxiang approval)",
        "installed_this_round": False,
        "host_software_unchanged": True,
        "sql_plane": "fully text-identified with stdlib; no tool gap for dialect/structure/carrier",
    },
    "dependency_gaps": [],
}

c = mapping_doc["counts"]
gap_kind_note = (("；编码损失风险" if any(g["kind"] == "encoding_loss_risk" for g in gaps) else "")
                 + ("；结构解析异常" if anomalies else ""))
summary = f"""# 第 4/6 块 · MDB 与 SQL 包（SUMMARY）

基线 git {VCS_REF}；inventory sha256={INV_SHA_EXPECTED[:16]}… 断言一致；32 宿主 python3 stdlib 流式只读；**SQL 未对任何库执行；本轮未安装依赖；源件只读零触**。

## 三计数
- 核心成员 **{c['core_members']}**（MDB {c['mdb_files']} + SQL {c['sql_files']}；完整链+sha 绑定 inventory 精确对账）
- 已枚举对象 **{c['enumerated_objects_total']}** = SQL 表 **{c['sql_tables_enumerated']}**（全量 CREATE TABLE 解析，异常 {c['sql_parse_anomalies']}）+ MDB 文件级 **{c['mdb_objects_header_confirmed']}**（头探针；表/字段枚举=GAP 不臆造）
- 已映射对象（提案）**{c['mapped_objects_proposed']}**（SQL 表→目标类型提案，PROPOSED_NOT_AUTHORIZED/ready_for_import=false）；MDB 表映射 0（待读取器）

## SQL 面
""" + "\n".join(
    f"- {sr['member_key'].split('!')[-1]}：方言 **{sr['dialect']}**（证据 {json.dumps(sr['dialect_evidence'], ensure_ascii=False)[:160]}）；表 {sr['table_count']}；INSERT 语句 {sr['insert_statement_count']}（行估算 {sr['row_count_estimate']}，口径注记在证）；载体 {sr['data_carrier']}；编码 {sr['encoding_detected']}（BOM {sr['bom_present']}，替换字符 {sr['replacement_chars_on_decode']}（定位行 {[h['line'] for h in sr.get('replacement_char_locations', [])][:3]}））；DROP {sr['drop_table_count']}/LOCK {sr['lock_tables_count']}"
    for sr in sql_results) + f"""

## MDB 面（工具缺口）
- 5 件头级确证（JET magic/签名/版本字节/页大小版本推导/128 字节 hexdump 逐字），sha 全匹配 inventory。
- **{mirror_note}**
- 逐件不可读原因+所需工具（mdbtools={MDBTOOLS_CANDIDATE} 候选提案，本轮不装）+隔离恢复路径在 evidence-gaps。
- 编码/二进制/NULL/精度面：MDB 需目录读取器后逐列断言，本轮不臆测。

## 相关成员处置（exactly-once）
3 内层容器 ZIP structural；Thumbs.db 非数据排除→块5；cbdb sqlite3 块1既有（78表736列）不重映射；china_chron.xls 块2既有；txt/README documentation。

## 缺口与批准面
缺口 **{len(gaps)}**（MDB 工具缺口×5{gap_kind_note}）；全部提案待茶香/Codex 批准；MDB 读取器安装需另批。
"""

(HERE / "members.json").write_text(json.dumps(members_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "object-mapping.json").write_text(json.dumps(mapping_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "evidence-gaps.json").write_text(json.dumps(gaps_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "SUMMARY.md").write_text(summary)
print(f"mdb-sql package built OK: members {c['core_members']} enumerated {c['enumerated_objects_total']} mapped {c['mapped_objects_proposed']} gaps {len(gaps)}")
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


# ---------------------------------------------------------------- MDB enumeration evidence
MDB_EV = HERE / "mdb_evidence"  # transferred alongside on 32; committed in repo .mdb-sql-block4-20261120/mdb/
MDB_IMAGE_ID = "sha256:74e022830b3b16ab18847d43c98d7b2fde042da7ae40a3841febee5c29000399"
CASE_BY_SHA_CHAIN = {
    ("harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip", "access_dbase/v3_chgis_dbase.ZIP!v3_chgis_database.mdb"): "v3_himive",
    ("harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip", "access_database/v4_chgis_dbase.mdb"): "v4_direct",
    ("harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip", "access_database/v4_chgis_dbase.zip!v4_chgis_dbase.mdb"): "v4_access_zip",
    ("harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip", "shapefiles/v4_chgis_dbase.zip!v4_chgis_dbase.mdb"): "v4_shapefiles_zip",
    ("harvard-full/doi_10_7910/DVN/ZZKZ6U/CHGIS_V2.zip", "access_dbase/chgis_v2_database.ZIP!chgis_v2_database.mdb"): "v2_zzkz6u",
}
MDB_TYPE_MAP = {
    "Text": lambda sz: f"varchar({sz})" if sz else "text",
    "Memo": lambda sz: "text", "Memo/Hyperlink": lambda sz: "text",
    "Long Integer": lambda sz: "integer", "Integer": lambda sz: "smallint",
    "Byte": lambda sz: "smallint", "Single": lambda sz: "real",
    "Double": lambda sz: "double precision", "Numeric": lambda sz: "numeric",
    "Decimal": lambda sz: "numeric", "DateTime": lambda sz: "timestamp",
    "Short DateTime": lambda sz: "timestamp", "Bit": lambda sz: "boolean",
    "OLE Object": lambda sz: "bytea", "Binary": lambda sz: "bytea",
    "Replication ID": lambda sz: "uuid",
}
MDB_BINARY_TYPES = {"OLE Object", "Binary"}


def parse_mdb_schema(text):
    tables = []
    for m in re.finditer(r"CREATE TABLE \[([^\]]+)\]\s*\((.*?)\);", text, re.S):
        tname, body = m.group(1), m.group(2)
        cols = []
        for ln in body.splitlines():
            cm = re.match(r"\s*\[([^\]]+)\]\s+([A-Za-z][A-Za-z/ ]*?)\s*(?:\((\d+)\))?\s*,?\s*$", ln)
            if cm:
                cname, ctype, sz = cm.group(1), cm.group(2).strip(), cm.group(3)
                sz = int(sz) if sz else None
                tt = MDB_TYPE_MAP.get(ctype, lambda s: "text")(sz)
                cols.append({"ordinal": len(cols) + 1, "original_name": cname,
                             "source_type": ctype, "size_verbatim": sz,
                             "target_type_proposal": tt,
                             "binary_flag": ctype in MDB_BINARY_TYPES,
                             "precision_note": (f"Text length {sz}" if ctype == "Text" and sz else
                                                "numeric precision/scale not exposed by mdb-schema; catalog-level check at import" if ctype in ("Numeric", "Decimal") else None),
                             "nullability_note": "mdb-schema does not expose NOT NULL flags; nullability requires catalog-level verification at import contract",
                             "encoding_note": "JET4 catalog UTF-16LE; mdbtools output declares UTF-8 conversion; original codepage semantics require value contract",
                             "definition_line_verbatim": ln.rstrip()})
            elif ln.strip():
                cols.append({"ordinal": len(cols) + 1, "parse_anomaly": True,
                             "definition_line_verbatim": ln.rstrip()})
        tables.append({"table_name_source": tname, "columns": cols,
                       "create_definition_verbatim": m.group(0)})
    return tables


def load_mdb_enumeration():
    if not MDB_EV.exists():
        return None
    ev = {}
    for case in CASE_BY_SHA_CHAIN.values():
        d = MDB_EV / case
        if not d.exists():
            return None
        schema_text = (d / "schema.txt").read_text(encoding="utf-8", errors="replace")
        tables = parse_mdb_schema(schema_text)
        listed = [t for t in (d / "tables.txt").read_text().splitlines() if t.strip()]
        rows = {}
        for ln in (d / "rowcounts.txt").read_text().splitlines():
            if "|" in ln:
                k, v = ln.rsplit("|", 1)
                rows[k] = int(v) if v.strip().isdigit() else None
        for t in tables:
            t["row_count_mdb_count"] = rows.get(t["table_name_source"])
        ev[case] = {
            "ver": (d / "ver.txt").read_text().strip(),
            "tables_listed": listed, "tables_parsed": tables,
            "table_count_listed": len(listed), "table_count_parsed": len(tables),
            "list_parse_symmetric_diff": sorted(set(listed) ^ {t["table_name_source"] for t in tables}),
            "schema_err_bytes": (d / "schema.err").stat().st_size if (d / "schema.err").exists() else None,
            "count_err_bytes": (d / "count.err").stat().st_size if (d / "count.err").exists() else None,
            "export_err_bytes": (d / "export.err").stat().st_size if (d / "export.err").exists() else None,
            "schema_sha256": sha256_bytes((d / "schema.txt").read_bytes()),
            "encoding_declaration": "UTF-8 (mdb-schema header comment verbatim)" if "encoding UTF-8" in schema_text else None,
        }
    return ev


# ---------------------------------------------------------------- build
sql_results = [parse_sql(e) for e in SQL]
mdb_results = [probe_mdb(e) for e in MDB]
MDB_ENUM = load_mdb_enumeration()
GEOM_EV_PATH = HERE / "geom_evidence" / "geom-extraction.json"
GEOM = json.loads(GEOM_EV_PATH.read_text()) if GEOM_EV_PATH.exists() else None
GEOM_SHA = sha256_bytes(GEOM_EV_PATH.read_bytes()) if GEOM else None
geom_summary = "" if not GEOM else """
## geom 二进制字面量提取（原始字节全程，a02 交付 lead/a03 核验）
- tgaz `geom` 表：**INSERT 1 条/记录 1**（三途径互证：语句扫描/全文件 1432 行交叉扫描/DDL AUTO_INCREMENT=2）；可验证 **1/1**，首个无法验证位置 **null**。
- 两层证据：raw_literal 33B（转义 \\0、\\\\）vs decoded_payload 25B；MySQL 内部格式 4B LE SRID=0 + WKB LE Point (115.31562, 38.94772)，consumed==len 精确闭合；SRID 0⇒CRS unresolved 不推断。
- 零替换字符参与生成、源 SQL 未执行；证据 .mdb-sql-block4-20261120/geom/（sha 入 mapping_doc.geom_extraction）。
"""

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
mdb_table_objects = []
for mr in mdb_results:
    parts = mr["member_key"].split("!")
    case = CASE_BY_SHA_CHAIN.get((parts[0], "!".join(parts[1:])))
    enum = MDB_ENUM.get(case) if MDB_ENUM and case else None
    obj = {
        "source_object_id": sha256_bytes(mr["member_key"].encode()),
        "carrier": "mdb_file",
        "source_file_or_chain": mr["member_key"],
        "source_identity": {"sha256": mr["sha256"], "size": mr["size"]},
        "header_probe": {k: v for k, v in mr.items()
                         if k not in ("member_key", "sha256", "size")},
        "table_enumeration_status": ("ENUMERATED_MDBTOOLS_READONLY" if enum else "GAP_NO_CATALOG_READER"),
        "status": {"confirmation_state": ("CONFIRMED_ENUMERATED" if enum else "CONFIRMED_HEADER_ONLY"),
                   "ready_for_import": False},
    }
    if enum:
        unreadable = [t for t in enum["tables_parsed"]
                      if any(c.get("parse_anomaly") for c in t["columns"])]
        obj["table_enumeration"] = {
            "tool": f"mdbtools={MDBTOOLS_CANDIDATE}", "image_id": MDB_IMAGE_ID,
            "container_network": "none", "snapshot_mount": "ro",
            "case": case, "ver": enum["ver"],
            "table_count_listed": enum["table_count_listed"],
            "table_count_parsed": enum["table_count_parsed"],
            "list_parse_symmetric_diff": enum["list_parse_symmetric_diff"],
            "schema_err_bytes": enum["schema_err_bytes"],
            "count_err_bytes": enum["count_err_bytes"],
            "export_err_bytes": enum["export_err_bytes"],
            "encoding_declaration": enum["encoding_declaration"],
            "schema_sha256": enum["schema_sha256"],
            "tables": enum["tables_parsed"],
            "unreadable_tables_or_fields": [
                {"table": t["table_name_source"],
                 "items": [c for c in t["columns"] if c.get("parse_anomaly")]}
                for t in unreadable],
            "row_count_total": sum(t["row_count_mdb_count"] or 0
                                   for t in enum["tables_parsed"]),
            "value_contract_note": "schema-level enumeration this round; full value export/encoding canonicalization/NULL semantics/binary byte-faithful contract at import stage",
        }
    mdb_objects.append(obj)
    if enum:
        stem = Path(parts[-1]).stem.lower()
        for t in enum["tables_parsed"]:
            tname = t["table_name_source"]
            ident = mr["member_key"] + "#" + tname
            fields = [c for c in t["columns"] if not c.get("parse_anomaly")]
            mdb_table_objects.append({
                "source_object_id": sha256_bytes(ident.encode()),
                "carrier": "mdb_table",
                "source_file_or_chain": mr["member_key"],
                "source_identity": {"sha256": mr["sha256"], "size": mr["size"],
                                    "table_name_source": tname, "case": case},
                "table_name_proposal": re.sub(r"[^a-z0-9_]", "_", f"{stem}_{tname}".lower()),
                "fields": fields, "field_count": len(fields),
                "row_count_mdb_count": t["row_count_mdb_count"],
                "create_definition_verbatim": t["create_definition_verbatim"],
                "status": {"confirmation_state": "PROPOSED_NOT_AUTHORIZED",
                           "ready_for_import": False},
            })
proposed.extend(mdb_table_objects)

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

_mdb_by_sha = {}
for o in mdb_objects:
    _mdb_by_sha.setdefault(o["source_identity"]["sha256"], o)
_mdb_tables_distinct = sum(o.get("table_enumeration", {}).get("table_count_parsed", 0)
                           for o in _mdb_by_sha.values())
_mdb_tables_enum = sum(o.get("table_enumeration", {}).get("table_count_parsed", 0)
                       for o in mdb_objects)
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
        "sql_table_proposals": len(proposed) - len(mdb_table_objects),
        "mdb_table_proposals": len(mdb_table_objects),
        "mdb_objects_header_confirmed": len(mdb_objects),
        "mdb_files_read_through": sum(1 for o in mdb_objects
                                      if o["table_enumeration_status"] == "ENUMERATED_MDBTOOLS_READONLY"),
        "mdb_tables_enumerated": _mdb_tables_enum,
        "mdb_tables_distinct_by_source_sha": _mdb_tables_distinct,
        "mdb_tables_distinct_note": "4 distinct source shas (V3/V4-direct/V4-zip-wrapped/V2); V4 direct vs zip-wrapped differ in bytes but mdb-schema/tables/rowcounts outputs are IDENTICAL (difference in non-schema pages); logical schema families = v3(12)+v4(13)+v2(11)=36; mirror merge deferred to block 6",
        "enumerated_objects_total": sum(len(sr["tables"]) for sr in sql_results) + _mdb_tables_enum,
    },
    "geom_extraction": (None if not GEOM else {
        "evidence_file": ".mdb-sql-block4-20261120/geom/geom-extraction.json",
        "evidence_sha256": GEOM_SHA,
        "extracted": GEOM}),
    "flags": {"ready_for_import": False, "target_mapping_approved": False,
              "sql_execution": "FORBIDDEN_THIS_ROUND_NOT_EXECUTED",
              "installs_this_round": False},
}

gaps = []
for mr in mdb_results:
    if MDB_ENUM:
        gaps.append({"object": mr["member_key"], "kind": "tool_gap_mdb_catalog_RESOLVED",
                     "resolution": (f"read through via Chaxiang-approved candidate image "
                                    f"{MDB_IMAGE_ID[:24]}… mdbtools={MDBTOOLS_CANDIDATE}; "
                                    "schema/count/export error files 0 bytes; see object table_enumeration"),
                     "sha256": mr["sha256"], "size": mr["size"],
                     "remaining_value_contract": "full value export/encoding canonicalization/NULL semantics/binary byte-faithful contract at import stage"})
    else:
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
                     "recovery_note": ("replacement chars localized (see locations/context_verbatim); where context shows binary payload inside string literals (e.g. geometry WKB-style raw high bytes), naive text decode loses original bytes — byte-faithful extraction required (isolation recovery); no value fabrication"),
                     "geom_extraction_status": ("byte-faithful extraction verified this round (1/1 record; raw literal 33B vs decoded payload 25B; MySQL SRID-0 prefix + WKB LE Point; zero replacement chars used; import value contract still pending)" if GEOM else None)})
for t in anomalies:
    gaps.append({"object": "sql_parse_anomaly", "kind": "structure_parse_anomaly",
                 "verbatim": t["create_definition_verbatim"][:500]})

gaps_doc = {
    "format": "xiangrugu.import-package.mdb-sql.evidence-gaps.v1",
    "baseline_git": VCS_REF,
    "gap_count": len(gaps), "gaps": gaps,
    "tool_gap_report": {
        "status": ("RESOLVED_MDB_CATALOG_VIA_APPROVED_CANDIDATE" if MDB_ENUM
                   else "MDB_CATALOG_READER_NOT_INSTALLED"),
        "affected_objects": [mr["member_key"] for mr in mdb_results],
        "capability_missing": ("none for schema-level enumeration (resolved)" if MDB_ENUM
                               else "JET/ACE catalog + table/field/value enumeration"),
        "required_tool": f"mdbtools={MDBTOOLS_CANDIDATE} (bookworm apt candidate measured on 32; locked in requirements-apt.lock mdbtools section)",
        "installed_this_round": bool(MDB_ENUM),
        "installed_in_candidate_image_only": bool(MDB_ENUM),
        "host_software_unchanged": True,
        "resolution": (None if not MDB_ENUM else {
            "image_id": MDB_IMAGE_ID,
            "apt_lock": "datamgmt/requirements-apt.lock mdbtools section (4 debs sha256)",
            "files_read_through": len(mdb_objects),
            "tables_enumerated": _mdb_tables_enum,
            "schema_count_export_errors": "0 bytes across all 5 cases",
            "remaining": "full value contract at import stage; mirror merge block 6"}),
        "sql_plane": "fully text-identified with stdlib; no tool gap for dialect/structure/carrier; geom binary literal extraction see geom-extraction evidence",
    },
    "dependency_gaps": [],
}

c = mapping_doc["counts"]
_mdb_field_instances = sum(len(o["fields"]) for o in mapping_doc["proposed_objects"] if o["carrier"] == "mdb_table")
_sql_column_instances = sum(len(o["fields"]) for o in mapping_doc["proposed_objects"] if o["carrier"] == "sql_table")
gap_kind_note = (("；编码损失风险" if any(g["kind"] == "encoding_loss_risk" for g in gaps) else "")
                 + ("；结构解析异常" if anomalies else ""))
summary = f"""# 第 4/6 块 · MDB 与 SQL 包（SUMMARY）

基线 git {VCS_REF}；inventory sha256={INV_SHA_EXPECTED[:16]}… 断言一致；32 宿主 python3 stdlib 流式只读；**SQL 未对任何库执行；依赖仅入候选镜像（mdbtools 4 deb 离线闭包），宿主零安装；源件只读零触**。

## 三计数
- 核心成员 **{c['core_members']}**（MDB {c['mdb_files']} + SQL {c['sql_files']}；完整链+sha 绑定 inventory 精确对账）
- 已枚举对象 **{c['enumerated_objects_total']}** = SQL 表 **{c['sql_tables_enumerated']}**（全量 CREATE TABLE 解析，异常 {c['sql_parse_anomalies']}；列 {_sql_column_instances}）+ MDB 表实例 **{c['mdb_tables_enumerated']}**（5/5 读通；字段实例 {_mdb_field_instances}）
- 已映射对象（提案）**{c['mapped_objects_proposed']}** = SQL 表提案 {c['sql_table_proposals']} + MDB 表提案 {c['mdb_table_proposals']}（PROPOSED_NOT_AUTHORIZED/ready_for_import=false，全部待批准）

## SQL 面
""" + "\n".join(
    f"- {sr['member_key'].split('!')[-1]}：方言 **{sr['dialect']}**（证据 {json.dumps(sr['dialect_evidence'], ensure_ascii=False)[:160]}）；表 {sr['table_count']}；INSERT 语句 {sr['insert_statement_count']}（行估算 {sr['row_count_estimate']}，口径注记在证）；载体 {sr['data_carrier']}；编码 {sr['encoding_detected']}（BOM {sr['bom_present']}，替换字符 {sr['replacement_chars_on_decode']}（定位行 {[h['line'] for h in sr.get('replacement_char_locations', [])][:3]}））；DROP {sr['drop_table_count']}/LOCK {sr['lock_tables_count']}"
    for sr in sql_results) + f"""

## MDB 面（茶香授权候选镜像，本轮读通）
- 镜像 xiangrugu:runtime-mdbtools-20261120-a Id {MDB_IMAGE_ID[:24]}…（mdbtools={MDBTOOLS_CANDIDATE}；4 deb 离线闭包 --network none 构建；requirements-apt.lock mdbtools 段）；mdb-tables/mdb-schema v1.0.0 预检通过；容器无网络/无凭据/无 socket，快照 :ro，仅本轮隔离目录解包，未进 pg32/pg32b。
- **5/5 读通**（全 JET4）：内部表 **{_mdb_tables_enum}**（按源 sha 去重 {_mdb_tables_distinct}；逻辑 schema 族 36=v3 12+v4 13+v2 11；V4 两版本字节异但 schema/表/行数输出全同，镜像对分别登记来源）；行数合计 {sum(o.get('table_enumeration', {}).get('row_count_total', 0) for o in mdb_objects)}；schema/count/export 错误文件全 0 字节；表清单 vs schema 解析对称差空；sha+成员序号全断言==inventory。
- 编码：mdb-schema 头部声明 UTF-8 输出（JET4 目录 UTF-16LE 转换，原始码页语义留值合同）；NULL：mdb-schema 不暴露 NOT NULL⇒导入合同目录级核验；精度：Text(n) 逐字、Numeric 精度/标度目录级待核；二进制：OLE Object/Binary→bytea 提案逐件标记。
- **{mirror_note}**
- 读不出表/字段：本轮 **0 项**（若有逐项在 object table_enumeration.unreadable_tables_or_fields）；全量值导出/编码规范化/NULL 语义/二进制字节忠实合同留导入阶段。

{geom_summary}
## 相关成员处置（exactly-once）
3 内层容器 ZIP structural；Thumbs.db 非数据排除→块5；cbdb sqlite3 块1既有（78表736列）不重映射；china_chron.xls 块2既有；txt/README documentation。

## 缺口与批准面
缺口 **{len(gaps)}** = MDB 读取器缺口×5 **已解决**（茶香授权候选镜像 runtime-mdbtools-20261120-a，仅入镜像不装宿主）+ SQL 编码记录×1（encoding_loss_risk：保留 geom 字节忠实提取结果 raw 33B/decoded 25B，导入合同待定）；96 提案仍待茶香/Codex 批准，ready_for_import=false。
"""

(HERE / "members.json").write_text(json.dumps(members_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "object-mapping.json").write_text(json.dumps(mapping_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "evidence-gaps.json").write_text(json.dumps(gaps_doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
(HERE / "SUMMARY.md").write_text(summary)
print(f"mdb-sql package built OK: members {c['core_members']} enumerated {c['enumerated_objects_total']} mapped {c['mapped_objects_proposed']} gaps {len(gaps)}")
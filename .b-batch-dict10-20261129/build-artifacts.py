"""Build per-table contract + payload for the three CBDB dictionary tables.

Read-only against the source (mode=ro&immutable=1). Column order PRESERVED from the
mapping draft's source_ordinal, which is what makes ASSUME_OFFICE_CODES differ:
its order is code, desc_chn, desc -- not code, desc, desc_chn.
"""
import sqlite3, hashlib, json, pathlib, sys

SRC = "file:/src/harvard/cbdb/cbdb_20260919.sqlite3?mode=ro&immutable=1"
MAP = "/tmp/mapping.json"
OUT = pathlib.Path("/data/var/b-batch/dict10")
want = {"COUNTRY_CODES", "LITERARYGENRE_CODES", "TEXT_ROLE_CODES", "APPOINTMENT_TYPES", "STATUS_TYPES", "ALTNAME_CODES", "BIOG_ADDR_CODES", "BIOG_INST_CODES", "ENTRY_TYPES", "INDEXYEAR_TYPE_CODES"}
ADJUDICATED = {
    "COUNTRY_CODES": "1e23b088ded253b5b4b41247a92a33490e5332891433dc0db2d84d557bce90e4",
    "LITERARYGENRE_CODES": "0e8f45e94354f108ef185916ed41fd9c96c2e09d7d619200cc47ddec38baf869",
    "TEXT_ROLE_CODES": "62f423e1d6899ebd8283c2948f44f28b9b6c43d99c39ac2ff64cb7a27840317e",
    "APPOINTMENT_TYPES": "0ab780b444137883895f05217cb4efe6d146e8335e3b89be3c2aa4feaa1c0d33",
    "STATUS_TYPES": "22f21f37567d90aad7afebe58ab17e896eda1667321e29bbb5201e1b9937f1ce",
    "ALTNAME_CODES": "110d8776517a70391c75f03e278d790d2f8fb5b0a7e0780531b8772dda8f4a59",
    "BIOG_ADDR_CODES": "e3316df00ad67591dda48bfc9efa56442efb9cf4be21dfc49f88c28264e738ac",
    "BIOG_INST_CODES": "dc254a78011157a7aae093c8061bb162460e247ba209371c4511734584d8bd88",
    "ENTRY_TYPES": "5f73008b57b6900ffaf31a52b75fc69b259acc399c1b0faccd82d3346febd884",
    "INDEXYEAR_TYPE_CODES": "4d16efe79d58c7c0f18717debf6ab61c73e9c6168c91dbef673a753bb8503932"
}

sys.path.insert(0, "/app/datamgmt/src")
from xiangrugu_datamgmt.unordered_values import (
    UnorderedSchema, UnorderedColumn, UnorderedLimits,
    header_bytes, trailer_bytes, encode_unordered_row)

con = sqlite3.connect(SRC, uri=True)
lim = UnorderedLimits()
mp = json.load(open(MAP))

def walk(o, acc):
    if isinstance(o, dict):
        if o.get("source_object_name") in want: acc.append(o)
        for v in o.values(): walk(v, acc)
    elif isinstance(o, list):
        for v in o: walk(v, acc)

ents = []; walk(mp, ents)
OUT.mkdir(parents=True, exist_ok=True)
manifest = {}
for e in sorted(ents, key=lambda x: x["source_object_name"]):
    t = e["source_object_name"]
    cs = sorted(e["columns"], key=lambda c: c["source_ordinal"])
    cols = tuple(UnorderedColumn(source_ordinal=i, column_key=c["column_identity"],
                                 pg_type=c["approved_type"],
                                 allow_null_value=bool(c["target_nullable_candidate"]))
                 for i, c in enumerate(cs))
    sch = UnorderedSchema(source_object_id=e["source_object_id"], columns=cols)
    sel = ", ".join('"%s"' % c["source_name"] for c in cs)
    rows = list(con.execute(f'select {sel} from "{t}"'))
    frames = [encode_unordered_row(sch, tuple(r), limits=lim) for r in rows]
    h = hashlib.sha256(); h.update(header_bytes(sch))
    for f in sorted(frames): h.update(f)
    h.update(trailer_bytes(len(rows)))
    canon = h.hexdigest()
    assert canon == ADJUDICATED[t], f"{t}: digest drifted {canon} != {ADJUDICATED[t]}"

    # payload TSV: tab-separated, NULL -> \N, LF line endings (same dialect as B batch)
    lines = []
    for r in rows:
        cells = []
        for v in r:
            if v is None: cells.append("\\N")
            elif isinstance(v, bool): cells.append("1" if v else "0")
            else: cells.append(str(v))
        lines.append("\t".join(cells))
    data = ("\n".join(lines) + "\n").encode("utf-8") if lines else b""
    pf = OUT / f"{t}.payload.tsv"
    pf.write_bytes(data)

    pk = [(c["source_pk_ordinal"], c["target_name_candidate"]) for c in cs if c.get("source_pk_ordinal")]
    pk.sort()
    manifest[t] = {
        "source_table": t,
        "source_object_id": e["source_object_id"],
        "target_schema": e["target_schema_candidate"],
        "target_table": e["target_table_candidate"],
        "columns": [{"ordinal": c["source_ordinal"], "source_column": c["source_name"],
                     "target_column": c["target_name_candidate"],
                     "pg_type": c["approved_type"],
                     "nullable": bool(c["target_nullable_candidate"]),
                     "column_identity": c["column_identity"]} for c in cs],
        "primary_key": {"columns_in_order": [n for _, n in pk]},
        "row_count": len(rows),
        "null_counts": {c["target_name_candidate"]: sum(1 for r in rows if r[i] is None)
                        for i, c in enumerate(cs)},
        "source_canonical_sha256": canon,
        "payload_file": str(pf),
        "payload_sha256": hashlib.sha256(data).hexdigest(),
        "payload_bytes": len(data),
        "payload_lines": len(lines),
    }
    print(f"{t:22s} rows={len(rows)} payload_sha={manifest[t]['payload_sha256'][:16]}… "
          f"pk={[n for _, n in pk]} order={[c['source_name'] for c in cs]}")

(OUT / "contract-ten-tables.json").write_text(
    json.dumps({"version": 1, "release_id": "2026-11-29-dict10",
                "source_member": {"rule_id": "m007906",
                                  "relative_path": "harvard/cbdb/cbdb_20260919.sqlite3",
                                  "sha256": "bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400"},
                "mapping_contract_sha256": "297b7c766baa40cc660f262e1ac433973d5d8bdde8c28eb2aca90733bfaec7d9",
                "digest_method": "sorted(encoded row frames); header_bytes + frames + trailer_bytes(count)",
                "tables": manifest}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print("contract written")

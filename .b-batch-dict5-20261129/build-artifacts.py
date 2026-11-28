"""Build per-table contract + payload for the three CBDB dictionary tables.

Read-only against the source (mode=ro&immutable=1). Column order PRESERVED from the
mapping draft's source_ordinal, which is what makes ASSUME_OFFICE_CODES differ:
its order is code, desc_chn, desc -- not code, desc, desc_chn.
"""
import sqlite3, hashlib, json, pathlib, sys

SRC = "file:/src/harvard/cbdb/cbdb_20260919.sqlite3?mode=ro&immutable=1"
MAP = "/tmp/mapping.json"
OUT = pathlib.Path("/data/var/b-batch/dict3")
want = {"YEAR_RANGE_CODES", "MEASURE_CODES", "PARENTAL_STATUS_CODES", "SOCIAL_INSTITUTION_TYPES", "OCCASION_CODES"}
ADJUDICATED = {
    "YEAR_RANGE_CODES": "50e611e9fac0fa4ac915c10e45c45cbcd0b62d7953ee6dd05035121640fc160f",
    "MEASURE_CODES": "a668a5276115b3004264142b9feea37968e698fdd8c90e101b7d40353a18a465",
    "PARENTAL_STATUS_CODES": "f52bc9732df6f2565aea50dea4d64ee07ba3751a7be035736aaed292975a3220",
    "SOCIAL_INSTITUTION_TYPES": "0231c049c73e07be57b0084758b759b8b1637ccf3dfc8755865c6f13cfe9fdbc",
    "OCCASION_CODES": "b462003398227df634ffd7830458db499d7cd7aa9f7cc717d4789e309418b061",
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

(OUT / "contract-three-tables.json").write_text(
    json.dumps({"version": 1, "release_id": "2026-11-29-dict5",
                "source_member": {"rule_id": "m007906",
                                  "relative_path": "harvard/cbdb/cbdb_20260919.sqlite3",
                                  "sha256": "bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400"},
                "mapping_contract_sha256": "297b7c766baa40cc660f262e1ac433973d5d8bdde8c28eb2aca90733bfaec7d9",
                "digest_method": "sorted(encoded row frames); header_bytes + frames + trailer_bytes(count)",
                "tables": manifest}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print("contract written")

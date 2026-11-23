#!/usr/bin/env python3
"""First-batch two Ca1884route spatial objects: read-only source-side value evidence.

Reads 1884route.zip SHP/DBF/CPG members read-only, reuses the approved encoding,
field mapping, one-based physical rownum, 2D Point / SRID 4326 and original X/Y.
Generates independent attribute (XRGVALUE-v1 via canonical.py) and geometry
(XRGGEOM-v1, original IEEE754 X/Y bytes preserved) expectations aligned by source
rownum. Records row counts, duplicate counts and full digests. If the actual
count differs from the known 59 rows, writes evidence and stops (exit 2).
No source modification; no database operations; no formal contract change.
"""
import hashlib
import json
import struct
import sys
import zipfile
from pathlib import Path

from xiangrugu_datamgmt import canonical

ZIP = Path("/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/E7HDYD/1884route.zip")
KNOWN_ROWS = 59
SRID = 4326
DIMENSIONS = 2
OBJECTS = [
    {"object_name": "Ca1884route_przh_1251",
     "source_object_id": "9b4496c93de442c447b58adf9be56303ab5fd4897d68bbf0bad99069d12d44dc",
     "stem": "5_1884route/Ca1884route_przh_1251", "codec": "cp1251",
     "shp_sha": "109d74b1e5cefcd1b32ad81e90fa94d150dd719b4fd530651b4dbdfff869eac7",
     "dbf_sha": "0b4b86cb8b6dc892", "cpg_sha": "ea80b523f4585374b7c94e7b9b420166e845e318f0efb4bafd6f51d3e8b1f72a"},
    {"object_name": "Ca1884route_przh_utf8",
     "source_object_id": "e601ce1a7667c8286abce0d09c5b81d3dc809265ed219dd6e4e1dd3c5cfc9ace",
     "stem": "5_1884route/Ca1884route_przh_utf8", "codec": "utf-8",
     "shp_sha": "109d74b1e5cefcd1b32ad81e90fa94d150dd719b4fd530651b4dbdfff869eac7",
     "dbf_sha": "eb9dfed2745641ac", "cpg_sha": "3ad3031f5503a4404af825262ee8232cc04d4ea6683d42c5dd0a2f2a27ac9824"},
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def parse_shp(raw):
    assert struct.unpack(">i", raw[0:4])[0] == 9994, "shp file code"
    assert struct.unpack("<i", raw[32:36])[0] == 1, "shp shape type Point"
    points = []
    off = 100
    while off < len(raw):
        recnum, words = struct.unpack(">ii", raw[off:off + 8])
        content = raw[off + 8:off + 8 + words * 2]
        assert struct.unpack("<i", content[0:4])[0] == 1, "record shape type"
        assert len(content) == 20, "point content length"
        xb, yb = content[4:12], content[12:20]
        points.append({"rownum": recnum, "x_bytes": xb.hex(), "y_bytes": yb.hex(),
                       "x": struct.unpack("<d", xb)[0], "y": struct.unpack("<d", yb)[0]})
        off += 8 + words * 2
    assert off == len(raw), "shp trailing bytes"
    assert [p["rownum"] for p in points] == list(range(1, len(points) + 1)), "shp rownum sequence"
    return points


def parse_dbf(raw, columns, codec):
    numrecords = struct.unpack("<i", raw[4:8])[0]
    headerlen = struct.unpack("<h", raw[8:10])[0]
    recordlen = struct.unpack("<h", raw[10:12])[0]
    fields = []
    off = 32
    while raw[off] != 0x0D:
        fd = raw[off:off + 32]
        fields.append({"name": fd[0:11].split(b"\x00")[0].decode("ascii"),
                       "type": chr(fd[11]), "length": fd[16], "decimals": fd[17]})
        off += 32
    assert [(f["name"], f["type"], f["length"], f["decimals"]) for f in fields] == \
           [(c["original_name"], c["source_type"], c["source_width_bytes"], c["source_decimals"])
            for c in columns], "dbf fields != approved mapping"
    assert headerlen == 32 + 32 * len(fields) + 1
    assert recordlen == 1 + sum(f["length"] for f in fields)
    base = headerlen + numrecords * recordlen
    assert len(raw) in (base, base + 1), "dbf length"  # optional 0x1A EOF terminator
    rows, deleted, blank_numeric = [], 0, []
    for i in range(numrecords):
        rec = raw[headerlen + i * recordlen:headerlen + (i + 1) * recordlen]
        if rec[0:1] == b"\x2a":
            deleted += 1
            continue
        assert rec[0:1] == b"\x20", "dbf deletion flag"
        values, pos = [], 1
        for f, c in zip(fields, columns):
            cell = rec[pos:pos + f["length"]]
            pos += f["length"]
            if f["type"] == "C":
                values.append(cell.decode(codec, errors="strict"))  # trailing spaces preserved
            else:
                text = cell.decode("ascii", errors="strict")  # N raw bytes preserved
                if text.strip() == "":
                    blank_numeric.append({"rownum": i + 1, "column": f["name"]})
                values.append(text)
        rows.append(tuple(values))
    return rows, numrecords, deleted, blank_numeric


def geometry_stream(sid, points):
    out = bytearray(b"XRGGEOM\x00\x01" + bytes.fromhex(sid) + struct.pack(">ib", SRID, DIMENSIONS))
    for p in points:
        out += b"\x52" + struct.pack(">Q", p["rownum"]) + bytes.fromhex(p["x_bytes"]) + bytes.fromhex(p["y_bytes"])
    out += b"\x45" + struct.pack(">Q", len(points))
    return bytes(out)


def main():
    attrs_doc = json.loads(Path(sys.argv[1]).read_text())
    attrs_by_sid = {o["source_object_id"]: o for o in attrs_doc["objects"]}
    inv = json.loads(Path(sys.argv[2]).read_text())
    dbf_full = {}
    for e in inv["entries"]:
        if e["relative_path"] == str(ZIP.relative_to("/mnt/wd61workmetadata/usedata")) and e["archive_chain"]:
            dbf_full[e["archive_chain"][0]] = e["sha256"]
    results, stop = [], False
    with zipfile.ZipFile(ZIP) as zf:  # read-only
        for obj in OBJECTS:
            stem = obj["stem"]
            shp_raw = zf.read(stem + ".shp")
            dbf_raw = zf.read(stem + ".dbf")
            cpg_raw = zf.read(stem + ".cpg")
            comp = {"shp": {"sha256": sha(shp_raw), "size": len(shp_raw), "expected": obj["shp_sha"],
                            "match": sha(shp_raw) == obj["shp_sha"]},
                    "dbf": {"sha256": sha(dbf_raw), "size": len(dbf_raw),
                            "expected": dbf_full[stem + ".dbf"], "match": sha(dbf_raw) == dbf_full[stem + ".dbf"]},
                    "cpg": {"sha256": sha(cpg_raw), "size": len(cpg_raw), "expected": obj["cpg_sha"],
                            "match": sha(cpg_raw) == obj["cpg_sha"], "declared": cpg_raw.decode("ascii")}}
            points = parse_shp(shp_raw)
            columns = attrs_by_sid[obj["source_object_id"]]["source_columns"]
            rows, numrecords, deleted, blank_numeric = parse_dbf(dbf_raw, columns, obj["codec"])
            n = len(points)
            aligned = (n == numrecords == len(rows) and deleted == 0
                       and [p["rownum"] for p in points] == list(range(1, n + 1)))
            schema = canonical.ValueSchema(
                source_object_id=obj["source_object_id"],
                columns=tuple(canonical.ValueColumn(column_key=c["column_id"], target_name=c["target_name"],
                                                    pg_type="text", nullable=False) for c in columns)
                + (canonical.ValueColumn(column_key=canonical.ROW_KEY, target_name="__src_rownum",
                                         pg_type="bigint", nullable=False),))
            summary = canonical.summarize_rows(
                schema, (row + (i + 1,) for i, row in enumerate(rows)), limits=canonical.ValueLimits())
            gstream = geometry_stream(obj["source_object_id"], points)
            seen_attr, dup_attr, seen_xy, dup_xy = set(), [], set(), []
            for i, row in enumerate(rows):
                if row in seen_attr:
                    dup_attr.append(i + 1)
                seen_attr.add(row)
                xy = (points[i]["x_bytes"], points[i]["y_bytes"])
                if xy in seen_xy:
                    dup_xy.append(i + 1)
                seen_xy.add(xy)
            count_ok = n == KNOWN_ROWS
            if not count_ok or not aligned or not all(c["match"] for c in comp.values()) or blank_numeric:
                stop = True
            results.append({
                "object_name": obj["object_name"], "source_object_id": obj["source_object_id"],
                "codec": obj["codec"], "components": comp,
                "row_count": n, "dbf_numrecords": numrecords, "shp_records": len(points),
                "known_rows": KNOWN_ROWS, "count_matches_known": count_ok,
                "deleted_records": deleted, "blank_numeric_fields": blank_numeric,
                "alignment": {"attr_geom_aligned_by_src_rownum": aligned, "rownum_range": [1, n]},
                "duplicate_counts": {"attribute_rows": len(dup_attr), "attribute_rownums": dup_attr,
                                     "coordinate_pairs": len(dup_xy), "coordinate_rownums": dup_xy},
                "attribute_expectation": {"canonical_format": "XRGVALUE-v1",
                                          "schema_nullability_note": "流 schema 按 XRGVALUE-v1 全源列 text NOT NULL（空串保留）nullable=False；yaml nullable_approved=true 为目标表 DDL 可空性批准（另一批准面），非流可空性；nullable_proposal=false 恰同值",
                                          "row_count": summary.row_count, "field_count": summary.field_count,
                                          "stream_bytes": summary.stream_bytes, "sha256": summary.sha256,
                                          "schema_sha256": sha(canonical.schema_bytes(schema)),
                                          "numeric_reading": "N raw bytes preserved as text; blank numeric NULL not approved",
                                          "character_trailing_spaces": "preserve"},
                "geometry_expectation": {"canonical_format": "XRGGEOM-v1", "srid": SRID,
                                         "dimensions": DIMENSIONS, "geometry_type": "Point",
                                         "coordinate_storage": "preserve_original_ieee754_xy_no_swap_or_transform",
                                         "row_count": len(points), "stream_bytes": len(gstream),
                                         "sha256": sha(gstream),
                                         "frame": "header XRGGEOM\\0\\1 + SID + srid>int32 + dims>byte; row 0x52 + rownum>uint64 + X(8 LE original) + Y(8 LE original); trailer 0x45 + count>uint64",
                                         "sample_first3": [{"rownum": p["rownum"], "x": p["x"], "y": p["y"],
                                                            "x_bytes": p["x_bytes"], "y_bytes": p["y_bytes"]}
                                                           for p in points[:3]]}})
    out = {"version": 1, "status": "COUNT_MISMATCH_STOP" if stop else "SOURCE_SIDE_EXPECTATIONS_GENERATED",
           "source_zip": str(ZIP), "source_zip_sha256": sha(ZIP.read_bytes()),
           "source_read_only": True, "formal_contract_modified": False, "database_connected": False,
           "objects": results}
    print(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    sys.exit(2 if stop else 0)


if __name__ == "__main__":
    main()
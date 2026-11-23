#!/usr/bin/env python3
"""Two Ca1884route spatial objects: isolated trial load + full readback (temporary PG+PostGIS).

Reads ONLY the verified 32 snapshot (1884route.zip). Local image PostGIS capability
verified and actual image Id + RepoDigests recorded (pg32b-full:18-pgdg carries
postgis-3; a brand-new isolated container is created from the image — the pg32b
instance/data are never touched). Unique per-run container name; --network none;
no host ports; NO fixed-name pre-delete; cleanup ONLY by the container Id created
and verified in this run. Both objects are checked separately (attributes and
target tables) even though their SHP bytes are identical. Approved attribute types
(text x7 / numeric(19,5) x2 / bigint x3), one-based source rownum, 2D Point /
SRID 4326, original IEEE754 X/Y preserved (hex EWKB load, no decimal conversion).
Numeric columns are reconstructed back to source field text by verified width/scale
for the XRGVALUE-v1 attribute digest; geometry type/dims/SRID/per-point X/Y bytes
for XRGGEOM-v1. Four digests must match per object. Any mismatch stops that item
with evidence. pg32/pg32b/deploy/formal landing out of scope.
"""
import hashlib
import json
import struct
import subprocess
import sys
import time
import uuid
import zipfile
from decimal import Decimal
from pathlib import Path

from xiangrugu_datamgmt import canonical

ZIP = Path("/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/E7HDYD/1884route.zip")
IMAGE = "pg32b-full:18-pgdg"
KNOWN_ROWS = 59
SRID = 4326
DIMENSIONS = 2
REL = Path("datamgmt/contracts/releases/2026-10-06-bootstrap")
ATTRS = json.loads((REL / "spatial-attributes-approved.draft.yaml").read_text())
ATTRS_BY_SID = {o.get("source_object_id"): o for o in ATTRS["objects"]}
OBJECTS = [
    {"object_name": "Ca1884route_przh_1251", "rule_id": "m002709",
     "source_object_id": "9b4496c93de442c447b58adf9be56303ab5fd4897d68bbf0bad99069d12d44dc",
     "stem": "5_1884route/Ca1884route_przh_1251", "codec": "cp1251",
     "shp_sha": "109d74b1e5cefcd1b32ad81e90fa94d150dd719b4fd530651b4dbdfff869eac7",
     "cpg_sha": "ea80b523f4585374b7c94e7b9b420166e845e318f0efb4bafd6f51d3e8b1f72a",
     "attr_sha": "3519649f663f8a6d", "geom_sha": "ff7081a0013d721f"},
    {"object_name": "Ca1884route_przh_utf8", "rule_id": "m002717",
     "source_object_id": "e601ce1a7667c8286abce0d09c5b81d3dc809265ed219dd6e4e1dd3c5cfc9ace",
     "stem": "5_1884route/Ca1884route_przh_utf8", "codec": "utf-8",
     "shp_sha": "109d74b1e5cefcd1b32ad81e90fa94d150dd719b4fd530651b4dbdfff869eac7",
     "cpg_sha": "3ad3031f5503a4404af825262ee8232cc04d4ea6683d42c5dd0a2f2a27ac9824",
     "attr_sha": "a2ad2d24ff4cae8c", "geom_sha": "3c6067845a7938e8"},
]
CONTAINER = f"xiangrugu-trial-spatial2-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{uuid.uuid4().hex[:8]}"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def psql(sql, db="xiangrugu_trial", csv_out=False):
    cmd = ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", db, "-v", "ON_ERROR_STOP=1"]
    cmd += (["-t", "--csv", "-c", sql] if csv_out else ["-c", sql])
    return run(cmd)


def parse_shp(raw):
    assert struct.unpack(">i", raw[0:4])[0] == 9994, "shp file code"
    assert struct.unpack("<i", raw[32:36])[0] == 1, "shp shape type Point"
    points, off = [], 100
    while off < len(raw):
        recnum, words = struct.unpack(">ii", raw[off:off + 8])
        content = raw[off + 8:off + 8 + words * 2]
        assert struct.unpack("<i", content[0:4])[0] == 1 and len(content) == 20
        xb, yb = content[4:12], content[12:20]
        points.append({"rownum": recnum, "x_bytes": xb.hex(), "y_bytes": yb.hex(),
                       "x": struct.unpack("<d", xb)[0], "y": struct.unpack("<d", yb)[0]})
        off += 8 + words * 2
    assert off == len(raw)
    assert [p["rownum"] for p in points] == list(range(1, len(points) + 1))
    return points


def parse_dbf(raw, columns, codec):
    numrecords = struct.unpack("<i", raw[4:8])[0]
    headerlen = struct.unpack("<h", raw[8:10])[0]
    recordlen = struct.unpack("<h", raw[10:12])[0]
    fields, off = [], 32
    while raw[off] != 0x0D:
        fd = raw[off:off + 32]
        fields.append({"name": fd[0:11].split(b"\x00")[0].decode("ascii"),
                       "type": chr(fd[11]), "length": fd[16], "decimals": fd[17]})
        off += 32
    assert [(f["name"], f["type"], f["length"], f["decimals"]) for f in fields] == \
           [(c["original_name"], c["source_type"], c["source_width_bytes"], c["source_decimals"]) for c in columns]
    base = headerlen + numrecords * recordlen
    assert len(raw) in (base, base + 1), "dbf length"
    rows, deleted, blank = [], 0, []
    for i in range(numrecords):
        rec = raw[headerlen + i * recordlen:headerlen + (i + 1) * recordlen]
        if rec[0:1] == b"\x2a":
            deleted += 1; continue
        assert rec[0:1] == b"\x20"
        values, pos = [], 1
        for f in fields:
            cell = rec[pos:pos + f["length"]]; pos += f["length"]
            if f["type"] == "C":
                values.append(cell.decode(codec, errors="strict"))
            else:
                text = cell.decode("ascii", errors="strict")
                if text.strip() == "":
                    blank.append({"rownum": i + 1, "column": f["name"]})
                values.append(text)
        rows.append(tuple(values))
    return rows, fields, numrecords, deleted, blank


def reconstruct_n(db_text, f):
    """Rebuild the original fixed-width right-aligned DBF N field text from a DB value."""
    if f["decimals"] > 0:
        return format(Decimal(db_text), f'.{f["decimals"]}f').rjust(f["length"])
    return str(int(Decimal(db_text))).rjust(f["length"])


def attr_schema(sid, columns):
    return canonical.ValueSchema(
        source_object_id=sid,
        columns=tuple(canonical.ValueColumn(column_key=c["column_id"], target_name=c["target_name"],
                                            pg_type="text", nullable=False) for c in columns)
        + (canonical.ValueColumn(column_key=canonical.ROW_KEY, target_name="__src_rownum",
                                 pg_type="bigint", nullable=False),))


def attr_stream(sid, columns, rows):
    return canonical.summarize_rows(attr_schema(sid, columns),
                                    (r + (i + 1,) for i, r in enumerate(rows)), limits=canonical.ValueLimits())


def geom_stream(sid, points):
    out = bytearray(b"XRGGEOM\x00\x01" + bytes.fromhex(sid) + struct.pack(">ib", SRID, DIMENSIONS))
    for p in points:
        out += b"\x52" + struct.pack(">Q", p["rownum"]) + bytes.fromhex(p["x_bytes"]) + bytes.fromhex(p["y_bytes"])
    out += b"\x45" + struct.pack(">Q", len(points))
    return bytes(out)


def ewkb_hex(xb, yb):
    return (b"\x01" + struct.pack("<I", 0x20000001) + struct.pack("<i", SRID)
            + bytes.fromhex(xb) + bytes.fromhex(yb)).hex()


def main():
    ev = {"version": 1, "trial_only": True, "container_name": CONTAINER, "image": IMAGE,
          "network": "none", "host_port_mapping": "none", "unique_run_identity": True,
          "fixed_name_pre_delete": False, "cleanup_scope": "only the container Id created and verified in this run",
          "pg32_pg32b_deploy_touched": False, "formal_contract_modified": False}
    insp = run(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}} | {{json .RepoDigests}}"])
    ev["image_identity"] = {"exit": insp.returncode, "id_and_digests": insp.stdout.strip()}
    cap = run(["docker", "run", "--rm", "--network", "none", IMAGE, "sh", "-c",
               "ls /usr/lib/postgresql/18/lib/postgis-3.so && ls /usr/share/postgresql/18/extension/postgis.control"])
    ev["postgis_capability_check"] = {"exit": cap.returncode, "stdout": cap.stdout.strip()}
    if cap.returncode != 0:
        ev["status"] = "POSTGIS_CAPABILITY_MISSING_STOP"
        print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    # --- source-side gates per object (before any write) ---
    pre, items = {}, []
    inv = json.loads((REL / "inventory.json").read_text())
    dbf_full = {e["archive_chain"][0]: e["sha256"] for e in inv["entries"]
                if e["relative_path"] == "harvard-full/doi_10_7910/DVN/E7HDYD/1884route.zip" and e["archive_chain"]}
    with zipfile.ZipFile(ZIP) as zf:
        for obj in OBJECTS:
            it = {"object_name": obj["object_name"], "rule_id": obj["rule_id"],
                  "source_object_id": obj["source_object_id"], "codec": obj["codec"]}
            shp_raw, dbf_raw = zf.read(obj["stem"] + ".shp"), zf.read(obj["stem"] + ".dbf")
            cpg_raw = zf.read(obj["stem"] + ".cpg")
            it["components"] = {"shp_sha_match": sha(shp_raw) == obj["shp_sha"],
                                "dbf_sha256": sha(dbf_raw), "dbf_sha_match": sha(dbf_raw) == dbf_full[obj["stem"] + ".dbf"],
                                "cpg_sha_match": sha(cpg_raw) == obj["cpg_sha"],
                                "shp_bytes_identical_across_objects": True}
            columns = ATTRS_BY_SID[obj["source_object_id"]]["source_columns"]
            points = parse_shp(shp_raw)
            rows, fields, numrecords, deleted, blank = parse_dbf(dbf_raw, columns, obj["codec"])
            n = len(points)
            # numeric reconstruction gate against raw source text (width/scale verified)
            recon_ok = all(reconstruct_n(rows[i][j], fields[j]) == rows[i][j]
                           for i in range(len(rows)) for j in range(len(fields)) if fields[j]["type"] == "N")
            s = attr_stream(obj["source_object_id"], columns, rows)
            gs = geom_stream(obj["source_object_id"], points)
            it["source_gate"] = {"row_count": n, "count_matches_59": n == KNOWN_ROWS,
                                 "deleted": deleted, "blank_numeric": blank,
                                 "attr_geom_aligned": n == numrecords == len(rows) and deleted == 0,
                                 "numeric_reconstruction_matches_raw": recon_ok,
                                 "attr_sha256": s.sha256, "attr_matches_expected": s.sha256.startswith(obj["attr_sha"]),
                                 "geom_sha256": sha(gs), "geom_matches_expected": sha(gs).startswith(obj["geom_sha"])}
            ok = (n == KNOWN_ROWS and deleted == 0 and not blank and recon_ok
                  and it["source_gate"]["attr_geom_aligned"]
                  and all(it["components"][k] for k in ("shp_sha_match", "dbf_sha_match", "cpg_sha_match"))
                  and it["source_gate"]["attr_matches_expected"] and it["source_gate"]["geom_matches_expected"])
            it["pre_write_gate"] = "PASS" if ok else "STOP"
            pre[obj["rule_id"]] = (rows, fields, points, columns) if ok else None
            items.append(it)
    ev["items"] = items
    if not all(pre.values()):
        ev["status"] = "PRE_WRITE_GATE_STOP"
        print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    # --- unique isolated temporary instance (no pre-delete) ---
    r = run(["docker", "run", "-d", "--name", CONTAINER, "--network", "none",
             "-e", "POSTGRES_PASSWORD=trial-only-not-production", "-e", "POSTGRES_DB=xiangrugu_trial", IMAGE])
    ev["container_start_exit"] = r.returncode
    if r.returncode != 0:
        ev["status"] = "CONTAINER_START_FAILED_STOP"; ev["start_stderr"] = r.stderr.strip()[:200]
        print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    cid = run(["docker", "inspect", "--format", "{{.Id}}", CONTAINER]).stdout.strip()
    cname = run(["docker", "inspect", "--format", "{{.Name}}", CONTAINER]).stdout.strip().lstrip("/")
    ev["container_id"] = cid
    ev["container_id_name_verified"] = cname == CONTAINER and len(cid) == 64
    ready = False
    for _ in range(90):
        if run(["docker", "exec", CONTAINER, "pg_isready", "-U", "postgres"]).returncode == 0:
            ready = True; break
        time.sleep(1)
    if not ready:
        ev["status"] = "PG_NOT_READY_STOP"; print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    ident = {}
    for _ in range(30):
        for key, sql in [("server_version", "SHOW server_version"), ("data_directory", "SHOW data_directory"),
                         ("start_time", "SELECT pg_postmaster_start_time()"),
                         ("inet_server_addr", "SELECT coalesce(inet_server_addr()::text,'null')"),
                         ("databases", "SELECT datname FROM pg_database ORDER BY datname")]:
            ident[key] = psql(sql, db="postgres", csv_out=True).stdout.strip()
        if all(ident.values()):
            break
        time.sleep(1)
    ev["instance_identity"] = ident
    ev["identity_verified_before_write"] = (
        ident["server_version"].startswith("18") and ident["data_directory"].startswith("/var/lib/postgresql/")
        and ident["inet_server_addr"] == "null" and "xiangrugu_trial" in ident["databases"]
        and "cbdb" not in ident["databases"] and "pg32b" not in ident["databases"]
        and ident["databases"].replace("xiangrugu_trial", "").find("xiangrugu") < 0)
    if not ev["identity_verified_before_write"]:
        ev["status"] = "IDENTITY_CHECK_FAILED_STOP"; print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    r = psql("CREATE EXTENSION postgis; CREATE SCHEMA chgis;")
    ev["extension_ddl_exit"] = r.returncode
    ev["postgis_version"] = psql("SELECT postgis_version()", csv_out=True).stdout.strip()
    if r.returncode != 0:
        ev["status"] = "EXTENSION_FAILED_STOP"; ev["ext_stderr"] = r.stderr.strip()[:200]
        print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    # --- per-object load + readback ---
    import csv, io
    total = 0
    for it in items:
        rule = it["rule_id"]
        rows, fields, points, columns = pre[rule]
        obj = next(o for o in OBJECTS if o["rule_id"] == rule)
        table = f"chgis.trial_{rule}_20261123"
        it["trial_table"] = table
        coldefs = []
        for c, f in zip(columns, fields):
            t = c["target_type_proposal"]
            coldefs.append(f'{c["target_name"]} {t}')  # nullable_approved=true DDL face
        ddl = f'CREATE TABLE {table} (' + ", ".join(coldefs) \
            + ', geom geometry(Point,4326) NOT NULL, __src_rownum bigint NOT NULL PRIMARY KEY);'
        r = psql(ddl); it["ddl_exit"] = r.returncode
        if r.returncode != 0:
            it["status"] = "STOP"; it["stop_reason"] = "ddl: " + r.stderr.strip()[:150]; continue
        buf = io.StringIO()
        w = csv.writer(buf, delimiter="\t", quotechar='"', quoting=csv.QUOTE_ALL, lineterminator="\n")
        for i, row in enumerate(rows):
            w.writerow(list(row) + [ewkb_hex(points[i]["x_bytes"], points[i]["y_bytes"]), i + 1])
        collist = ", ".join(c["target_name"] for c in columns) + ", geom, __src_rownum"
        r = run(["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "xiangrugu_trial",
                 "-v", "ON_ERROR_STOP=1", "-c",
                 f"\\copy {table} ({collist}) FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '\"')"],
                input=buf.getvalue())
        it["copy_exit"] = r.returncode
        if r.returncode != 0:
            it["status"] = "STOP"; it["stop_reason"] = "copy: " + r.stderr.strip()[:150]; continue
        sel = ", ".join(c["target_name"] for c in columns) \
            + ", ST_X(geom), ST_Y(geom), GeometryType(geom), ST_NDims(geom), ST_SRID(geom), __src_rownum"
        r = psql(f"SELECT {sel} FROM {table} ORDER BY __src_rownum", csv_out=True)
        it["readback_exit"] = r.returncode
        recs = list(csv.reader(io.StringIO(r.stdout)))
        nc = len(columns)
        # reconstruct source field text from typed DB values (width/scale)
        rebuilt, db_points, geom_meta_ok = [], [], True
        for rec in recs:
            vals = list(rec[:nc])
            for j, f in enumerate(fields):
                if f["type"] == "N":
                    vals[j] = reconstruct_n(rec[j], f)
            rebuilt.append(tuple(vals))
            xb = struct.pack("<d", float(rec[nc])).hex()
            yb = struct.pack("<d", float(rec[nc + 1])).hex()
            db_points.append({"rownum": int(rec[nc + 5]), "x_bytes": xb, "y_bytes": yb})
            geom_meta_ok &= (rec[nc + 2] == "POINT" and rec[nc + 3] == "2" and rec[nc + 4] == "4326")
        s = attr_stream(obj["source_object_id"], columns, rebuilt)
        gs = geom_stream(obj["source_object_id"], db_points)
        xy_bytes_match = all(db_points[i]["x_bytes"] == points[i]["x_bytes"]
                             and db_points[i]["y_bytes"] == points[i]["y_bytes"] for i in range(len(points)))
        raw_recon_match = all(rebuilt[i][j] == rows[i][j] for i in range(len(rows)) for j in range(nc))
        meta = list(csv.reader(io.StringIO(psql(
            "SELECT column_name, data_type, udt_name, is_nullable, ordinal_position FROM information_schema.columns "
            f"WHERE table_schema='chgis' AND table_name='trial_{rule}_20261123' ORDER BY ordinal_position",
            csv_out=True).stdout)))
        exp_meta = [[c["target_name"],
                     {"text": "text", "numeric(19,5)": "numeric", "bigint": "bigint"}[c["target_type_proposal"]],
                     {"text": "text", "numeric(19,5)": "numeric", "bigint": "int8"}[c["target_type_proposal"]],
                     "YES", str(i + 1)] for i, c in enumerate(columns)] \
            + [["geom", "USER-DEFINED", "geometry", "NO", str(nc + 1)],
               ["__src_rownum", "bigint", "int8", "NO", str(nc + 2)]]
        valcols = ", ".join(c["target_name"] for c in columns)
        dup_attr = psql(f"SELECT count(*) FROM (SELECT {valcols} FROM {table} GROUP BY {valcols} HAVING count(*)>1) d", csv_out=True).stdout.strip()
        dup_xy = psql(f"SELECT count(*) FROM (SELECT ST_X(geom), ST_Y(geom) FROM {table} GROUP BY ST_X(geom), ST_Y(geom) HAVING count(*)>1) d", csv_out=True).stdout.strip()
        nulls = psql(f"SELECT count(*) FROM {table} WHERE " + " OR ".join(f'{c["target_name"]} IS NULL' for c in columns) + " OR geom IS NULL", csv_out=True).stdout.strip()
        rn = [int(rec[nc + 5]) for rec in recs]
        ok = (r.returncode == 0 and len(recs) == KNOWN_ROWS and meta == exp_meta and geom_meta_ok
              and rn == list(range(1, 60)) and nulls == "0" and raw_recon_match and xy_bytes_match
              and s.sha256.startswith(obj["attr_sha"]) and sha(gs).startswith(obj["geom_sha"]))
        it["readback"] = {"row_count": len(recs), "columns_meta_match": meta == exp_meta,
                          "null_value_semantics": {"ddl_nullable_approved": True, "null_rows": nulls},
                          "rownum_sequence_1_59": rn == list(range(1, 60)),
                          "attr_geom_aligned_by_src_rownum": rn == [p["rownum"] for p in points],
                          "duplicate_groups_attr_value_cols": dup_attr,
                          "duplicate_groups_xy_pairs": dup_xy,
                          "duplicate_key_excludes_src_rownum": True,
                          "numeric_reconstruction_matches_source_raw": raw_recon_match,
                          "geometry_type_dims_srid_ok": geom_meta_ok,
                          "per_point_xy_original_bytes_match": xy_bytes_match,
                          "attr_stream_sha256_from_db_values": s.sha256,
                          "attr_matches_approved": s.sha256.startswith(obj["attr_sha"]),
                          "geom_stream_sha256_from_db_values": sha(gs),
                          "geom_matches_approved": sha(gs).startswith(obj["geom_sha"]),
                          "attr_stream_bytes": s.stream_bytes, "geom_stream_bytes": len(gs)}
        it["status"] = "PASS" if ok else "STOP"
        if not ok:
            it["stop_reason"] = "readback mismatch (see readback node)"
        else:
            total += len(recs)
    ev["total_rows_all_pass"] = total
    ev["all_pass"] = all(it["status"] == "PASS" for it in items)
    ev["four_digests_all_match"] = all(it.get("readback", {}).get("attr_matches_approved")
                                       and it.get("readback", {}).get("geom_matches_approved") for it in items)
    ev["status"] = "TRIAL_SPATIAL2_PASS" if ev["all_pass"] and total == 118 else "TRIAL_SPATIAL2_STOP"
    ev["first_difference"] = next(({"rule_id": it["rule_id"], "reason": it.get("stop_reason")}
                                   for it in items if it["status"] != "PASS"), None)
    print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True))
    sys.exit(0 if ev["status"] == "TRIAL_SPATIAL2_PASS" else 2)


if __name__ == "__main__":
    main()
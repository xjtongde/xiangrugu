#!/usr/bin/env python3
"""Block-4 geom raw-byte extraction from tgaz_bak_2018.sql (MySQL dump).

Protocol: zipfile binary stream; payload NEVER text-decoded. Byte-level
scan of INSERT INTO `geom` statements (multi-line aware), MySQL
backslash-escape-aware single quote boundaries. Two evidence layers per
literal: raw file bytes and MySQL-decoded payload. Geometry validation =
4-byte LE SRID + WKB. No SQL executed; source read-only; stdlib only.
"""
import hashlib
import json
import struct
import sys
import zipfile

SNAP = sys.argv[1] if len(sys.argv) > 1 else "/data"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/work/geom-extraction.json"
REL = "harvard-full/doi_10_7910/DVN/H3OB28/tgaz_bak_2018.zip"
MEMBER = "tgaz_bak_2018.sql"
EXPECT_SHA = ("4c6db692b61bdafb8d4ce00e30aff2a35fc23e6d83638b50c23dadbae75c3346")

UNESCAPE = {0x30: b"\x00", 0x27: b"'", 0x22: b'"', 0x62: b"\x08",
             0x6e: b"\n", 0x72: b"\r", 0x74: b"\t", 0x5a: b"\x1a",
             0x5c: b"\\"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def iter_lines_bytes(zf):
    """Yield (line_no, raw_line_bytes) without decoding the member."""
    with zf.open(MEMBER) as f:
        n = 0
        buf = b""
        eof = False
        while not eof:
            chunk = f.read(1 << 20)
            if not chunk:
                eof = True
            start = 0
            while True:
                i = chunk.find(b"\n", start)
                if i < 0:
                    buf += chunk[start:]
                    break
                n += 1
                yield n, (buf + chunk[start:i]).rstrip(b"\r")
                buf = b""
                start = i + 1
        if buf:
            n += 1
            yield n, buf.rstrip(b"\r")


def parse_value_tuples(region):
    """Parse VALUES region bytes at byte level into tuples of fields.
    Field = (kind, raw_lit, decoded, escapes); kind 'str'|'raw'."""
    out = []
    i = 0
    L = len(region)
    while i < L:
        p = region.find(b"(", i)
        if p < 0:
            break
        i = p + 1
        tup = []
        while i < L:
            c = region[i]
            if c == 0x27:  # '
                j = i + 1
                raw = bytearray()
                dec = bytearray()
                esc = []
                while j < L:
                    ch = region[j]
                    if ch == 0x5C:  # \
                        nxt = region[j + 1] if j + 1 < L else None
                        if nxt is None:
                            raw.append(ch)
                            esc.append("eof")
                            j += 1
                            continue
                        raw += bytes([ch, nxt])
                        if nxt in UNESCAPE:
                            dec.extend(UNESCAPE[nxt])
                        elif nxt in (0x25, 0x5F):  # \% \_ keep both chars
                            dec += bytes([ch, nxt])
                        else:                       # \x -> x (MySQL rule)
                            dec.append(nxt)
                        esc.append(chr(nxt))
                        j += 2
                        continue
                    if ch == 0x27:
                        break
                    raw.append(ch)
                    dec.append(ch)
                    j += 1
                tup.append(("str", bytes(raw), bytes(dec), esc))
                i = j + 1
            elif c in (0x2C, 0x20, 0x09, 0x0D, 0x0A):
                i += 1
            elif c == 0x29:  # )
                i += 1
                break
            else:
                j = i
                while j < L and region[j] not in (0x2C, 0x29):
                    j += 1
                tok = region[i:j].strip()
                tup.append(("raw", tok, tok, []))
                i = j
        out.append(tup)
    return out


def validate_geometry(payload):
    res = {"decoded_len": len(payload)}
    if len(payload) < 5:
        res.update(valid=False, fail_at_byte=0,
                   reason="shorter than SRID(4)+byteorder(1)")
        return res
    srid, = struct.unpack_from("<I", payload, 0)
    res["srid_prefix_le"] = srid
    bo = payload[4]
    if bo == 1:
        res["wkb_byte_order"] = "LE"
        en = "<"
    elif bo == 0:
        res["wkb_byte_order"] = "BE"
        en = ">"
    else:
        res.update(valid=False, fail_at_byte=4,
                   reason=f"invalid byte order marker {bo}")
        return res
    gt, = struct.unpack_from(en + "I", payload, 5)
    names = {1: "Point", 2: "LineString", 3: "Polygon", 4: "MultiPoint",
             5: "MultiLineString", 6: "MultiPolygon", 7: "GeometryCollection"}
    base = gt & 0x00FFFFFF
    res["geom_type_code"] = gt
    res["geom_type"] = names.get(base, f"unknown({base})")
    off = 9
    coords = []
    try:
        if base == 1:
            x, y = struct.unpack_from(en + "dd", payload, off)
            coords = [[x, y]]
            off += 16
        elif base == 2:
            npts, = struct.unpack_from(en + "I", payload, off)
            off += 4
            if len(payload) < off + npts * 16:
                raise ValueError(f"truncated linestring at {off}")
            for k in range(min(npts, 2)):
                x, y = struct.unpack_from(en + "dd", payload, off + k * 16)
                coords.append([x, y])
            off += npts * 16
            res["num_points"] = npts
        elif base == 3:
            nring, = struct.unpack_from(en + "I", payload, off)
            off += 4
            rings = []
            for _ in range(nring):
                np_, = struct.unpack_from(en + "I", payload, off)
                off += 4
                if len(payload) < off + np_ * 16:
                    raise ValueError(f"truncated ring at {off}")
                if not coords and np_:
                    x, y = struct.unpack_from(en + "dd", payload, off)
                    coords.append([x, y])
                rings.append(np_)
                off += np_ * 16
            res["polygon_rings"] = rings
        elif base == 4:
            n, = struct.unpack_from(en + "I", payload, off)
            off += 4
            need = n * (5 + 16)
            if len(payload) < off + need:
                raise ValueError(f"truncated multipoint at {off}")
            res["sub_geometry_count"] = n
            x, y = struct.unpack_from(en + "dd", payload, off + 5)
            coords = [[x, y]]
            off += need
        elif base in (5, 6, 7):
            n, = struct.unpack_from(en + "I", payload, off)
            off += 4
            res["sub_geometry_count"] = n
            # walk sub-geometries recursively but bounded: verify each header
            def walk(p0, depth):
                if depth > 3 or p0 + 5 > len(payload):
                    raise ValueError(f"cannot verify sub-header at {p0}")
                b2 = payload[p0]
                e2 = "<" if b2 == 1 else ">"
                g2, = struct.unpack_from(e2 + "I", payload, p0 + 1)
                q = p0 + 5
                t2 = g2 & 0x00FFFFFF
                if t2 == 1:
                    q += 16
                elif t2 == 2:
                    m, = struct.unpack_from(e2 + "I", payload, q)
                    q += 4 + m * 16
                elif t2 == 3:
                    m, = struct.unpack_from(e2 + "I", payload, q)
                    q += 4
                    for _ in range(m):
                        k, = struct.unpack_from(e2 + "I", payload, q)
                        q += 4 + k * 16
                elif t2 == 4:
                    m, = struct.unpack_from(e2 + "I", payload, q)
                    q += 4 + m * 21
                else:
                    raise ValueError(f"nested type {t2} unsupported walker at {p0}")
                if q > len(payload):
                    raise ValueError(f"truncated nested geometry at {q}")
                return q
            p = off
            for k in range(n):
                p = walk(p, 1)
            off = p
            res["sub_headers_verified"] = n
        else:
            raise ValueError(f"type {base} beyond simple shapes")
        res["coords_sample"] = coords[:2]
        res["consumed_bytes"] = off
        res["valid"] = (off <= len(payload))
        if not res["valid"]:
            res["first_unverifiable_byte_offset"] = off
            res["reason"] = "consumed exceeds length"
    except Exception as e:
        res["valid"] = False
        res["first_unverifiable_byte_offset"] = off
        res["reason"] = str(e)[:100]
    return res


def main():
    z = zipfile.ZipFile(SNAP + "/" + REL)
    ddl_lines = []
    in_ddl = False
    stmts = []          # (start_line, statement_bytes)
    cur = None
    total_lines = 0
    for n, line in iter_lines_bytes(z):
        total_lines = n
        if not in_ddl and line.startswith(b"CREATE TABLE `geom`"):
            in_ddl = True
        if in_ddl:
            ddl_lines.append(line.decode("utf-8", "surrogatepass"))
            if line.rstrip().endswith(b";"):
                in_ddl = False
        if cur is None:
            if line.startswith(b"INSERT INTO `geom`"):
                cur = [n, bytearray(line)]
                if line.rstrip().endswith(b";"):
                    stmts.append((cur[0], bytes(cur[1])))
                    cur = None
        else:
            cur[1] += b"\n" + line
            if line.rstrip().endswith(b";"):
                stmts.append((cur[0], bytes(cur[1])))
                cur = None
    rows = []
    unverifiable_first = None
    esc_rules_seen = set()
    for start_ln, sb in stmts:
        vpos = sb.find(b"VALUES")
        region = sb[vpos + 6:] if vpos >= 0 else b""
        for tup in parse_value_tuples(region):
            strs = [(r, d, e) for (k, r, d, e) in tup if k == "str"]
            geom_raw = geom_dec = None
            esc_all = []
            if strs:
                geom_raw, geom_dec, esc_all = max(strs, key=lambda t: len(t[1]))
                esc_all = sorted(set(esc_all))
                esc_rules_seen.update(esc_all)
            fields = [{"kind": k, "raw_len": len(r), "decoded_len": len(d),
                       "ascii_token": (d.decode("ascii", "ignore")
                                        if k == "raw" and len(d) <= 32 else None)}
                      for (k, r, d, _) in tup]
            geo = validate_geometry(geom_dec) if geom_dec is not None else None
            rec = {"sql_line": start_ln, "field_count": len(tup),
                   "fields": fields,
                   "raw_literal_sha256": sha(geom_raw) if geom_raw is not None else None,
                   "raw_literal_len": len(geom_raw) if geom_raw is not None else None,
                   "decoded_sha256": sha(geom_dec) if geom_dec is not None else None,
                   "decoded_len": len(geom_dec) if geom_dec is not None else None,
                   "escapes_found_in_geom_literal": esc_all,
                   "geometry_validation": geo}
            if geo and not geo.get("valid") and unverifiable_first is None:
                unverifiable_first = {"sql_line": start_ln,
                                      "row_index": len(rows),
                                      "byte_offset": geo.get("first_unverifiable_byte_offset"),
                                      "reason": geo.get("reason")}
            rows.append(rec)
    out = {
        "source_identity": {"relative_path": REL, "member": MEMBER,
                            "sha256_inventory": EXPECT_SHA},
        "total_sql_lines": total_lines,
        "create_table_geom_ddl_verbatim": "\n".join(ddl_lines) or None,
        "geom_insert_statements": len(stmts),
        "geom_rows": len(rows),
        "rows_verified": sum(1 for r in rows
                             if r["geometry_validation"] and r["geometry_validation"].get("valid")),
        "rows_invalid": sum(1 for r in rows
                           if r["geometry_validation"] and not r["geometry_validation"].get("valid")),
        "rows_no_geom_literal": sum(1 for r in rows if not r["geometry_validation"]),
        "first_unverifiable_position": unverifiable_first,
        "mysql_escape_rules_applied": {
            "mapped_single_char": ["\\0", "\\'", '\\"', "\\b", "\\n", "\\r", "\\t", "\\Z", "\\\\"],
            "kept_both_chars": ["\\%", "\\_"],
            "other_backslash_x": "\\x -> x",
            "escape_chars_actually_observed": sorted(esc_rules_seen)},
        "no_replacement_chars_used": True,
        "sql_not_executed": True,
        "payload_never_text_decoded": True,
        "rows": rows,
    }
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("statements:", out["geom_insert_statements"],
          "rows:", out["geom_rows"],
          "verified:", out["rows_verified"],
          "invalid:", out["rows_invalid"],
          "no-geom:", out["rows_no_geom_literal"],
          "first_unverifiable:", unverifiable_first)


main()

import json, zipfile, io, os, struct, hashlib

SNAP = "/data"
WORK = "/work"


def member_bytes(relpath, chain_parts, leaf):
    """chain_parts: slash-joined intermediate dirs/archives (may be empty),
    leaf: final member name inside the LAST archive. Progressive resolution:
    each prefix that ends with a .zip/.ZIP member is descended into."""
    raw_path = os.path.join(SNAP, relpath)
    data = None
    cur_is_file = True
    # chain_parts already holds CHAIN[:-1] as slash-joined segments and leaf
    # is the final chain element (itself possibly a multi-segment path).
    parts = ([p for p in chain_parts.split("/") if p] if chain_parts else []) \
        + [x for x in leaf.split("/") if x]
    # a "chain" element may be an empty string when the member sits directly
    # at the archive root (inventory records it as ['']); require that every
    # intermediate hop is non-empty before treating this as a plain file.
    real_hops = [x for x in parts[:-1] if x]
    if not chain_parts and len(parts) == 1 and "/" in relpath \
            and not any(x == "" for x in leaf.split("/")) \
            and outer_is_plain(relpath):
        # top-level plain file (no archive hop): read bytes directly
        with open(raw_path, "rb") as fh:
            return fh.read()
    data = None
    i = 0
    while i < len(parts):
        z = zipfile.ZipFile(raw_path) if data is None else zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist()
        # try longest remaining segment-path as a member name first
        pick = None
        for j in range(len(parts), i, -1):
            want = "/".join(parts[i:j])
            cand = [n for n in names if n == want]
            if not cand:
                cand = [n for n in names if n.lower() == want.lower()]
            if not cand and "/" in want:
                # directory-prefixed only; never grab a same-extension sibling
                cand = [n for n in names if n.endswith("/" + want)]
            if cand:
                pick = (cand[0], j)
                break
        if pick is None:
            # search deeper prefixes for an archive member to hop into
            hop = None
            for j in range(i + 1, len(parts) + 1):
                want = "/".join(parts[i:j])
                cand = [n for n in names
                        if (n == want or n.endswith("/" + want))
                        and n.lower().endswith((".zip", ".kmz"))]
                if cand:
                    hop = (cand[0], j)
                    break
            if hop is None:
                raise KeyError("/".join(parts[i:]))
            data = z.read(hop[0])
            i = hop[1]
            continue
        nm, j = pick
        if j == len(parts):
            return z.read(nm)
        if nm.lower().endswith((".zip", ".kmz")):
            data = z.read(nm)
            i = j
            continue
        raise KeyError("not-an-archive:" + nm)
    raise RuntimeError("unreachable")


def outer_is_plain(relpath):
    """True when the outer relative_path is NOT itself an archive."""
    return not relpath.lower().endswith((".zip", ".kmz"))


SHA_OK = {}


def check(outer, chain, leaf, sha, ext):
    key = outer + ("!" + "/".join(x for x in [chain, leaf] if x))
    try:
        blob = member_bytes(outer, chain, leaf)
    except Exception as e:
        return {"key": key, "ext": ext, "error": f"{type(e).__name__}: {e}"}
    obs = hashlib.sha256(blob).hexdigest()
    rec = {"key": key, "ext": ext, "sha_match": obs == sha, "size": len(blob)}
    if obs != sha:
        return rec
    try:
        if ext == ".shp":
            code, = struct.unpack_from("<i", blob, 32)
            bb = struct.unpack_from("<8d", blob, 36)
            rec["shape_type"] = code
            rec["bbox"] = bb
            rec["file_length_words"] = struct.unpack_from("<i", blob, 24)[0] * 2
        elif ext == ".dbf":
            nrec, = struct.unpack_from("<I", blob, 4)
            hlen, rlen = struct.unpack_from("<HH", blob, 8)
            nf = (hlen - 33) // 32
            flds = []
            for i in range(nf):
                off = 32 + i * 32
                nm = blob[off:off + 11].split(b"\x00")[0].decode("cp437", "replace")
                t, = struct.unpack_from("<c", blob, off + 11)
                ln, dec = blob[off + 16], blob[off + 17]
                flds.append({"name": nm, "type": t.decode(), "len": ln, "dec": dec})
            rec["dbf"] = {"records": nrec, "header_len": hlen, "record_len": rlen,
                          "fields": flds}
        elif ext in (".prj", ".cpg"):
            txt = blob[:4096].decode("utf-8", "replace")
            rec["text_head"] = txt.strip()[:600]
        elif ext == ".tab":
            txt = blob[:65536].decode("latin-1", "replace")
            head = txt.split("\n")
            # U+2028/2029 are JSON-string-safe here but splitlines-hostile;
            # normalize control chars so the .jsonl stays one record per line
            def _safe(s):
                # escape every control char incl U+0085 (NEL) and U+2028/2029:
                # Python str.splitlines() treats them as line breaks, which
                # would corrupt this one-record-per-line .jsonl.
                return "".join(ch if ord(ch) >= 0x20 and ord(ch) != 0x85
                               and ch not in "\u2028\u2029" else " "
                               for ch in s.rstrip("\r\n"))
            rec["tab_lines"] = [_safe(l) for l in head[:120]]
        elif ext in (".dat", ".map", ".ind"):
            rec["magic_head"] = blob[:16].hex()
        elif ext == "kml":
            import xml.etree.ElementTree as ET
            root = ET.fromstring(blob)
            kinds = {}
            for el in root.iter():
                t = el.tag.rsplit("}", 1)[-1]
                if t in ("Point", "LineString", "Polygon", "LinearRing",
                         "MultiGeometry", "Placemark"):
                    kinds[t] = kinds.get(t, 0) + 1
            rec["kml_elements"] = kinds
            rec["bytes"] = len(blob)
    except Exception as e:
        rec["parse_error"] = f"{type(e).__name__}: {e}"
    return rec


def main():
    tasks = json.load(open(WORK + "/tasks.json"))
    out = []
    for outer, chain, leaf, sha, ext in tasks["header_tasks"]:
        out.append(check(outer, chain, leaf, sha, ext))
    for outer, chain, leaf, sha, _ in tasks["kml_tasks"]:
        if leaf.lower().endswith(".kmz"):
            try:
                blob = member_bytes(outer, chain, leaf)
                zz = zipfile.ZipFile(io.BytesIO(blob))
                inner = [n for n in zz.namelist() if n.lower().endswith(".kml")]
                out.append({"key": outer + "!"+"/".join([chain, leaf]),
                            "ext": "kmz", "inner_kml": inner})
                for n in inner:
                    ib = zz.read(n)
                    d = dict(out[-1]); d["key"] += "#" + n
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(ib)
                    kinds = {}
                    for el in root.iter():
                        t = el.tag.rsplit("}", 1)[-1]
                        if t in ("Point", "LineString", "Polygon", "LinearRing",
                                 "MultiGeometry", "Placemark"):
                            kinds[t] = kinds.get(t, 0) + 1
                    d["kml_elements"] = kinds
                    out.append(d)
            except Exception as e:
                out.append({"key": outer + "!"+"/".join([chain, leaf]),
                            "ext": "kmz", "error": str(e)})
        else:
            out.append(check(outer, chain, leaf, sha, "kml"))
    with open(WORK + "/spatial_evidence.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    errs = sum(1 for r in out if r.get("error"))
    mism = sum(1 for r in out if r.get("sha_match") is False)
    print("records:", len(out), "errors:", errs, "sha_mismatch:", mism)


main()

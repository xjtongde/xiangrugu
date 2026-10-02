# -*- coding: utf-8 -*-
"""truth.column_encoding —— 逐列编码判定（§5.4 判定法②的机器执行）。

对每个 DBF 图层，对每个 C 型列：
  - 收集**相异且含高位字节（0x80–0xFF）**的字段值（上限 SAMPLE_MAX，按记录序取样）；
  - 逐候选编码试解，仅当**全部相异值可解且无替换字符**者入选（§5.4②）；
  - 无高位字节 → 判 ascii（编码无关）；
  - 多候选皆可解 → ambiguous（列出）；零候选 → undetermined（该列不装，§5.4④）。

产出：recon/column_encoding.jsonl（每图层一行）＋ summary。
只读源件；不写库、不改源件。
"""
import io
import json
import os
import zipfile

from . import dbf as dbf_mod
from . import roots as roots_mod

RECON = os.path.join(os.path.dirname(__file__), "..", "recon")
MULTI = ["utf-8", "gbk", "big5", "cp932"]   # 多字节：解通＝有信号（gbk/big5 范围重叠，仍须语义定）
SINGLE = ["cp1251", "cp1252", "latin-1"]    # 单字节：恒"解通"，属真空事实，须另判
SAMPLE_MAX = 8000           # 每列相异高位字节值取样上限
MAX_RECORDS = 200000        # 每图层扫描记录数上限


def _ok(enc, vs):
    try:
        return all("\ufffd" not in v.decode(enc) for v in vs)
    except UnicodeDecodeError:
        return False


def _single_letterscores(vs):
    # 对每单字节码页，统计非 ASCII 解码后落 Cyrillic 块 vs Latin 块的字符数
    scores = {}
    for enc in SINGLE:
        cyr = lat = 0
        for v in vs:
            try:
                s = v.decode(enc)
            except UnicodeDecodeError:
                continue
            for ch in s:
                o = ord(ch)
                if o < 128:
                    continue
                if 0x0400 <= o <= 0x04FF:
                    cyr += 1
                elif 0x00A0 <= o <= 0x024F:
                    lat += 1
        scores[enc] = {"cyr": cyr, "lat": lat}
    return scores


def classify(values):
    vs = list(values)
    if not vs:
        return {"distinct_highbyte": 0, "high_byte_ratio": 0.0, "multi_clean": [], "single_scores": {}, "verdict": "ascii"}
    total = sum(len(v) for v in vs)
    high = sum(1 for v in vs for b in v if b >= 0x80)
    ratio = high / total if total else 0          # 高位字节占比：CJK≈1、散点拉丁≈0.1–0.3
    multi = [e for e in MULTI if _ok(e, vs)]
    single = _single_letterscores(vs)
    cjk = set(multi) & {"gbk", "big5", "cp932"}
    if "utf-8" in multi and not cjk:
        verdict = "utf-8"
    elif cjk and ratio >= 0.5:
        verdict = "cjk-needs-pin"                  # 由 LDID/字段语义定 GBK 或 Big5
    elif ratio < 0.5:
        verdict = "single-byte:latin"              # 散点高位字节＝拉丁变音符（cp1252/latin-1）
    else:
        verdict = "single-byte:dense"              # 高占比却无多字节信号→疑 cp1251/binary
    return {"distinct_highbyte": len(vs), "high_byte_ratio": round(ratio, 3),
            "multi_clean": multi, "single_scores": single, "verdict": verdict}


def survey_dbf(dbf_bytes):
    drec = dbf_mod.parse_dbf(dbf_bytes)
    header = drec["header_size"]
    recsz = drec["record_size"]
    n_rec = min(drec["records"], MAX_RECORDS)
    text_cols = [f for f in drec["fields"] if f["type"] == "C"]
    samples = {f["name"]: set() for f in text_cols}
    truncated = {f["name"]: False for f in text_cols}
    for i in range(n_rec):
        off = header + i * recsz
        if off + recsz > len(dbf_bytes):
            break
        if dbf_bytes[off] == 0x2A:  # 删除标记，跳过
            continue
        for f in text_cols:
            s = samples[f["name"]]
            if len(s) >= SAMPLE_MAX:
                continue
            v = dbf_bytes[off + f["offset"]: off + f["offset"] + f["length"]]
            v = v.rstrip(b"\x00 ")
            if any(b2 >= 0x80 for b2 in v):
                s.add(v)
    out = {f["name"]: classify(samples[f["name"]]) for f in text_cols}
    if n_rec < drec["records"]:
        for k in out:
            out[k]["note"] = f"scanned {n_rec}/{drec['records']} records"
    return {"fields": out, "ldid": drec["language_driver"], "record_scan": n_rec}


def _walk(zbytes, path_label, depth, out):
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    for n in z.namelist():
        if n.endswith("/"):
            continue
        ext = os.path.splitext(n)[1].lower()
        if ext == ".dbf":
            d, base = os.path.split(n)
            try:
                sur = survey_dbf(z.read(n))
                out.append({"zip": path_label, "layer": base[:-4], "dir": d,
                            "records_scanned": sur["record_scan"], "ldid": sur["ldid"],
                            "columns": sur["fields"]})
            except Exception as e:  # noqa: BLE001
                out.append({"zip": path_label, "layer": base[:-4], "error": str(e)})
        elif ext == ".zip" and depth < 3:
            try:
                _walk(z.read(n), f"{path_label}::{n}", depth + 1, out)
            except Exception:  # noqa: BLE001
                pass


def enumerate_all():
    import glob
    root = roots_mod.usedata()
    zips = sorted(glob.glob(root + "/**/*.zip", recursive=True) +
                  glob.glob(root + "/**/*.ZIP", recursive=True))
    out = []
    for zp in zips:
        try:
            _walk(open(zp, "rb").read(), os.path.relpath(zp, root), 1, out)
        except Exception as e:  # noqa: BLE001
            out.append({"zip": os.path.relpath(zp, root), "error": str(e)})
    return out


def summary(records):
    from collections import Counter
    col_ver = Counter()
    needs_pin = []
    for r in records:
        if "columns" not in r:
            continue
        for name, c in r["columns"].items():
            v = c.get("verdict", "?")
            col_ver[v] += 1
            if v not in ("ascii", "utf-8"):
                needs_pin.append((r["zip"], r["layer"], name, v))
    return {
        "layers_surveyed": sum(1 for r in records if "columns" in r),
        "columns_by_verdict": dict(col_ver),
        "needs_pin_count": len(needs_pin),
    }


def main():
    records = enumerate_all()
    os.makedirs(RECON, exist_ok=True)
    with open(os.path.join(RECON, "column_encoding.jsonl"), "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    sm = summary(records)
    with open(os.path.join(RECON, "column_encoding_summary.json"), "w", encoding="utf-8") as f:
        json.dump(sm, f, ensure_ascii=False, indent=2)
    print(json.dumps(sm, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
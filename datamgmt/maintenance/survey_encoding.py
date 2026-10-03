# -*- coding: utf-8 -*-
"""survey_encoding.py —— 全量逐列编码普查（段B 判表纠偏）。

对每个 shapefile 图层的每个 C 型列，采集非空含高字节值（上限 200 样本），按
「utf-8 → gbk → big5 → cp932 → 单字节(俄/西)」阶梯判其真实编码。输出直读字节之真值，
供重排 decoding.yaml。只读源件，不写库。
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DM = os.path.dirname(_HERE)
sys.path.insert(0, _DM)

from truth import dbf  # noqa: E402
from truth import srcopen  # noqa: E402

CFG = os.path.join(_DM, "config", "sources.yaml")
OUT = os.path.join(_DM, "recon", "encoding_survey.jsonl")


def _try(s, enc):
    try:
        s.decode(enc)
        return True
    except UnicodeDecodeError:
        return False


def _ish(s, enc):
    """True=可解，或仅在**尾部**缺字节（DBF 定宽字段截断 UTF-8/GBK 末字符）。"""
    try:
        s.decode(enc)
        return True
    except UnicodeDecodeError as e:
        return e.end == len(s)


def _has_kana(samples):
    for s in samples:
        t = s.decode("cp932", "replace")
        if any(0x3040 <= ord(c) <= 0x30FF for c in t):
            return True
    return False


_RUSSIAN_MARK = ("RUS", "RUO")  # NAME_RUS / NAME_RUO / NAME_RUS_2 → 俄语西里尔(cp1251)


def _is_russian(col):
    c = col.upper()
    return any(m in c for m in _RUSSIAN_MARK)


def detect(samples, layer, col):
    """返回 'ascii'/'utf-8'/'gbk'/'big5'/'cp932'/'cp1251'/'cp1252'/'mixed'。"""
    if not samples:
        return "ascii"
    if all(_ish(s, "utf-8") for s in samples):
        return "utf-8"
    # 俄语列在 GBK 之前据名判：俄语西里尔字节常可伪解为 GBK，须语义锚定（§5.4 例证）
    if _is_russian(col):
        return "cp1251"
    if all(_ish(s, "gbk") for s in samples):
        return "gbk"
    if all(_ish(s, "big5") for s in samples):
        return "big5"
    if all(_ish(s, "cp932") for s in samples) and _has_kana(samples):
        return "cp932"
    cyr = lat = 0
    for s in samples:
        for ch in s.decode("cp1251", "replace"):
            o = ord(ch)
            if 0x0400 <= o <= 0x04FF:
                cyr += 1
            elif (o < 0x80 and ch.isalpha()) or 0x00C0 <= o <= 0x00FF:
                lat += 1
    if cyr > lat:
        return "cp1251"
    if lat > 0:
        return "cp1252"
    return "mixed"


def _survey_carrier(entries, carrier, get_dbf):
    """对某 carrier 的每个源：读 dbf 型属性字节(dbf/dat)，逐 C 列采样 detect 真编码。"""
    rows = []
    for e in entries:
        if e["carrier"] != carrier:
            continue
        if carrier == "shapefile" and e.get("geometry_only"):
            continue
        b = get_dbf(e)
        if b is None:
            continue
        fields = dbf.parse_dbf(b)["fields"]
        for i, f in enumerate(fields):
            if f["type"] != "C":
                continue
            samples = []
            for vals, deleted in dbf.iter_records(b):
                if deleted:
                    continue
                raw = vals[i].rstrip(b" \x00")
                if raw and any(x >= 0x80 for x in raw):
                    samples.append(raw)
                if len(samples) >= 200:
                    break
            enc = detect(samples, e["target"].split(".", 1)[1], f["name"])
            rows.append({"target": e["target"], "col": f["name"],
                         "detected": enc, "has_nonascii": bool(samples)})
    return rows


def main():
    entries = [json.loads(l.strip()[2:]) for l in open(CFG, encoding="utf-8")
               if l.strip().startswith("- ")]
    rows = []
    rows += _survey_carrier(entries, "shapefile",
                            lambda e: srcopen.read_member(e["key"], ".dbf", required=True))
    rows += _survey_carrier(entries, "mapinfo",
                            lambda e: srcopen.read_mapinfo_sibling(e["key"], ".dat"))

    ncol = len(rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    c = Counter(r["detected"] for r in rows if r["has_nonascii"])
    print("C 列总数:", ncol, "| 含非ASCII列数:", sum(1 for r in rows if r["has_nonascii"]))
    print("非ASCII列编码分布:", dict(c))
    print("结果落:", OUT)


if __name__ == "__main__":
    main()
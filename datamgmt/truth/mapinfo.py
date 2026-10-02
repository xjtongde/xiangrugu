# -*- coding: utf-8 -*-
"""MapInfo .tab 头解析 —— .tab 系文本头，含源对编码的声明（!charset）与字段定义。

只看头（结构＋编码声明，闸1 前身）；.dat/.map 的要素数留待阶段二（二进制）。
"""
import io
import os
import re
import zipfile

from . import roots as roots_mod

RECON = os.path.join(os.path.dirname(__file__), "..", "recon")

_CHARSET_MAP = {
    "WindowsLatin1": "cp1252", "Neutral": "cp1252?", "MacRoman": "mac-roman",
    "WindowsCyrillic": "cp1251", "WindowsArabic": "cp1256",
    "WindowsGreek": "cp1253", "WindowsHebrew": "cp1255",
    "WindowsJapanese": "cp932", "WindowsKorean": "cp949",
    "WindowsTraditionalChinese": "big5", "WindowsSimplifiedChinese": "gbk",
    "WindowsSimpChinese": "gbk", "WindowsTradChinese": "big5",
    "UTF-8": "utf-8",
}


def parse_tab_header(text: str):
    """解析 MapInfo .tab 头文本，返回 {charset, type, n_fields, fields, is_mapinfo}。"""
    if "!table" not in text and "!version" not in text:
        return {"is_mapinfo": False}
    charset = None
    mtype = None
    n_fields = None
    fields = []
    in_fields = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("!charset"):
            charset = line.split(None, 1)[1].strip().strip('"')
        m = re.match(r"Type\s+(\w+).*?Charset\s+\"?(.+?)\"?$", line)
        if m and mtype is None:
            mtype = m.group(1)
            charset = charset or m.group(2).strip('"')
        m = re.match(r"Fields\s+(\d+)", line)
        if m:
            n_fields = int(m.group(1))
            in_fields = True
            continue
        if in_fields:
            # 字段行：NAME TYPE [(width)] ;  ；遇 '  ' 或 表尾则止
            mm = re.match(r"^\s*([A-Za-z0-9_]+)\s+([A-Za-z]+)\s*(\((\d+)(?:,(\d+))?\))?\s*;?\s*$", line)
            if mm:
                fields.append({
                    "name": mm.group(1),
                    "type": mm.group(2),
                    "width": int(mm.group(4)) if mm.group(4) else None,
                    "decimals": int(mm.group(5)) if mm.group(5) else None,
                })
    return {
        "is_mapinfo": True,
        "charset_declared": charset,
        "charset_codec": _CHARSET_MAP.get(charset or "", charset),
        "type": mtype,
        "n_fields": n_fields,
        "parsed_fields": len(fields),
        "fields": fields,
    }


def _walk_zip(zbytes, path_label, depth, out):
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    for n in z.namelist():
        if n.endswith("/"):
            continue
        ext = os.path.splitext(n)[1].lower()
        if ext == ".tab":
            raw = z.read(n)
            try:
                text = raw.decode("cp1252", errors="replace")
                hdr = parse_tab_header(text)
                rec = {"zip": path_label, "member": n, "bytes": len(raw)}
                if hdr.get("is_mapinfo"):
                    rec.update(hdr)
                else:
                    rec["is_mapinfo"] = False
                    rec["note"] = "非 MapInfo（疑 delimited-text）"
                out.append(rec)
            except Exception as e:  # noqa: BLE001
                out.append({"zip": path_label, "member": n, "error": str(e)})
        elif ext == ".zip" and depth < 3:
            try:
                _walk_zip(z.read(n), f"{path_label}::{n}", depth + 1, out)
            except Exception:  # noqa: BLE001
                pass


def enumerate_mapinfo():
    import glob
    root = roots_mod.usedata()
    zips = sorted(glob.glob(root + "/**/*.zip", recursive=True) +
                  glob.glob(root + "/**/*.ZIP", recursive=True))
    out = []
    for zp in zips:
        try:
            _walk_zip(open(zp, "rb").read(), os.path.relpath(zp, root), 1, out)
        except Exception as e:  # noqa: BLE001
            out.append({"zip": os.path.relpath(zp, root), "error": str(e)})
    return out


def main():
    rows = enumerate_mapinfo()
    import json
    os.makedirs(RECON, exist_ok=True)
    p = os.path.join(RECON, "mapinfo_baseline.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
    from collections import Counter
    mi = [r for r in rows if r.get("is_mapinfo")]
    deltxt = [r for r in rows if not r.get("is_mapinfo")]
    cs = Counter((r.get("charset_declared"), r.get("charset_codec")) for r in mi)
    print(json.dumps({
        "mapinfo_tables": len(mi),
        "delimited_text_tab": len(deltxt),
        "charset_declared": {f"{a}({b})": n for (a, b), n in cs.items()},
        "with_fields_parsed": sum(1 for r in mi if r.get("parsed_fields")),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
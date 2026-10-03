# -*- coding: utf-8 -*-
"""decode.py —— 只做解码判定表的**读取**（config 层，与 roots.py 同级）。

§6.1 独立性：字节→字符的「列级解码实现」由 importer/load.py 与 verifier/verify.py
各自独立写一遍；此处仅把 decoding.yaml 解析成 `families[id] → {default, exceptions}`，
供两侧各自按同一份判表实现解码，绝不替谁解码。
"""
import os
import re

_DEC_CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "decoding.yaml")


def load_decoding():
    """解析 decoding.yaml → dict[族id] = {"default": enc|None, "exceptions": {enc:[列名]}}。

    只认已知结构（缩进 2/4/6），无 pyyaml 依赖。
    """
    fams = {}
    cur = None
    section = None
    for ln in open(_DEC_CFG, encoding="utf-8").read().splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        indent = len(ln) - len(ln.lstrip(" "))
        if indent == 2 and s.startswith("- id:"):
            fid = s[len("- id:"):].strip().strip('"')
            fams[fid] = {"default": None, "exceptions": {}}
            cur, section = fid, None
            continue
        if cur is None:
            continue
        if indent == 4 and s.startswith("default:"):
            section = "default"
        elif indent == 4 and s.startswith("exceptions:"):
            section = "exceptions"
        elif indent == 4:
            section = None
        elif indent == 6 and section == "default" and s.startswith("encoding:"):
            fams[cur]["default"] = s[len("encoding:"):].strip().strip('"')
        elif indent == 6 and section == "exceptions":
            m = re.match(r'"([^"]*)"\s*:\s*\[(.*)\]', s)
            if m:
                cols = [c.strip().strip('"') for c in m.group(2).split(",") if c.strip()]
                fams[cur]["exceptions"][m.group(1)] = cols
    return fams


def col_encoding(fam, colname):
    """按判表给单列定编码；判不定（default=None）→ None（该列不装）。"""
    if fam is None:
        return None
    for enc, cols in fam["exceptions"].items():
        if colname in cols:
            return enc
    return fam["default"]
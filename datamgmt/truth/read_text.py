# -*- coding: utf-8 -*-
"""纯文本分列文件（.tab/.csv/.tsv 等）结构探测 —— 直读字节，测编码＋行/列。"""


def sniff_encoding(b: bytes):
    s = b[:8192]
    for name in ("utf-8", "gbk", "big5", "gb18030", "cp1251", "cp932"):
        try:
            s.decode(name)
            return "utf8" if name == "utf-8" else name
        except UnicodeDecodeError:
            pass
    return "latin1_or_binary"


def guess_delimiter(line: str):
    for d in ("\t", ",", ";", "|"):
        if d in line:
            return d
    return None


def probe_dsv(path: str, max_preview: int = 80):
    """返回 {path, bytes, encoding, rows_total, cols_first_line, delimiter, first_line}。

    rows_total＝去尾空行后的物理行数；首行是否为表头留给阶段二判定，此处仅照实记录。
    """
    with open(path, "rb") as f:
        raw = f.read()
    enc = sniff_encoding(raw)
    text = raw.decode("utf-8" if enc == "latin1_or_binary" else enc, errors="replace")
    lines = [l.rstrip("\r") for l in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    first = lines[0] if lines else ""
    delim = guess_delimiter(first)
    cols = len(first.split(delim)) if delim else (1 if first else 0)
    return {
        "path": path,
        "bytes": len(raw),
        "encoding": enc,
        "rows_total": len(lines),
        "cols_first_line": cols,
        "delimiter": repr(delim),
        "first_line": first[:max_preview],
    }


import csv as _csv
import io as _io
import re as _re

_INT_RE = _re.compile(r"^-?\d+$")
_NUM_RE = _re.compile(r"^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$")
_LEADZERO_RE = _re.compile(r"^-?0[0-9]")


def decode_full(b: bytes):
    """整文件定编码：utf-8（去 BOM）→ gbk → big5。均不入 → utf-8 容错。"""
    for name in ("utf-8", "gbk", "big5"):
        try:
            b.decode(name)
            return "utf-8" if name == "utf-8" else name
        except UnicodeDecodeError:
            continue
    return "utf-8"


def read_tsv(path: str, encoding: str = "utf-8"):
    """读 TAB 分列（含引号/内嵌换行）：返回 (colnames, rows)。

    rows 元素为 list[str|None]；空字段→None。表头去掉 BOM；尾随空表头列（源件末列分隔符) 一并裁掉。
    """
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode(encoding)
    reader = _csv.reader(_io.StringIO(text), delimiter="\t")
    it = iter(reader)
    header = next(it, None)
    if header is None:
        return [], []
    header = [h.lstrip("\ufeff") for h in header]
    while header and header[-1].strip() == "":
        header.pop()
    ncols = len(header)
    rows = []
    for r in it:
        if not r or (len(r) == 1 and r[0].strip() == ""):
            continue
        r = r[:ncols]
        r += [""] * (ncols - len(r))
        rows.append([(None if c == "" else c) for c in r])
    return header, rows


def sniff_pg_types(colnames, rows):
    """§5.3 文本源逐列嗅探：全整数→bigint；全数值→numeric；否则 text。确定性（同文件同结果）。

    含前导零的值（如代码 00110）一律按 text 保字面，绝不为 bigint 丢前导零（R-08）。"""
    types = {}
    for i, name in enumerate(colnames):
        vals = [r[i] for r in rows if i < len(r) and r[i] is not None]
        if not vals:
            types[name] = "text"
        elif all(_INT_RE.match(v) for v in vals) and not any(_LEADZERO_RE.match(v) for v in vals):
            types[name] = "bigint"
        elif all(_NUM_RE.match(v) for v in vals):
            types[name] = "numeric"
        else:
            types[name] = "text"
    return types
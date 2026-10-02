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
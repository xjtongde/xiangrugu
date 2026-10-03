# -*- coding: utf-8 -*-
"""verifier.verify —— 六道闸之 闸1/2/3（腿A sqlite 先行），与 importer.load **零共用代码**。

独立性（§6.1）：期望值一律由 truth/ 直读源件字节现算，绝不取自已装载之库计数；
　载具（db.py）系驱动器层共用，业务读值/真值/比对各自独立实现。

闸3 值级：类型感知多重集差集（§6.3 行哈希多重集）；null 用哨兵 '␀'(U+2400) 显式化。
库侧读值经 -F'|' —— 前提：本表值不含管道符/换行（段A NIAN_HAO 满足；违者 assert 即停，另行换 COPY TO csv）。"""
import json
import os
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATAMGMT = os.path.dirname(_HERE)
if _DATAMGMT not in sys.path:
    sys.path.insert(0, _DATAMGMT)

from db import rows, quote_ident  # noqa: E402
from truth import roots, sqlite  # noqa: E402

USEDATA = roots.usedata()
CFG = os.path.join(_DATAMGMT, "config", "sources.yaml")
NULL_SENT = "\u2400"  # ␀ SYMBOL FOR NULL


def load_entries():
    out = []
    with open(CFG, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s.startswith("- "):
                out.append(json.loads(s[2:]))
    return out


def _canon(v):
    """源值 → 库侧可比字符串。None→哨兵；bytes→hex；int/float/str→str()。"""
    if v is None:
        return NULL_SENT
    if isinstance(v, bytes):
        return "\\x" + v.hex()
    return str(v)


def verify_sqlite(db, entry):
    schema, tname = entry["target"].split(".", 1)
    tname = tname.lower()
    nas_path, table = entry["key"].split("::", 1)
    path = os.path.join(USEDATA, nas_path)

    colnames, srows = sqlite.read_values(path, table)
    pg_types = [entry["columns"][c] for c in colnames]
    sq, st = quote_ident(schema), quote_ident(tname + "__stg")

    # 闸1 结构：库列集 vs 源列集 差集须空（按序取库列，比名字）
    dbcols = rows(db, (
        f"SELECT column_name, data_type FROM information_schema.columns "
        f"WHERE table_schema='{schema}' AND table_name='{tname}__stg' "
        f"ORDER BY ordinal_position;"
    ))
    expect_names = [c.lower() for c in colnames]
    got_names = [r[0] for r in dbcols]
    g1_pass = (got_names == expect_names)
    if not g1_pass:
        return {"table": f"{schema}.{tname}", "verdict": "FAIL", "stopped_at": "g1",
                "g1_structure": {"pass": False, "expect": expect_names, "got": got_names}}

    # 闸2 计数
    cnt = int(rows(db, f"SELECT count(*) FROM {sq}.{st};")[0][0])
    g2_pass = (cnt == len(srows))
    if not g2_pass:
        return {"table": f"{schema}.{tname}", "verdict": "FAIL", "stopped_at": "g2",
                "g2_count": {"pass": False, "expect": len(srows), "got": cnt}}

    # 闸3 值级：类型感知多重集
    # 源侧
    for r in srows:
        assert all("\n" not in _canon(v) and "|" not in _canon(v) for v in r), \
            f"{table} 值含 '|' 或换行：段A -F'|' 读法不适用"
    src_multi = Counter(tuple(_canon(v) for v in r) for r in srows)

    selexpr = ", ".join(
        f"COALESCE({quote_ident(c.lower())}::text,'{NULL_SENT}')" for c in colnames
    )
    db_rows = rows(db, f"SELECT {selexpr} FROM {sq}.{st};")
    db_multi = Counter(tuple(r) for r in db_rows)

    d1 = src_multi - db_multi   # 源有库无（欠装）
    d2 = db_multi - src_multi   # 库有源无（多装/改写）
    g3_pass = (not d1 and not d2)

    return {
        "table": f"{schema}.{tname}",
        "g1_structure": {"pass": g1_pass, "expect": expect_names, "got": got_names},
        "g2_count": {"pass": g2_pass, "expect": len(srows), "got": cnt},
        "g3_value": {"pass": g3_pass, "diff_src_only": len(d1), "diff_db_only": len(d2),
                     "samples_src_only": list(d1)[:5], "samples_db_only": list(d2)[:5]},
        "verdict": "CONFORMS" if g3_pass else "FAIL",
    }


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "cbdb_reh"
    entries = load_entries()
    e = next(x for x in entries if x["carrier"] == "sqlite" and x["target"].endswith("NIAN_HAO"))
    print(json.dumps(verify_sqlite(db, e), ensure_ascii=False, indent=2))
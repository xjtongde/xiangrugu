# -*- coding: utf-8 -*-
"""SQLite（CBDB 等）结构探测 —— 只读连接，取每张表/视图的列集与行数。"""
import sqlite3


def probe_sqlite(path: str):
    """返回 [{name, kind, rows, columns:[(cid,name,type,notnull)]}]，按名排序。

    仅读 sqlite_master；禁写（mode=ro）。
    """
    uri = f"file:{path}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        rows = con.execute(
            "SELECT name, type FROM sqlite_master "
            "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        out = []
        for name, kind in rows:
            if kind == "table":
                cnt = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                cols = [
                    {"cid": r[0], "name": r[1], "type": r[2], "notnull": r[3]}
                    for r in con.execute(f'PRAGMA table_info("{name}")').fetchall()
                ]
                out.append({"name": name, "kind": "table", "rows": cnt, "columns": cols})
            else:
                out.append({"name": name, "kind": "view", "rows": None, "columns": None})
        return out
    finally:
        con.close()


def read_values(path: str, table: str):
    """直读某表全部行，返回 (colnames, rows)。

    值忠实原样：None / int / float / str / bytes（sqlite3 原生类型，不二次转换）。
    行序＝自然 rowid 序（与 count 一致）。
    """
    uri = f"file:{path}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        cur = con.execute(f'SELECT * FROM "{table}"')
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return cols, list(rows)
    finally:
        con.close()
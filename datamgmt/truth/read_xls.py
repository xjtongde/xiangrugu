# -*- coding: utf-8 -*-
"""truth.read_xls —— 直读老式 .xls(BIFF/OLE2) 用 xlrd，产出 schema 供 sources.yaml（阶段二）与装载（阶段三 leg C）。

用法：需 xlrd（隔离装于 /tmp/xlsdeps，PYTHONPATH=/tmp/xlsdeps）。
纪律：只读源件；"绝不让工具猜"——表头行、跳过行、空分隔列、列类型都在本文件的
XLS_SPEC 里按文件逐一显式登记；不在 spec 的文件一律返回"未登记，不装"。
"""
import json
import os

USEDATA = "/mnt/wd61workmetadata/usedata"
RECON = os.path.join(os.path.dirname(__file__), "..", "recon")

# 每文件一 spec（§5.2 leg C 逐列声明）：
#   sheet / header_row(表头行号,0起) / skip_after_header(尾注行? 暂0)
#   drop_cols = 空分隔列（同名 '' 无数据）
#   columns = [name, pg_type, note]
XLS_SPEC = {
    "harvard-full/doi_10_7910/DVN/EOH3FV/1999_gb_pop_uce.xls": {
        "sheet": "adm3", "header_row": 3, "drop_cols": [],
        "columns": [
            ("GB_Code_99", "text", "GB/T 2260 1999 县级代码，保前导零；1格被源件存为数字(232700)"),
            ("PINYIN_NAME", "text", "县级名拼音"),
            ("PROVINCE", "text", "省名"),
            ("PREFECTURE", "text", "地级名"),
            ("POP_1999_C", "bigint", "1999 人口数(整数值，格内为浮点)"),
            ("POP_NOTE_1999", "text", "稀疏备注，全表约18格"),
        ],
    },
    "harvard-full/doi_10_7910/DVN/PRCLTU/THDL_ADMareas_rev022401.xls": {
        "sheet": "THDL_ADMareas", "header_row": 0,
        "drop_cols": [10, 11, 15, 19],  # 空表头分隔列
        "columns": [
            ("Prov_ID", "text", "省码，混合型(5数字+1文本)，按文本保字面"),
            ("Prov_Name", "text", "省名"),
            ("Prov_Seat", "text", "省政府驻地"),
            ("Pref_ID", "text", "地级码，按文本保字面"),
            ("Pref_Name", "text", "地级名"),
            ("Pref_Seat", "text", "地级驻地"),
            ("GB_91", "text", "GB 1991 县级代码，按文本保字面"),
            ("Cnty_Name_91", "text", "1991 县名"),
            ("Cnty_Seat_ID", "text", "县驻地码"),
            ("Cnty_Seat_Name", "text", "县驻地名"),
            ("CG_91-95", "text", "91→95 变更标记(N=未变)"),
            ("New_Name_95", "text", "1995 新名"),
            ("GB_95", "text", "GB 1995 县级代码"),
            ("CG_95-99", "text", "95→99 变更标记"),
            ("New_Name_99", "text", "1999 新名"),
            ("GB_99", "text", "GB 1999 县级代码"),
            ("PY_ALT_99", "text", "拼音别名(112格非空)"),
        ],
    },
}


def read_schema(relpath, xlrd):
    if relpath not in XLS_SPEC:
        return {"path": relpath, "registered": False,
                "note": "未在 XLS_SPEC 登记，不装（宁缺勿错）"}
    sp = XLS_SPEC[relpath]
    wb = xlrd.open_workbook(os.path.join(USEDATA, relpath), on_demand=True)
    sh = wb.sheet_by_name(sp["sheet"])
    hdr = [str(sh.cell_value(sp["header_row"], i)).strip()
           for i in range(sh.ncols)]
    # 校验 spec 列名与表头一致
    assert hdr[0].lower().replace(" ", "_") == sp["columns"][0][0].lower(), \
        (relpath, hdr, sp["columns"][0])
    cols = [{"name": n, "pg_type": t, "note": no}
            for (n, t, no) in sp["columns"]]
    return {
        "path": relpath, "registered": True, "sheet": sp["sheet"],
        "nrows": sh.nrows, "ncols": sh.ncols,
        "header_row": sp["header_row"],
        "data_rows": sh.nrows - sp["header_row"] - 1,
        "drop_cols": sp["drop_cols"],
        "columns": cols,
    }


def _cell_str(cell, pg_type, xlrd):
    """xls 单元格 → str|None：空/白→None；bigint→int 化；数值列去尾 .0；其余字面。"""
    ct = cell.ctype
    if ct in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return None
    v = cell.value
    if pg_type == "bigint":
        return str(int(v))
    if ct == xlrd.XL_CELL_NUMBER:
        if isinstance(v, float) and v == int(v):
            return str(int(v))
        return repr(v)
    return str(v)


def read_cells(relpath, xlrd):
    """按 XLS_SPEC 读数据行（表头行之后，跳过 drop_cols）→ (colnames, rows)。"""
    sp = XLS_SPEC[relpath]
    wb = xlrd.open_workbook(os.path.join(USEDATA, relpath), on_demand=True)
    sh = wb.sheet_by_name(sp["sheet"])
    keep = [i for i in range(sh.ncols) if i not in sp["drop_cols"]]
    colnames = [n for (n, t, no) in sp["columns"]]
    assert len(keep) >= len(colnames), (relpath, keep, colnames)
    rows = []
    for r in range(sp["header_row"] + 1, sh.nrows):
        vals = []
        for ci, (n, t, no) in enumerate(sp["columns"]):
            cell = sh.cell(r, keep[ci])
            vals.append(_cell_str(cell, t, xlrd))
        rows.append(vals)
    return colnames, rows


def main():
    import xlrd
    out = [read_schema(p, xlrd) for p in XLS_SPEC]
    os.makedirs(RECON, exist_ok=True)
    with open(os.path.join(RECON, "xls_baseline.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    for o in out:
        print(json.dumps(o, ensure_ascii=False))


if __name__ == "__main__":
    main()
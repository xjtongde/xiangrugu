"""Independent unordered value verification, numeric-normalised.

The first attempt compared raw text and reported 6028 differences; that was MY
artefact, not a data problem: (a) I keyed a dict on one column so 3859 rows collapsed
to 1703 keys, and (b) double precision renders `0.0` from the payload as `0` on readback.
Here every cell is normalised by type before comparison, and rows are compared as a
MULTISET so duplicates cannot be silently merged.
"""
import pathlib, subprocess, sys
from collections import Counter

host = sys.argv[1]
INT = ["c_u5f_inst_u5f_name_u5f_code", "c_u5f_inst_u5f_code",
       "c_u5f_inst_u5f_addr_u5f_type_u5f_code", "c_u5f_inst_u5f_addr_u5f_begin_u5f_year",
       "c_u5f_inst_u5f_addr_u5f_end_u5f_year", "c_u5f_inst_u5f_addr_u5f_id"]
FLOAT = ["inst_u5f_xcoord", "inst_u5f_ycoord"]
TXT = ["c_u5f_source", "c_u5f_pages", "c_u5f_notes"]
order = INT + FLOAT + TXT

proj = ", ".join(
    ("coalesce(%s::text,'\\N')" % c) if c in TXT else
    ("coalesce(%s::float8::numeric(40,10)::text,'\\N')" % c) if c in FLOAT else
    ("coalesce(%s::text,'\\N')" % c) for c in order)
sql = "select %s from cbdb.cbdb__social_u5f_institution_u5f_addr" % proj
out = subprocess.run(["psql", "-h", host, "-p", "5432", "-U", "xrg_loader",
                      "-d", "xiangrugu_iso", "-tA", "-F", "\t", "-c", sql],
                     capture_output=True, text=True)
if out.returncode != 0:
    print("DUMP_FAILED", out.stderr[:300]); sys.exit(1)


def norm_int(v):
    return None if v == r"\N" else str(int(v))


def norm_float(v):
    return None if v == r"\N" else str(float(v))


def norm_txt(v):
    return None if v == r"\N" else v


def key(vals):
    n = []
    for c, v in zip(order, vals):
        n.append(norm_int(v) if c in INT else norm_float(v) if c in FLOAT else norm_txt(v))
    return tuple(n)


db = Counter(key(l.split("\t")) for l in out.stdout.splitlines() if l)
pl_raw = pathlib.Path("/data/var/b-batch/payload.bin").read_bytes().split(b"\n")
pl = Counter(key([c.decode() for c in r.split(b"\t")]) for r in pl_raw if r)

print("db rows      =", sum(db.values()))
print("payload rows =", sum(pl.values()))
only_db = sum((db - pl).values())
only_pl = sum((pl - db).values())
print("unordered difference (multiset) =", only_db + only_pl)
print("rows only in DB     =", only_db)
print("rows only in payload=", only_pl)
for x in list((db - pl).items())[:2]:
    print("  DB-only:", str(x[0])[:150])
for x in list((pl - db).items())[:2]:
    print("  PAY-only:", str(x[0])[:150])
print("NULL fidelity: db null cells =",
      sum(1 for k in db.elements() for v in k if v is None),
      " payload null cells =", sum(1 for k in pl.elements() for v in k if v is None))
print("VERDICT:", "VALUES_EQUAL" if only_db + only_pl == 0 else "VALUES_DIFFER")

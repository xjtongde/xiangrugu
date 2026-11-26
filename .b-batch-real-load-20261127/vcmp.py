import json
from xiangrugu_datamgmt.unordered_validate import UnorderedEvidence, UnorderedInput, compare_unordered
from xiangrugu_datamgmt.unordered_values import UnorderedColumn, UnorderedSchema
from xiangrugu_datamgmt.value_sort import UnorderedLimits
from xiangrugu_datamgmt.sqlite_values import open_sqlite_values
IN=json.load(open('/data/var/in/inputs.json')); obj=IN['approved']
schema=UnorderedSchema(obj['source_object_id'], tuple(UnorderedColumn(**c) for c in obj['columns']))
TYPES=[c['pg_type'] for c in IN['target']['columns']]
def src():
    with open_sqlite_values('/mnt/wd61workmetadata/usedata/harvard/cbdb/cbdb_20260919.sqlite3',
        expected_size=586485760, expected_sha256='bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400',
        relative_path='harvard/cbdb/cbdb_20260919.sqlite3', table='SOCIAL_INSTITUTION_ADDR',
        source_columns=tuple(obj['source_columns']), schema=schema) as st:
        for row in st: yield tuple(row)
rows=[]
for line in open('/data/var/work/payload.bin','rb').read().split(b'\n'):
    if not line: continue
    out=[]
    for c,t in zip(line.split(b'\t'),TYPES):
        v=c.decode()
        out.append(None if v=='\\N' else (int(v) if t=='bigint' else (float(v) if t=='double precision' else v)))
    rows.append(tuple(out))
def tgt():
    for r in rows: yield r
SHA='2cb8c354b0e75e6ae230e3b00540146e823eaa8de8def2abce89ad6179a07579'
SEV=UnorderedEvidence("source",schema.source_object_id,SHA)
TEV=UnorderedEvidence("target","cbdb.cbdb__social_u5f_institution_u5f_addr",SHA)
rep=compare_unordered(schema, UnorderedInput(schema=schema,rows=src(),evidence=SEV),
                      UnorderedInput(schema=schema,rows=tgt(),evidence=TEV),
                      limits=UnorderedLimits(), scratch_parent="/data/var")
d=rep.to_dict()
print(json.dumps({k:d.get(k) for k in ("result","error_code","source_sha256","target_sha256","source_count","target_count","missing_rows","excess_rows")},ensure_ascii=False,indent=1))

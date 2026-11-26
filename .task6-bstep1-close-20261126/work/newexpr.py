"""新模型表达力测试：11 列（含 2 列 double precision）+ 有序复合主键。"""
import json, sys, pathlib
sys.path.insert(0, '/tmp/a01pkg')
from xiangrugu_datamgmt_new.contracts import ReleaseContract, ColumnMapping, PrimaryKey, ObjectTarget

box = pathlib.Path('/tmp/a01pkg')
draft = json.load(open(box/'b-contract-draft.json'))
tgt = draft['rules'][0]['targets'][0]
appr = json.load(open(box/'b-approval-table.json'))

out = {}
bad = []
for c in tgt['columns']:
    try:
        ColumnMapping(**c)
    except Exception as e:
        bad.append({'column': c['source_column'], 'pg_type': c['pg_type'], 'error': str(e).splitlines()[:2]})
out['columns_rejected'] = bad
out['all_11_columns_accepted'] = len(bad) == 0
out['double_precision_columns'] = [c['source_column'] for c in tgt['columns'] if c['pg_type'] == 'double precision']

pk_rows = sorted([r for r in appr['columns'] if r['source_pk_position'] > 0],
                 key=lambda x: x['source_pk_position'])
pk_order = [r['source_column'] for r in pk_rows]
name_by_src = {r['source_column']: r['target_name_candidate'] for r in appr['columns']}
pk_targets = [name_by_src[s] for s in pk_order]
out['source_pk_order'] = pk_order
out['target_pk_order'] = pk_targets
pk = PrimaryKey(columns=tuple(pk_targets))
out['primary_key_accepted'] = True
out['pk_column_count'] = len(pk.columns)

t2 = dict(tgt)
t2['primary_key'] = {'columns': pk_targets}
obj = ObjectTarget(**t2)
out['object_target_accepted'] = True
out['pk_preserved_order'] = list(obj.primary_key.columns) == pk_targets

try:
    cols = [dict(c) for c in tgt['columns']]
    for c in cols:
        if c['target_column'] in pk_targets:
            c['nullable'] = True
    ObjectTarget(object_name=tgt['object_name'], schema=tgt['schema'], table=tgt['table'],
                 expected_count=tgt['expected_count'], expected_sha256=tgt['expected_sha256'],
                 columns=cols, primary_key={'columns': pk_targets})
    out['nullable_pk_rejected'] = 'NO (BUG)'
except Exception:
    out['nullable_pk_rejected'] = 'YES'

try:
    t3 = dict(tgt); t3['primary_key'] = {'columns': ['not_a_column']}
    ObjectTarget(**t3)
    out['unmapped_pk_rejected'] = 'NO (BUG)'
except Exception:
    out['unmapped_pk_rejected'] = 'YES'

try:
    PrimaryKey(columns=(pk_targets[0], pk_targets[0]))
    out['duplicate_pk_rejected'] = 'NO (BUG)'
except Exception:
    out['duplicate_pk_rejected'] = 'YES'

full = json.loads(json.dumps(draft))
full['rules'][0]['targets'][0]['primary_key'] = {'columns': pk_targets}
try:
    m = ReleaseContract.model_validate(full)
    out['full_contract_validated'] = True
    out['full_contract_columns'] = len(m.rules[0].targets[0].columns)
    out['full_contract_sha256'] = m.sha256
    out['full_contract_canonical_len'] = len(m.canonical_bytes())
except Exception as e:
    out['full_contract_validated'] = f'REJECTED: {str(e).splitlines()[:4]}'
print(json.dumps(out, ensure_ascii=False, indent=1))

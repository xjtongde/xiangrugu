import json, sys, hashlib, pathlib
sys.path.insert(0, '/tmp/a01pkg')
from xiangrugu_datamgmt_patched.contracts import ReleaseContract, contract_schema, validate_contract_document
BOX = pathlib.Path('/tmp/a01pkg')
out = json.load(open(BOX/'cand_out.json'))
cand = out['candidate']
res = {}
try:
    m = ReleaseContract.model_validate(json.loads(json.dumps(cand)))
    res['validated'] = True
    res['sha256'] = m.sha256
    res['canonical_len'] = len(m.canonical_bytes())
    t = m.rules[0].targets[0]
    res['columns'] = len(t.columns)
    res['ordinals'] = [c.ordinal for c in t.columns]
    res['double_precision'] = [c.source_column for c in t.columns if c.pg_type == 'double precision']
    res['nullable_count'] = sum(1 for c in t.columns if c.nullable)
    res['pk'] = list(t.primary_key.columns)
    res['expected_count'] = t.expected_count
    res['expected_sha256'] = t.expected_sha256
except Exception as e:
    res['validated'] = False
    res['error'] = str(e).splitlines()[:6]
# schema 域校验
try:
    validate_contract_document(json.loads(json.dumps(cand)), contract_schema())
    res['schema_domain_ok'] = True
except Exception as e:
    res['schema_domain_ok'] = f'REJECTED: {str(e).splitlines()[:3]}'
print(json.dumps(res, ensure_ascii=False, indent=1))

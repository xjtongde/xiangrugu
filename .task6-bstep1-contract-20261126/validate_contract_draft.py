"""用正式 ReleaseContract 模型校验 B 批合同草案，并逐项定位不可表达处。"""
import json, sys, pathlib
sys.path.insert(0,'/workspace/datamgmt/src')
from xiangrugu_datamgmt.contracts import ReleaseContract, ColumnMapping, ObjectTarget

box=pathlib.Path('/tmp/a01box')
draft=json.load(open(box/'b-contract-draft.json'))
out={}
# 1) 逐列建模测试，定位不可表达列
bad=[]
for c in draft['rules'][0]['targets'][0]['columns']:
    try:
        ColumnMapping(**c)
    except Exception as e:
        bad.append({'column':c['source_column'],'pg_type':c['pg_type'],
                    'error':[l for l in str(e).splitlines() if 'pattern' in l or 'String should' in l][:1]})
out['columns_rejected_by_model']=bad
out['ordinal_contiguity_required_by_model']=True  # 由 subset 重建序数才通过所证
# 2) 剔除不可表达列后重建连续序数（模型要求 1..N 连续，见 G6），检验其余能否完整通过
d2=json.loads(json.dumps(draft))
cols=d2['rules'][0]['targets'][0]['columns']
keep=[c for c in cols if c['pg_type'] in ('text','bigint')]
for i,c in enumerate(keep,start=1): c['ordinal']=i
d2['rules'][0]['targets'][0]['columns']=keep
try:
    m=ReleaseContract.model_validate(d2)
    out['subset_without_double_precision']='VALIDATED_OK'
    out['subset_column_count']=len(keep)
    out['subset_canonical_sha256']=m.sha256
except Exception as e:
    out['subset_without_double_precision']=f'REJECTED: {str(e).splitlines()[:6]}'
# 3) 全量草案校验（预期因 double precision 失败）
try:
    m=ReleaseContract.model_validate(draft)
    out['full_draft']='VALIDATED_OK'
    out['full_canonical_sha256']=m.sha256
except Exception as e:
    lines=[l for l in str(e).splitlines() if 'String should match' in l or 'pg_type' in l]
    out['full_draft']=f'REJECTED_AS_EXPECTED: {lines[:2]}'
print(json.dumps(out,ensure_ascii=False,indent=1))

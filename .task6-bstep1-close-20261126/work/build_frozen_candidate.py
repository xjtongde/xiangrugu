"""B 批单表冻结候选生成器（确定性，可从仓内输入复现）。

输入：本盒已批准的审批表 + 源 DDL 实测探针 + 命名碰撞检查结果
硬断言：11 列原序不删列 / 2 列 double precision / 6 列有序复合主键 / 3859 / 重复 0 / 2cb8c354
"""
import json, hashlib, pathlib, sys

BOX = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
OUT = BOX

def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()

appr = json.load(open(BOX / 'b-approval-table-v2.json'))
probe = json.load(open(BOX / 'source-ddl-probe.json'))
coll = json.load(open(BOX / 'collision-check.json'))

EXPECTED_SHA = '2cb8c354b0e75e6ae230e3b00540146e823eaa8de8def2abce89ad6179a07579'
EXPECTED_ROWS = 3859
DUPLICATES = 0
INVENTORY_SHA = 'fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db'

# ---- 硬断言：授权与源实测 ----
assert appr['column_count'] == 11, appr['column_count']
assert appr['source_row_count'] == EXPECTED_ROWS == probe['rows']
assert len(appr['columns']) == 11
r62 = appr['r62_readback_cross_check']
assert r62['duplicate_rows'] == DUPLICATES
assert r62['source_sha256'] == EXPECTED_SHA == r62['target_sha256']
assert r62['missing_rows'] == 0 and r62['excess_rows'] == 0
assert r62['comparison_result'] == 'comparison_equal'
assert appr['source_ddl_sha256'] == probe['ddl_sha256']
assert coll['verdict'] == 'PASS_NO_COLLISION_STOP_NOT_TRIGGERED'

cols = sorted(appr['columns'], key=lambda c: c['column_ordinal_1based'])
assert [c['column_ordinal_1based'] for c in cols] == list(range(1, 12)), 'must preserve 1..11 order'
assert all(c['approval']['target_column_name'] == 'APPROVED' for c in cols), 'all 11 columns must be approved'
dp = [c for c in cols if c['target_pg_type_candidate'] == 'double precision']
assert len(dp) == 2 and {c['source_column'] for c in dp} == {'inst_xcoord', 'inst_ycoord'}

columns_out = [{
    'ordinal': c['column_ordinal_1based'],
    'source_column': c['source_column'],
    'target_column': c['target_name_candidate'],
    'pg_type': c['target_pg_type_candidate'],
    'nullable': c['target_nullable_candidate'],
} for c in cols]
assert len({c['target_column'] for c in columns_out}) == 11
assert sum(1 for c in columns_out if c['nullable']) == 5
assert sum(1 for c in columns_out if not c['nullable']) == 6

# ---- 有序复合主键：源 PK 位次 -> 目标列，双向都要一致 ----
pk_rows = sorted([c for c in cols if c['source_pk_position'] > 0], key=lambda c: c['source_pk_position'])
assert len(pk_rows) == 6
pk_source = [c['source_column'] for c in pk_rows]
pk_targets = [c['target_name_candidate'] for c in pk_rows]
probe_pk = [i['name'] for i in probe['indexes_detail'][0]['index_info']]
assert pk_source == probe_pk, (pk_source, probe_pk)
assert probe['indexes_detail'][0]['origin'] == 'pk'
assert probe['pk_distinct'] == EXPECTED_ROWS
pk_decl = [c for c in appr['constraints_and_indexes'] if c['item'] == 'PRIMARY KEY'][0]
assert pk_decl['source_definition']['source_columns_in_pk_order'] == pk_source
assert len(probe['fk_list']) == 0

# ---- 约束与默认值来源依据入证 ----
def _h(o): return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
constraint_sources = {}
for r in appr['constraints_and_indexes']:
    constraint_sources[r['item']] = {
        'source_declared': r['source_declared'],
        'source_definition': r['source_definition'],
        'target_proposal': r['target_proposal'],
        'approval_status': r['approval'],
        'target_execution': r['target_execution'],
        'source_fact_verified_live': r.get('source_fact_verified_live', True),
        'basis_digests': {
            'source_ddl_sha256': probe['ddl_sha256'],
            'pragma_table_info_sha256': _h(probe['pragma_table_info']),
            'index_list_sha256': _h(probe['index_list']),
            'indexes_detail_sha256': _h(probe['indexes_detail']),
            'fk_list_sha256': _h(probe['fk_list']),
        },
    }
default_sources = {
    'columns_with_default_null': [c['source_column'] for c in cols if c['source_default_sql'] is not None],
    'columns_without_default': [c['source_column'] for c in cols if c['source_default_sql'] is None],
    'defaults_are_literal_null': all(c['source_default_sql'] in (None, 'NULL') for c in cols),
    'basis': 'pragma table_info dflt_value 实测（source-ddl-probe.json:pragma_table_info）',
    'basis_digest': _h(probe['pragma_table_info']),
}

candidate = {
    'version': 1,
    'release_id': '2026-11-26-bstep1-addr-single-table-frozen-candidate',
    'source_version': 'usedata-wd61-verified-snapshot',
    'inventory_sha256': INVENTORY_SHA,
    'status': 'frozen',
    'review': {
        'approved_by': '茶香',
        'approved_at': '2026-11-26T14:30:00Z',
        'approval_ref': 'chaxiang-authorized-20261126-bstep1-close-batch',
    },
    'exceptions': [],
    'rules': [{
        'rule_id': 'm007906',
        'selector': {'relative_path': appr['source_member']['relative_path'],
                     'archive_chain': [], 'archive_ordinals': []},
        'expected': {'kind': 'file', 'size': appr['source_member']['size_bytes'],
                     'sha256': appr['source_member']['sha256'], 'signature': 'sqlite'},
        'disposition': 'IMPORT',
        'reason': ('B 批单表导入：SOCIAL_INSTITUTION_ADDR 11 列映射与六项约束处置经茶香 2026-11-26 授权批准；'
                   'R62 隔离试装 TRIAL_PASS（复用未重跑）；目标名已完成全量碰撞检查无冲突'),
        'format_family': 'sqlite',
        'encodings': [],
        'targets': [{
            'object_name': 'SOCIAL_INSTITUTION_ADDR',
            'schema': coll['table_level']['target_schema'],
            'table': coll['table_level']['target_table'],
            'expected_count': EXPECTED_ROWS,
            'expected_sha256': EXPECTED_SHA,
            'columns': columns_out,
            'primary_key': {'columns': pk_targets},
        }],
        'validator': 'canonical_value_v1',
        'mirror_of': None,
        'mirror_evidence_sha256': None,
    }],
}
# 绑定块单独作为证据（不进合同规范字节，避免污染模型）
binding = {
    'source_member_rule_id': 'm007906',
    'source_relative_path': appr['source_member']['relative_path'],
    'source_sha256': appr['source_member']['sha256'],
    'source_size_bytes': appr['source_member']['size_bytes'],
    'source_object_id': appr['source_object_id'],
    'source_schema_hash': appr['source_schema_hash'],
    'expected_rows': EXPECTED_ROWS,
    'duplicate_rows': DUPLICATES,
    'source_side_sha256': EXPECTED_SHA,
    'field_count': r62['source_fields'],
    'inventory_sha256': INVENTORY_SHA,
    'approval_reference': {
        'approval_table': 'b-approval-table-v2.json',
        'approval_table_sha256': sha_file(BOX / 'b-approval-table-v2.json'),
        'authorized_by': '茶香',
        'authorized_at': '2026-11-26',
        'scope': '11 列映射 + 六项约束处置（PK/UNIQUE/INDEX/FK/DEFAULT/NOT NULL）批准',
        'columns_approved': 11,
    },
    'columns_preserve_source_order': True,
    'columns_count': 11,
    'double_precision_columns': ['inst_xcoord', 'inst_ycoord'],
    'primary_key_ordered': True,
    'primary_key_source_order': pk_source,
    'primary_key_target_order': pk_targets,
    'constraint_and_default_sources': constraint_sources,
    'default_sources': default_sources,
    'collision_check': {'ref': 'collision-check.json', 'sha256': sha_file(BOX / 'collision-check.json'),
                        'verdict': coll['verdict']},
    'model_extension': {
        'pg_type_added': 'double precision',
        'primary_key_field_added': 'ObjectTarget.primary_key（有序目标列元组）',
        'old_contract_digest_preserved': 'fa28a878f48fed506700cbaaf91c6a8ee45bdc28e9fef05904b3c56f4c61929e',
    },
    'full_ready_for_import': False,
    'production_write': False,
    'note': '单表冻结候选；不等于写库授权，六项约束 target_execution 仍为 NOT_EXECUTED',
}
out = {'candidate': candidate, 'binding': binding}
print(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))

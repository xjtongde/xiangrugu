"""把 b-approval-table.json 升级为 v2：本盒茶香授权批准的 11 列映射与六项约束处置。"""
import json, hashlib, pathlib, sys

BOX = pathlib.Path(sys.argv[1])
APPROVAL = {
    'authorized_by': '茶香',
    'authorized_at': '2026-11-26T14:30:00Z',
    'authorization_ref': '第 6/6 块后续·第 1/6 步收口｜固定基线 608d191',
    'authorization_text_summary': '批准 b-approval-table.json 中 SOCIAL_INSTITUTION_ADDR 的 11 列映射与六项约束处置；目标名先完成全量碰撞检查；保留 11 列原序，不得通过删列使校验通过',
}
a = json.load(open(BOX / 'b-approval-table.json'))
v2 = json.loads(json.dumps(a))
v2['version'] = 2
v2['supersedes'] = 'b-approval-table.json v1（11 列/六项约束为 PENDING）'
v2['upgraded_at_utc'] = '2026-11-26T14:30:00Z'

# 目标命名：碰撞检查已 PASS
coll = json.load(open(BOX / 'collision-check.json'))
assert coll['verdict'] == 'PASS_NO_COLLISION_STOP_NOT_TRIGGERED'
v2['target']['naming_collision_check'] = 'PASS_NO_COLLISION'
v2['target']['naming_collision_evidence'] = 'collision-check.json'
v2['target']['table_name_status'] = 'APPROVED_BY_CHAXIANG_20261126'
v2['target']['approval'] = {'target_table_name': 'APPROVED',
                            'target_column_names': 'APPROVED'}

# 11 列逐列批准
for c in v2['columns']:
    ap = c['approval']
    ap['target_table_name'] = 'APPROVED'
    ap['target_column_name'] = 'APPROVED'
    ap['nullability_constraints'] = 'APPROVED'
    ap['approved_by'] = APPROVAL['authorized_by']
    ap['approved_at'] = APPROVAL['authorized_at']
    ap['authorization_ref'] = APPROVAL['authorization_ref']

# 六项约束处置批准（执行仍 NOT_EXECUTED）
for r in v2['constraints_and_indexes']:
    r['approval'] = 'APPROVED_BY_CHAXIANG_20261126'
    r['approved_by'] = APPROVAL['authorized_by']
    r['approved_at'] = APPROVAL['authorized_at']
    assert r['target_execution'] == 'NOT_EXECUTED', 'constraint execution must stay NOT_EXECUTED'

v2['approval_summary']['already_approved'] = list(v2['approval_summary']['already_approved']) + [
    '目标表名（全量碰撞检查 PASS_NO_COLLISION）',
    '目标列名 11/11（保留原序，未删列）',
    '可空性/约束处置六项（批准；target_execution 仍 NOT_EXECUTED）',
]
v2['approval_summary']['pending_decision'] = [
    '六项约束的实际执行（target_execution 仍 NOT_EXECUTED）',
    '新的写库授权原文（首批 88f4f1ac 不得复用）',
    'Codex 独立验收放行',
]
v2['authorization'] = APPROVAL
print(json.dumps(v2, ensure_ascii=False, indent=1, sort_keys=True))

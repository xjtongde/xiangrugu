"""A 批：从已接收的 fa28a878… 合同生成新版正式处置账（不改动旧账与原清单）。

产物：
  disposition-ledger-fa28a878-20261126.json  新版正式账
  a-ledger-delta-report.json                 与旧账逐项对比
"""
import json, hashlib, sys, collections
from pathlib import Path
sys.path.insert(0, '/tmp/a01pkg')
from xiangrugu_datamgmt_patched.contracts import ReleaseContract
from xiangrugu_datamgmt_patched.disposition import DispositionLedger
from xiangrugu_datamgmt_patched.inventory import (ChecksumAssertion, InventoryEntry,
                                                  InventoryIssue, InventoryManifest)

BOX = Path(sys.argv[1])
CAND = BOX / 'abatch-candidate.json'
INV = BOX / 'inventory.json'
OLD = BOX / 'old-ledger.json'
AUTH_SHA = 'fa28a878f48fed506700cbaaf91c6a8ee45bdc28e9fef05904b3c56f4c61929e'
ORIG_INV = 'fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db'


def rebuild_manifest(doc):
    entries = tuple(InventoryEntry(
        relative_path=e['relative_path'], archive_chain=tuple(e.get('archive_chain', ())),
        archive_ordinals=tuple(e.get('archive_ordinals', ())), kind=e.get('kind', 'file'),
        size=e.get('size'), sha256=e.get('sha256'), signature=e.get('signature', 'unknown'))
        for e in doc['entries'])
    issues = tuple(InventoryIssue(
        code=i['code'], relative_path=i['relative_path'],
        archive_chain=tuple(i.get('archive_chain', ())), archive_ordinals=tuple(i.get('archive_ordinals', ())),
        detail=i.get('detail', ''), blocking=i.get('blocking', True)) for i in doc['issues'])
    checksums = tuple(ChecksumAssertion(
        ledger=c['ledger'], line=c['line'], raw_name=c['raw_name'], target=c['target'],
        expected_sha256=c['expected_sha256'], matched=c['matched'],
        archive_chain=tuple(c.get('archive_chain', ())), archive_ordinals=tuple(c.get('archive_ordinals', ())))
        for c in doc['checksums'])
    limits = tuple(sorted((k, int(v)) for k, v in doc['limits']))
    return InventoryManifest(entries=entries, issues=issues, checksums=checksums, limits=limits)


inv_bytes = INV.read_bytes()
manifest = rebuild_manifest(json.loads(inv_bytes))
assert manifest.sha256 == ORIG_INV, ('inventory sha drift', manifest.sha256)

contract = ReleaseContract.model_validate(json.loads(CAND.read_text()))
assert contract.sha256 == AUTH_SHA, ('contract sha mismatch', contract.sha256)
assert contract.inventory_sha256 == ORIG_INV
assert contract.status == 'frozen'

ledger = DispositionLedger.evaluate(manifest, contract)
cov = ledger.coverage()

# 分项统计
records = ledger.records
matched = [r for r in records if len(r.rule_ids) == 1]
unmatched = [r for r in records if not r.rule_ids]
multiple = [r for r in records if len(r.rule_ids) > 1]
by_disp = collections.Counter(r.disposition.value if hasattr(r.disposition, 'value') else r.disposition
                              for r in matched)

# 规则反查：每条规则命中数
rule_hits = collections.Counter()
for r in matched:
    rule_hits[r.rule_ids[0]] += 1
rule_ids = [r.rule_id for r in contract.rules]
exclusive = all(rule_hits.get(rid, 0) == 1 for rid in rule_ids)
dup_attr = [r.member.relative_path for r in multiple]

ledger_doc = ledger.canonical_bytes()
import base64
ledger_json = json.loads(ledger_doc.decode('utf-8'))

out = {
    'format': 'xiangrugu.formal-ledger.v1',
    'release_id': contract.release_id,
    'contract_sha256': contract.sha256,
    'inventory_sha256': manifest.sha256,
    'status': ledger.status,
    'records': ledger_json['records'],
    'issues': ledger_json['issues'],
}
ledger_bytes = json.dumps(out, ensure_ascii=False, sort_keys=True, indent=1).encode('utf-8')

# 旧账对比
old = json.loads(OLD.read_text())
old_cov_paths = {(r['member']['relative_path'], tuple(r['member'].get('archive_chain', ())),
                  tuple(r['member'].get('archive_ordinals', ()))): r for r in old['records']}
delta = {'old_record_count': len(old['records']), 'new_record_count': len(records),
         'old_contract_sha256': old['contract_sha256'],
         'new_contract_sha256': contract.sha256,
         'old_inventory_sha256': old['inventory_sha256'],
         'new_inventory_sha256': manifest.sha256,
         'new_issues': ledger_json['issues'],
         'old_issues': old['issues']}
drift = [p for p, r in ((p, r) for p, r in old_cov_paths.items())]
changed = []
for r in records:
    key = (r.member.relative_path, tuple(r.member.archive_chain), tuple(r.member.archive_ordinals))
    o = old_cov_paths.get(key)
    nd = r.disposition.value if hasattr(r.disposition, 'value') else r.disposition
    if o is None or o['disposition'] != nd or o['rule_ids'] != list(r.rule_ids):
        changed.append({'relative_path': r.member.relative_path, 'old': o['disposition'] if o else None,
                        'new': nd, 'old_rules': o['rule_ids'] if o else None, 'new_rules': list(r.rule_ids)})
delta['changed_records'] = len(changed)
delta['changed_sample'] = changed[:5]

print(json.dumps({'ledger': out, 'summary': {
    'contract_sha256': contract.sha256,
    'inventory_sha256': manifest.sha256,
    'records': len(records),
    'matched': len(matched),
    'unmatched': len(unmatched),
    'multiple': len(multiple),
    'coverage_matched': cov.matched,
    'coverage_unmatched': cov.unmatched,
    'coverage_multiple': cov.multiple,
    'coverage_unexplained': cov.unexplained,
    'coverage_blocked': cov.blocked,
    'coverage_errors': cov.errors,
    'conforms': cov.conforms,
    'ready_for_import': ledger.ready_for_import,
    'by_disposition': dict(by_disp),
    'rules': len(contract.rules),
    'rules_all_exclusive_single_owner': exclusive,
    'rule_hit_counts': dict(rule_hits),
    'duplicate_attribution': dup_attr,
    'issue_codes': sorted({i.code for i in ledger.issues}),
    'issue_count': len(ledger.issues),
}, 'delta': delta}, ensure_ascii=False, indent=1, sort_keys=True))

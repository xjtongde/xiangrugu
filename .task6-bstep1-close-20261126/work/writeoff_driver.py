"""A 批：用同一合同 fa28a878 重生两份例外证据并调用正式核销入口（只读，不连库）。"""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, '/tmp/a01pkg')
from xiangrugu_datamgmt_patched.contracts import ReleaseContract
from xiangrugu_datamgmt_patched.disposition import DispositionLedger
from xiangrugu_datamgmt_patched.inventory import (ChecksumAssertion, InventoryEntry,
                                                  InventoryIssue, InventoryManifest)
from xiangrugu_datamgmt_patched.writeoff import ORIGINAL_INVENTORY_SHA256, run_writeoff

HERE = Path(sys.argv[1])
AUTH_SHA = 'fa28a878f48fed506700cbaaf91c6a8ee45bdc28e9fef05904b3c56f4c61929e'


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


inv_bytes = (HERE / 'inventory.json').read_bytes()
manifest = rebuild_manifest(json.loads(inv_bytes))
contract = ReleaseContract.model_validate(json.loads((HERE / 'abatch-candidate.json').read_text()))
assert contract.sha256 == AUTH_SHA
raw_ledgers = {'SHA256SUMS-b2': (HERE / 'SHA256SUMS-b2').read_bytes(),
               'harvard/chgis/SHA256SUMS.txt': (HERE / 'chgis-SHA256SUMS.txt').read_bytes()}

out = {
    'inventory_file_sha256': hashlib.sha256(inv_bytes).hexdigest(),
    'manifest_reconstructed_sha256': manifest.sha256,
    'original_inventory_lock': manifest.sha256 == ORIGINAL_INVENTORY_SHA256,
    'contract_canonical_sha256': contract.sha256,
    'contract_matches_authorized_fa28a878': contract.sha256 == AUTH_SHA,
    'contract_inventory_binding': contract.inventory_sha256 == ORIGINAL_INVENTORY_SHA256,
    'contract_status': contract.status,
    'nul_raw_sha256': hashlib.sha256(raw_ledgers['SHA256SUMS-b2']).hexdigest(),
    'nul_raw_size': len(raw_ledgers['SHA256SUMS-b2']),
    'chgis_raw_sha256': hashlib.sha256(raw_ledgers['harvard/chgis/SHA256SUMS.txt']).hexdigest(),
    'chgis_raw_size': len(raw_ledgers['harvard/chgis/SHA256SUMS.txt']),
    'formal_frozen_parse': 'PASS',
}
result = run_writeoff(manifest, contract, raw_ledgers)
out['writeoff_result'] = result
out['closed_issue_count'] = len(result['closed_issues'])
out['closed_issues_identity'] = sorted((i['code'], i['detail'], i['relative_path'])
                                       for i in result['closed_issues'])
out['exactly_three_fixed_closed'] = out['closed_issues_identity'] == sorted([
    ('checksum_line', 'line=173', 'SHA256SUMS-b2'),
    ('checksum_missing', 'line=4', 'harvard/chgis/SHA256SUMS.txt'),
    ('checksum_nul', 'count=126', 'SHA256SUMS-b2')])
out['original_complete_false_preserved'] = manifest.complete is False
out['inventory_bytes_untouched'] = hashlib.sha256(
    (HERE / 'inventory.json').read_bytes()).hexdigest() == out['inventory_file_sha256']
out['derived_issue_codes'] = result['derived_issue_codes']
out['writeoff_ready_for_import'] = result['ready_for_import']

# 证据独立重算
nul_ev = result['run_evidence']['nul']
chgis_ev = result['run_evidence']['chgis']
def edigest(o):
    return hashlib.sha256(json.dumps(o, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()
out['nul_evidence_sha256_recomputed'] = edigest(nul_ev)
out['chgis_evidence_sha256_recomputed'] = edigest(chgis_ev)
(HERE / 'nul-evidence.json').write_text(json.dumps(nul_ev, ensure_ascii=False, indent=1, sort_keys=True) + '\n')
(HERE / 'chgis-evidence.json').write_text(json.dumps(chgis_ev, ensure_ascii=False, indent=1, sort_keys=True) + '\n')
(HERE / 'writeoff-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + '\n')

print(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))

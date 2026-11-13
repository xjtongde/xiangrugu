#!/usr/bin/env python3
"""DSH independent acceptance of returned p01 proxy receipts (read-only).

Recomputes every digest from raw bytes; trusts no narrative claim.
Run from the repo root: python3 docs/superpowers/evidence/2026-11-13-p01-task-card/acceptance-check.py
"""
import json, hashlib
from pathlib import Path
R = Path('docs/superpowers/evidence/2026-11-13-p01-task-card-receipts/returned')
EV = Path('docs/superpowers/evidence/2026-11-13-p01-task-card')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jload(p): return json.loads(Path(p).read_text())
checks = []
def ck(name, ok, detail=''):
    checks.append({'check': name, 'ok': bool(ok), 'detail': str(detail)})
    if not ok: print('FAIL:', name, detail)

IMAGE='sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a'
REV='8fbc8c97fcf1d818caddf6ab556fa82d986643ed'
CARD_SHA_CLAIM='41bd0ecfb8b9cf6081909f60e27780c40fd5d7bf3019847a77905a4f61fc0b69'
REVIEW_SHA_CLAIM='a7c2c5bdb69a17e8c6038065f16eff378b81f443bdc486a8af1a2b014630c93d'
M=R/'p01-card-metadata'; P=R/'p01-card-product-gate'; J=R/'p01-card-reject-noauth'

# 1. digests & cross-consistency
card_path=M/'output/task-card.closed.json'; card_sha=sha(card_path)
ck('card_sha_recomputed', card_sha==CARD_SHA_CLAIM, card_sha)
ck('card_toplevel_copy_identical', (R/'task-card.closed.json').read_bytes()==card_path.read_bytes())
review_path=M/'output/review/review.json'; review_sha=sha(review_path)
ck('review_sha_recomputed', review_sha==REVIEW_SHA_CLAIM, review_sha)
card=jload(card_path); review=jload(review_path); cr=jload(M/'output/card-receipt.json'); ver=jload(R/'verification.json')
ck('card_receipt_binds_card_sha', cr['task_card_sha256']==card_sha==cr['task_card']['sha256'])
ck('verification_binds_card_sha', ver['task_card_sha256']==card_sha)
ck('verification_binds_review_sha', ver['review_sha256']==review_sha)
ck('card_binds_review_sha', card['bindings']['closed_review']['sha256']==review_sha==cr['closed_review']['sha256'])
rej=jload(J/'rejection-receipt.json')
ck('rejection_binds_card_sha', rej['task_card_sha256']==card_sha)
ck('verification_status', ver['status']=='P01_TASK_CARD_METADATA_VERIFIED_CLOSED')
ck('verification_attempt', ver['attempt_id']=='real-p01-20261113-a'==card['attempt_id']==cr['attempt_id'])
ck('card_receipt_closed_flags', cr['source_read_authorized'] is False and cr['postgresql_authorized'] is False and cr['real_execution_ready'] is False and cr['source_bytes_read'] is False and cr['ready_for_import'] is False and cr['contract_frozen'] is False)
ck('card_receipt_image', cr['actual_image']=={'git_revision':REV,'image_id':IMAGE,'source_status':'dirty','user':'10001:10001'})

# 2. card closed state & identities
ck('card_status_closed', card['status']=='CLOSED_REAL_PARTITION_TASK_CARD_NOT_EXECUTABLE')
ck('card_source_read_unauthorized', card['source_read_authorized'] is False)
ck('card_postgresql_unauthorized', card['postgresql_authorized'] is False)
ck('card_auth_null', card['authorization']['authorization_file'] is None and card['authorization']['authorization_sha256'] is None and card['authorization']['required'] is True)
ck('card_historical_consumed', card['authorization']['historical_p01_authorizations_consumed'] is True)
ck('card_expected_nulls', card['expected_count'] is None and card['expected_sha256'] is None)
ck('card_no_auto', card['auto_retry'] is False and card['auto_next_partition'] is False and card['one_attempt_only'] is True)
ck('card_not_ready', card['ready_for_import'] is False and card['contract_frozen'] is False)
ck('card_partition', card['partition_id']=='large-p01')
so=card['source_object']
ck('card_object_identity', so['source_object_name']=='POSTED_TO_ADDR_DATA' and so['source_object_id']=='1650019ee3e5efb5dceeac27e7871317eb61551cfb3e7754be6be36c63bc52ac' and so['schema_hash']=='a942064328b43402fcb811a15f8adf24cfbcba2e94b10db203f7b1fa68e0bb08' and so['rule_id']=='m007906')
ck('card_8_columns', so['source_columns']==['c_posting_id','c_personid','c_office_id','c_addr_id','c_created_by','c_created_date','c_modified_by','c_modified_date'])
parent_rel='datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-value-project-partition-readiness.closed.json'
parent=jload(parent_rel)
osr=jload(parent['bindings']['original_scope_review']['path'])
osr_obj=[o for o in osr['objects'] if o['source_object_name']=='POSTED_TO_ADDR_DATA'][0]
ck('card_schema_hash_matches_parent', so['schema_hash']==osr_obj['schema_hash'])
ck('card_column_keys_match_parent', so['columns']==osr_obj['columns'])
ck('card_source_columns_match_parent', so['source_columns']==osr_obj['source_columns'])
ck('parent_expected_nulls', osr_obj.get('expected_count') is None and osr_obj.get('expected_sha256') is None)
ck('card_parent_binding_sha', card['bindings']['parent_review']['sha256']==sha(parent_rel)=='edf31997132133987b7505ce1a90563e7b7a21335b94bcd91dfdf10d8046692e')
ck('card_roots_binding_sha', card['bindings']['roots']['sha256']==sha('datamgmt/config/roots.yaml')=='6235c356fca754a687a2f02998770c9609b20748ade674d0050d86a0a428e07c')
cert_rel='docs/superpowers/evidence/2026-10-13-medium-foreground/raw/batch-runner-medium-foreground-20261013/foreground-metadata/output/fixture/certificate.json'
ck('card_certificate_binding_sha', card['bindings']['certificate']['sha256']==sha(cert_rel)=='58cb2e50f2124829130d4a9d6b8e55b8f6b2418bca18458685cb5d16ff193f9a')
rv_rel='docs/superpowers/evidence/2026-11-13-request-reader-integration/verification.json'
ck('card_runtime_verification_binding_sha', card['bindings']['runtime_verification']['sha256']==sha(rv_rel)=='8c121fd05e47db385b170d379436492ffd79e96ef99c1adae4b5ea0951f7f3da')
cert=jload(cert_rel); snap=card['snapshot']
ck('card_snapshot_id', snap['snapshot_id']==cert['snapshot_id']=='2026-10-07-bootstrap')
ck('card_manifest_sha', snap['manifest_sha256']==cert['manifest_sha256']=='03174f42f62dbea16402cdcbd05aa132a0a478453d7f31a09127374835f14699')
members=cert['members']; files=[m for m in members if m['kind']=='file']; dirs=[m for m in members if m['kind']=='directory']
ck('card_member_counts', snap['members_total']==len(members)==232 and snap['files']==len(files)==189 and snap['directories']==len(dirs)==43)
mem=[m for m in files if m['path']=='harvard/cbdb/cbdb_20260919.sqlite3'][0]
ck('card_member_identity', snap['member']=={'kind':'file','path':mem['path'],'sha256':mem['sha256'],'size':mem['size']} and mem['size']==586485760 and mem['sha256']=='bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400')
size_sum=sum(m['size'] for m in files)
ck('digest_budget_derivation', size_sum==2508987728 and snap['logical_digest_budget_bytes']==size_sum+2*586485760==3681959248)
rv=jload(rv_rel); rt=card['runtime']
rv_image=Path('docs/superpowers/evidence/2026-11-13-request-reader-integration/runtime-image.id').read_text().strip()
ck('card_runtime_image', rt['image_id']==IMAGE==rv_image)
ck('card_runtime_revision', rt['git_revision']==REV)
ck('card_runtime_user_status', rt['user']=='10001:10001' and rt['source_status']=='dirty' and rt['image_tag']=='xiangrugu:runtime-request-reader-20261113-a')
ck('card_artificial_batch_binding', rt['verified_artificial_batch']=={'complete':rv['complete'],'fields':rv['fixture_fields'],'rows':rv['fixture_rows'],'supervisor_elapsed_seconds':rv['supervisor_elapsed_seconds']})
res=card['resources']
ck('card_resources', res['cpus']==0.5 and res['memory_bytes']==805306368 and res['memory_swap_equals_memory'] and res['cgroup_swap_zero'] and res['pids_limit']==128 and res['network']=='none' and res['readonly_rootfs'] and res['readonly_source'] and res['cap_drop']=='ALL' and res['no_new_privileges'] and res['nice']==19 and res['ionice']=='idle' and res['workers']==1 and res['single_task_serial'])
ck('card_stream_limits', res['canonical_stream_bytes']==268435456 and res['app_temp_bytes']==1073741824 and res['chunk_bytes']==2097152 and res['chunk_rows']==4096 and res['merge_fan_in']==16 and res['max_temp_files']==1024)
ck('card_no_hard_isolation_claims', res['filesystem_hard_quota'] is False and res['hard_io_bandwidth_isolation'] is False)
ck('card_deadlines', card['deadlines']=={'candidate_seconds':1800,'host_seconds':1830,'real_mode_activated':False,'transport_seconds':1880})
ck('card_stop_conditions_count', len(card['stop_conditions'])==18)
ck('card_read_scope', card['read_scope']['full_snapshot_digest_recheck'] and card['read_scope']['sqlite_digest_before_after'] and card['read_scope']['nas_forbidden'] and card['read_scope']['postgresql_forbidden'] and card['read_scope']['other_table_values_forbidden'] and card['read_scope']['freeze_import_publish_forbidden'])
ck('card_coverage', card['coverage']=={'complete_tables':68,'task8_complete':False,'total_tables':78})

# 3. review closed
ck('review_status', review['status']=='DRAFT_PROJECT_PARTITION_REVIEW_NOT_EXECUTABLE')
ck('review_missing_empty', review['missing']==[])
for f in ('source_read_authorized','postgresql_authorized','contract_frozen','ready_for_import'):
    ck('review_flag_'+f, review.get(f) is False)
sel=jload(M/'output/review.selection.json'); desc=jload(M/'output/review/descriptor.review.json')
ck('selection_attempt', sel['attempt_id']=='real-p01-20261113-a')
ck('descriptor_attempt', desc['attempt_id']=='real-p01-20261113-a' and desc['partition_id']=='large-p01')
ck('review_generated_descriptor_sha', review['generated']['descriptor.review.json']==sha(M/'output/review/descriptor.review.json'))
ck('review_generated_request_sha', review['generated']['request.review.json']==sha(M/'output/review/request.review.json'))
ck('selection_manifest_pin', sel['expected_manifest_sha256']=='03174f42f62dbea16402cdcbd05aa132a0a478453d7f31a09127374835f14699')
def resolve(container_path):
    if container_path.startswith('/data/var/run/'): return M/'output'/container_path[len('/data/var/run/'):]
    if container_path == '/metadata/selected-certificate.json': return Path(cert_rel)
    if container_path == '/metadata/runtime-verification.json': return Path(rv_rel)
    if container_path == '/metadata/build-inputs.sha256': return Path('docs/superpowers/evidence/2026-11-13-request-reader-integration/build-inputs.sha256')
    if container_path.startswith('/metadata/'): return Path(container_path[len('/metadata/'):])
    return None
sel_pins_ok=True
for name,pin in sel['files'].items():
    local=resolve(pin['path'])
    if local is None or not local.exists() or sha(local)!=pin['sha256']:
        sel_pins_ok=False; print('  selection pin mismatch:', name, pin['path'])
ck('selection_file_pins_all_match', sel_pins_ok)
req=jload(M/'output/review/request.review.json')
ck('request_template_approval_null', req.get('approval_file') is None and req.get('approval_sha256') is None)
ck('request_template_source_mode', req.get('source_mode')=='project_snapshot')

# 4. image identity
ident=IMAGE+' '+REV+' 10001:10001 dirty'
for run in (M,P,J): ck('image_identity_'+run.name, (run/'image-identity.txt').read_text().strip()==ident)
ck('verification_image_identity', ver['image_identity']==ident and ver['image_identity_match'] is True)

# 5. resources
for run in (M,P):
    hc=jload(run/'host-config.json')
    ck('hostconfig_'+run.name, hc['NanoCpus']==500000000 and hc['Memory']==805306368 and hc['MemorySwap']==805306368 and hc['PidsLimit']==128 and hc['NetworkMode']=='none' and hc['ReadonlyRootfs'] is True and hc['CapDrop']==['ALL'] and any(str(s).startswith('no-new-privileges') for s in hc['SecurityOpt']))
    ck('hostconfig_no_nas_'+run.name, 'wd61workmetadata' not in json.dumps(hc))
    lim=jload(run/'output/limits.json')
    ck('limits_'+run.name, lim['cpu.max']=='50000 100000' and lim['memory.max']=='805306368' and lim['memory.swap.max']=='0' and int(lim['pids.max'])<=128 and lim['worker_nice']==19 and lim['worker_ionice']=='idle')

# 6. refusal 1
ck('reject_exit_code_file', (J/'exit-code.txt').read_text().strip()=='2')
ck('reject_exit_code_receipt', rej['exit_code']==2)
ck('reject_refused_before_materialize', rej['refused_before_materialize'] is True)
ck('reject_authorization_absent', rej['authorization_present'] is False)
ck('reject_executable_files_zero', rej['executable_request_or_approval_files']==0)
ck('reject_no_materialize_dir', rej['materialize_dir_found'] is False)
ck('reject_no_real_candidate', rej['real_candidate_container_found'] is False)
ck('reject_boundaries', rej['source_bytes_read'] is False and rej['postgresql_connected'] is False and rej['ready_for_import'] is False)
ck('reject_no_container_created', not (J/'container-id.txt').exists() and not (J/'host-config.json').exists())
ck('verification_rejection_ok', ver['rejection_ok'] is True and ver['authorization_absent'] is True and ver['executable_request_or_approval_files']==0 and ver['real_candidate_absent'] is True)
ck('rejection_receipt_sha', sha(J/'rejection-receipt.json')==ver['rejection_receipt_sha256'])

# 7. refusal 2
pg=jload(P/'output/product-gate-receipt.json')
ck('product_gate_refused', pg['refused'] is True and pg['reason']=='real_execution_closed')
ck('product_gate_no_batch', pg['batch_created'] is False)
ck('product_gate_no_materialize', pg['executable_request_created'] is False and pg['approval_created'] is False)
ck('product_gate_default_artificial', pg['authorized_source_mode']=='artificial')
ck('product_gate_template_closed', pg['template_closed'] is True)
ck('product_gate_no_source_read', pg['source_bytes_read'] is False)
ck('product_gate_exit', (P/'exit-code.txt').read_text().strip()=='0')
ck('product_gate_template_sha', (P/'request-template.sha256').read_text().strip()==sha(M/'output/review/request.review.json')==pg['request_sha256'])
ck('verification_product_gate_ok', ver['product_gate_ok'] is True)
ck('product_gate_receipt_sha', sha(P/'output/product-gate-receipt.json')==ver['product_gate_receipt_sha256'])

# 8. recovery & no executable artifacts
for run in (M,P):
    st=jload(run/'container-state.json')
    ck('state_'+run.name, st['Running'] is False and st['ExitCode']==0 and st['OOMKilled'] is False and st['Dead'] is False and st['Status']=='exited')
    ck('removal_'+run.name, (run/'removal.txt').read_text().strip()=='xiangrugu-evidence-'+run.name)
    mon=jload(run/'output/monitor.json')
    ck('monitor_'+run.name, mon['status']=='SYNTHETIC_WORKER_COMPLETED' and mon['reason'] is None and mon['process_group_gone'] is True and mon['worker_exit_code']==0 and mon['synthetic_only'] is True)
ck('removed_candidates_2', ver['removed_candidates']==2)
allfiles=[p for p in R.rglob('*') if p.is_file()]
ck('no_batch_json', not any(p.name=='batch.json' for p in allfiles))
ck('no_approval_json', not any(p.name=='approval.json' for p in allfiles))
ck('no_executable_request', not any(p.name in ('request.json','scope.json','budget.json') for p in allfiles))
ck('no_authorization_json', not any(p.name=='authorization.json' for p in allfiles))
ck('verification_no_batch', ver['no_batch_anywhere'] is True)

# 9. services / host
for run in (M,P,J):
    ck('services_stable_'+run.name, (run/'services-before.txt').read_bytes()==(run/'services-after.txt').read_bytes())
    ck('services_healthy_'+run.name, (run/'services-before.txt').read_text().count('running healthy')==2)
boots={(run/'boot-id.txt').read_text().strip() for run in (M,P,J)}
ck('boot_id_consistent', len(boots)==1 and boots.pop()==ver['boot_id'])
ck('host_pswpout_zero', ver['host_pswpout']==0)
ck('dev_idle', ver['dev_idle'] is True)
ck('fs_not_nas', ver['runtime_fs']=='ext4' and ver['snapshot_fs']=='ext4' and ver['no_nas_filesystem'] is True)
ck('boundaries_held', ver['real_source_read'] is False and ver['source_bytes_read'] is False and ver['postgresql_connected'] is False and ver['contract_frozen'] is False and ver['ready_for_import'] is False and ver['real_candidate_started'] is False and ver['authorization_consumed'] is False and ver['new_real_expectations']==0)
ck('coverage_unchanged', ver['coverage_complete_tables']==68 and ver['coverage_total_tables']==78 and ver['task8_complete'] is False)

# 10. installed modules
bi={}
for line in Path('docs/superpowers/evidence/2026-11-13-request-reader-integration/build-inputs.sha256').read_text().splitlines():
    s,p=line.split('  ',1); bi[p]=s
for run in (M,P):
    io=jload(run/'output/installed-origin.json')
    mods=io['modules']
    ck('installed_7_modules_'+run.name, len(mods)==7 and io['installed_product_verified'] is True)
    ck('installed_modules_match_'+run.name, all(bi.get('datamgmt/src/xiangrugu_datamgmt/'+name+'.py')==rec['sha256'] and rec['path'].endswith('xiangrugu_datamgmt/'+name+'.py') for name,rec in mods.items()))
ck('verification_modules', ver['installed_modules_verified']==7 and ver['installed_modules_match'] is True)

# 11. staging (host 32 locale zh_CN: sha256sum prints 成功 instead of OK)
pc=(R/'packet-check.txt').read_text().splitlines()
ck('packet_check_25_ok', len(pc)==25 and all(l.endswith(': OK') or l.endswith(': 成功') for l in pc))
manifest={l.split('  ',1)[1] for l in (EV/'packet-inputs.sha256').read_text().splitlines()}
ck('packet_check_paths_match_manifest', {l.rsplit(': ',1)[0] for l in pc}==manifest)

# 12. transport
exits=[]
for name in ('metadata','product-gate','reject-noauth'):
    events=[json.loads(l) for l in (R/(name+'.log.controller.jsonl')).read_text().splitlines() if l.strip()]
    rex=[e for e in events if e.get('reason')=='remote_exit']
    ck('transport_remote_exit_'+name, len(rex)==1)
    exits.append(rex[0].get('remote_exit_code') if rex else None)
ck('transport_exits_0_0_2', exits==[0,0,2], str(exits))
ck('ssh_logs_empty_as_noted', all((R/(n+'.log')).stat().st_size==0 for n in ('metadata','product-gate','reject-noauth')))

# 13. worker logs & internal receipts
wl=(M/'worker.log').read_text()
ck('worker_log_card_prepared', 'CLOSED_REAL_PARTITION_REVIEW_AND_CARD_PREPARED' in wl and CARD_SHA_CLAIM in wl)
pwl=(P/'worker.log').read_text()
ck('worker_log_gate_refused', 'PRODUCT_GATE_REFUSED_AS_EXPECTED' in pwl and 'real_execution_closed' in pwl)
ck('metadata_only_receipt_sha', sha(M/'output/metadata-only-receipt.json')==ver['metadata_only_receipt_sha256']==card['bindings']['metadata_only_receipt']['sha256'])
ck('selection_sha', sha(M/'output/review.selection.json')==ver['selection_sha256']==card['bindings']['selection']['sha256'])
ck('preparation_sha', sha(M/'output/preparation/preparation.json')==card['bindings']['preparation']['sha256'])
ck('card_receipt_sha', sha(M/'output/card-receipt.json')==ver['card_receipt_sha256'])
mor=jload(M/'output/metadata-only-receipt.json')
ck('metadata_only_flags', mor['metadata_only'] is True and mor['real_source_read'] is False and mor['source_bytes_read'] is False and mor['new_real_expectations']==0 and mor['postgresql_authorized'] is False)
# retained .incomplete hardlink duplicates are the product's no-clobber publication protocol
ck('incomplete_retained_review', (M/'output/review/.review.json.incomplete').read_bytes()==(M/'output/review/review.json').read_bytes())
ck('incomplete_retained_preparation', (M/'output/preparation/.preparation.incomplete').read_bytes()==(M/'output/preparation/preparation.json').read_bytes())

failed=[c for c in checks if not c['ok']]
report={'as_of':'2026-11-13','receipt_commit':'5cd428af8d615b30e399c40c980edc5870c94709','attempt_id':'real-p01-20261113-a','task_card_sha256':card_sha,'closed_review_sha256':review_sha,'total_checks':len(checks),'failed':len(failed),'checks':checks}
Path(EV/'acceptance-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=1)+'\n')
print('ACCEPTANCE:', len(checks), 'checks,', len(failed), 'failed')
for c in failed: print('  FAIL', c['check'], c['detail'])

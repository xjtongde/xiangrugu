#!/usr/bin/env python3
"""Block 5 lead reconciliation v2: fixes disposition hyphens, nested member_key
chain reconstruction ('/'.join(chain)==rest), handoff supersession, doc-note xref."""
import json, collections
R = 'datamgmt/contracts/releases/2026-10-06-bootstrap/'
OUT = '.raster-block5-20261121/'
inv = json.load(open(R + 'inventory.json'))
E = inv['entries']
def key(e): return (e['relative_path'], tuple(e.get('archive_chain', [])), tuple(e.get('archive_ordinals', [])))
bykey = {key(e): e for e in E}
pc = collections.defaultdict(list)
for e in E: pc[(e['relative_path'], tuple(e.get('archive_chain', [])))].append(e)
psha = collections.defaultdict(list)
for e in E: psha[(e['relative_path'], e.get('sha256'))].append(e)

owned = {}
xrefs = []
def claim(e, block, note='', supersede=False):
    k = key(e)
    if k in owned:
        prev = owned[k]
        if prev[0] == block: return
        if supersede and prev[0] == 'handoff_block3':
            owned[k] = (block, note); return
        xrefs.append({'key': list(k), 'owner': prev, 'also_referenced_by': (block, note)})
        return
    owned[k] = (block, note)

def resolve(path, chain, sha=None, ordinals=None):
    if ordinals is not None:
        k = (path, tuple(chain), tuple(ordinals))
        if k in bykey: return bykey[k]
    cands = pc.get((path, tuple(chain)), [])
    if len(cands) == 1: return cands[0]
    if sha:
        m = [e for e in cands if e.get('sha256') == sha]
        if len(m) == 1: return m[0]
    return None

def resolve_member_key(mk, sha):
    outer, _, rest = mk.partition('!')
    if not rest:
        c = pc.get((outer, ()))
        return c[0] if c and len(c) == 1 else None
    cands = [e for e in E if e['relative_path'] == outer and '/'.join(e.get('archive_chain', [])) == rest]
    if len(cands) == 1: return cands[0]
    if len(cands) > 1 and sha:
        m = [e for e in cands if e.get('sha256') == sha]
        if len(m) == 1: return m[0]
    return None

unresolved = []
cb = json.load(open(R + 'import-package/cbdb/members.json'))
for m in cb['members']:
    e = resolve(m['relative_path'], m.get('archive_chain', []), m.get('sha256'), m.get('archive_ordinals'))
    if e: claim(e, 'block1', m.get('disposition_from_ledger', ''))
    else: unresolved.append(('block1', m['relative_path']))
tm = json.load(open(R + 'import-package/tabular/members.json'))
b5_handoff = []
for m in tm['members']:
    si = m['source_identity']
    e = resolve(si['relative_path'], si.get('archive_chain', []), si.get('sha256'), si.get('archive_ordinals'))
    if not e: unresolved.append(('block2', si['relative_path'], si.get('archive_chain'))); continue
    d = m['disposition']
    if d == 'organized': claim(e, 'block2', m.get('category', ''))
    elif d == 'handoff-block3': claim(e, 'handoff_block3', '')
    elif d == 'handoff-block5':
        claim(e, 'handoff_block5', m.get('category', '')); b5_handoff.append(key(e))
    else: claim(e, 'block2_' + d, '')
sg = json.load(open(R + 'import-package/spatial/groups.json'))
sp_n = 0
for g in sg['groups']:
    for m in g['members']:
        e = resolve_member_key(m['member_key'], m.get('sha256_inventory'))
        if e: claim(e, 'block3', g['family_candidate'], supersede=True); sp_n += 1
        else: unresolved.append(('block3', m['member_key']))
ms = json.load(open(R + 'import-package/mdb-sql/members.json'))
b5_from_b4 = []
for m in ms['core_members']:
    e = resolve(m['relative_path'], m.get('archive_chain', []), m.get('sha256'), m.get('archive_ordinals'))
    if e: claim(e, 'block4', m.get('family', ''))
    else: unresolved.append(('block4core', m.get('member_key')))
for m in ms['related_members']:
    e = resolve(m['relative_path'], m.get('archive_chain', []), m.get('sha256'), m.get('archive_ordinals'))
    if not e: unresolved.append(('block4rel', m['relative_path'], m.get('archive_chain'))); continue
    d = m['disposition']
    if d == 'excluded_non_data_to_block5':
        claim(e, 'block5_handoff_via_block4', 'Thumbs.db cache'); b5_from_b4.append(key(e))
    elif d == 'structural_container': claim(e, 'block4', 'structural_container')
    elif d.startswith('owned_by_block'): pass
    elif d == 'documentation_note': claim(e, 'block4_doc_note', 'documentation')
unowned = [k for k in bykey if k not in owned]
b5set = set(b5_handoff) | set(b5_from_b4)
cand_keys = list(dict.fromkeys(b5_handoff + b5_from_b4 + unowned))
cands = []
for k in cand_keys:
    e = bykey[k]
    leaf = (e['archive_chain'][-1] if e.get('archive_chain') else e['relative_path']).split('/')[-1]
    ext = leaf.rsplit('.', 1)[-1].lower() if '.' in leaf else ''
    src = 'handoff_block2' if k in set(b5_handoff) else ('handoff_block4' if k in set(b5_from_b4) else 'unowned_scan')
    cands.append({'relative_path': e['relative_path'], 'archive_chain': e.get('archive_chain', []),
                  'archive_ordinals': e.get('archive_ordinals', []), 'kind': e['kind'], 'size': e.get('size'),
                  'sha256': e.get('sha256'), 'signature': e.get('signature'), 'leaf': leaf, 'ext': ext,
                  'candidate_source': src})
recon = {'inventory_entries': len(E), 'inventory_sha256_prefix': 'fb5e6b334b898d62',
         'inventory_complete_flag': inv.get('complete'), 'inventory_issues': inv.get('issues', []),
         'owned_total': len(owned), 'owned_by_block': dict(collections.Counter(v[0] for v in owned.values())),
         'cross_references': xrefs, 'unresolved_refs': unresolved, 'unowned_count': len(unowned),
         'spatial_members_resolved': sp_n,
         'candidate_total': len(cands),
         'candidate_by_source': dict(collections.Counter(c['candidate_source'] for c in cands)),
         'candidate_by_kind': dict(collections.Counter(c['kind'] for c in cands)),
         'candidate_ext_histogram': dict(collections.Counter(c['ext'] for c in cands))}
json.dump(recon, open(OUT + 'recon.json', 'w'), ensure_ascii=False, indent=1, sort_keys=True)
json.dump(cands, open(OUT + 'candidates.json', 'w'), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: recon[k] for k in ['owned_total', 'owned_by_block', 'unowned_count', 'spatial_members_resolved', 'candidate_total', 'candidate_by_source', 'candidate_by_kind']}, ensure_ascii=False, indent=1))
print('xrefs:', len(xrefs), 'unresolved:', len(unresolved))
print('ext:', json.dumps(recon['candidate_ext_histogram'], ensure_ascii=False))
"""Owned fixed project-shaped protocol data; never an external source path."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import runpy
import sqlite3
import struct
import sys

import yaml

from xiangrugu_datamgmt.snapshots import digest,inventory,write_json_exclusive
from xiangrugu_datamgmt.project_partition import prepare_project_partition_review,materialize_project_partition_request
from xiangrugu_datamgmt.task_partition import prepare_partition_task


def pin(path):
    return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def save(path,document):
    path.parent.mkdir(parents=True,exist_ok=True);write_json_exclusive(path,document)
    return pin(path)


def wide(db,obj,rows):
    name=obj['source_object_name']
    def text(n):return f'{n//2:04d}'+'汉'*21844
    def frame(n):
        raw=text(n).encode('utf-8');assert len(raw)==65536
        payload=b'\x02'+struct.pack('>q',0)+b'\x01'+len(raw).to_bytes(8,'big')+raw+b'\x00'*6
        result=b'R'+(8).to_bytes(4,'big')+len(payload).to_bytes(8,'big')+payload
        assert len(result)==65573
        return result
    with sqlite3.connect(db) as connection:
        connection.execute(f'DELETE FROM "{name}"')
        connection.executemany(f'INSERT INTO "{name}" VALUES (?,?,?,?,?,?,?,?)',
            ((0,text(n),None,None,None,None,None,None) for n in range(rows-1,-1,-1)))
    schema_raw=json.dumps([[c['source_ordinal'],c['column_key'],c['pg_type'],c['allow_null_value']] for c in obj['columns']],
        ensure_ascii=True,separators=(',',':')).encode('ascii')
    schema=hashlib.sha256(schema_raw).digest()
    expected=hashlib.sha256(b'XRGSET\x00\x01'+bytes.fromhex(obj['source_object_id'])+schema)
    # Two equal frames per pair, generated in byte-sorted order without the product sorter.
    for pair in range((rows+1)//2):
        encoded=frame(pair*2)
        for _ in range(min(2,rows-pair*2)):expected.update(encoded)
    expected.update(b'E'+rows.to_bytes(8,'big'))
    return dict(source_object_id=obj['source_object_id'],source_object_name=name,schema_hash=schema.hex(),
        expected_count=rows,field_count=rows*8,expected_sha256=expected.hexdigest(),canonical_stream_bytes=81+rows*65573)


def reader_merge(db,obj):
    """Fixed 80k-row p01 only; independent hand frames, no external input."""
    rows=80000
    assert len(obj['columns'])==8 and obj['columns'][0]['pg_type']=='bigint'
    assert all(c['pg_type']=='text' and c['allow_null_value'] for c in obj['columns'][1:])
    def values(index):
        key=index-1 if index and index%97==0 else index
        return (key,*(None if key%7==0 else f'owned-{key:06d}-{column}' for column in range(1,8)))
    def frame(index):
        value=values(index)
        payload=b'\x02'+struct.pack('>q',value[0])
        for text in value[1:]:
            if text is None:payload+=b'\x00'
            else:
                raw=text.encode('utf-8');payload+=b'\x01'+len(raw).to_bytes(8,'big')+raw
        return b'R'+(8).to_bytes(4,'big')+len(payload).to_bytes(8,'big')+payload
    with sqlite3.connect(db) as connection:
        connection.execute(f'DELETE FROM "{obj["source_object_name"]}"')
        connection.executemany(f'INSERT INTO "{obj["source_object_name"]}" VALUES (?,?,?,?,?,?,?,?)',
                               (values(index) for index in range(rows-1,-1,-1)))
    schema_raw=json.dumps([[c['source_ordinal'],c['column_key'],c['pg_type'],c['allow_null_value']] for c in obj['columns']],
                          ensure_ascii=True,separators=(',',':')).encode('ascii')
    schema=hashlib.sha256(schema_raw).digest()
    expected=hashlib.sha256(b'XRGSET\x00\x01'+bytes.fromhex(obj['source_object_id'])+schema)
    counts=Counter(frame(index) for index in range(rows))
    stream_bytes=81
    for encoded,count in sorted(counts.items()):
        for _ in range(count):expected.update(encoded)
        stream_bytes+=len(encoded)*count
    expected.update(b'E'+rows.to_bytes(8,'big'))
    return dict(source_object_id=obj['source_object_id'],source_object_name=obj['source_object_name'],
                schema_hash=schema.hex(),expected_count=rows,field_count=rows*8,
                expected_sha256=expected.hexdigest(),canonical_stream_bytes=stream_bytes)


def build(root,*,image,revision,scenario):
    if type(scenario) is not str or scenario not in ('coverage','wide-fit','wide-over','reader-multi-merge'):raise ValueError('project_fixture_scenario')
    root=Path(root)
    if (not root.is_absolute() or Path('/data/var/run') not in root.parents or '..' in root.parts
            or any(p.is_symlink() for p in (root,*root.parents)) or not root.is_dir()):raise ValueError('project_fixture_output')
    if any(root.iterdir()):raise FileExistsError('project_fixture_exists')
    seed=runpy.run_path(str(Path(__file__).with_name('prepare_artificial_partitions.py')))['seed']
    request,scope,budgets,golden=seed(root,image,revision)
    fixture=root/'fixture';snapshot=fixture/'snapshots'/request['snapshot_id'];db=snapshot/request['relative_path']
    selected_golden=golden
    if scenario=='reader-multi-merge':
        rows=80000
        golden[0]=reader_merge(db,scope['objects'][0]);selected_golden=[golden[0]]
        budgets[0]['read_limits'].update(max_rows=rows,max_cells=rows*8)
        budgets[0]['sort_limits']['max_rows']=rows
    elif scenario!='coverage':
        rows=4093 if scenario=='wide-fit' else 4094
        selected_golden=[wide(db,scope['objects'][0],rows)]
        budgets[0]['read_limits'].update(max_rows=4094,max_cells=32752,max_value_bytes=268435456)
        budgets[0]['sort_limits']['max_rows']=4094
    members=inventory(snapshot);source=next(m for m in members if m['path']==request['relative_path'])
    request.update(expected_size=source['size'],expected_sha256=source['sha256'],manifest_sha256=digest(members))
    scope['source']=source
    repo=root/'metadata-repository';roots=repo/'datamgmt/config/roots.yaml';roots.parent.mkdir(parents=True)
    config=yaml.safe_load((fixture/'readonly-roots.yaml').read_text())
    config['roots']['usedata'].update(host='owned-project-protocol-fixture',path=str(root/'authority-never-read'))
    config['deployment']['source_snapshots'].update(container_root=str(fixture/'snapshots'),container_evidence_root=str(root))
    roots.write_text(yaml.safe_dump(config))
    certificate=save(root/'certificate.json',dict(version=1,status='VERIFIED',snapshot_id=request['snapshot_id'],
        source_path=config['roots']['usedata']['path'],members=members,manifest_sha256=request['manifest_sha256']))
    authority=dict(source_read_authorized=False,postgresql_authorized=False,contract_frozen=False,ready_for_import=False)
    objects=[dict(obj,schema_hash=g['schema_hash'],expected_count=None,expected_sha256=None,
        read_limits=cap['read_limits'],sort_limits=cap['sort_limits']) for obj,cap,g in zip(scope['objects'],budgets,golden,strict=True)]
    parent=dict(snapshot_id=request['snapshot_id'],member=source,objects=10,columns=235)
    packet=dict(version=1,status='METADATA_READINESS_SUPPLEMENT_NOT_EXECUTABLE',git_revision=revision,**authority,scope=parent,
        verified_artificial_deadlines=dict(candidate_seconds=1800,host_seconds=1830,transport_seconds=1880,real_mode_activated=False),bindings={})
    docs=dict(original_scope_review=dict(group='large',rule_id=request['rule_id'],scope=parent,objects=objects,**authority),
        preparation=dict(objects=[dict(source_object_id=o['source_object_id'],source_object_name=o['source_object_name'],columns=o['columns'],schema_hash=o['schema_hash']) for o in objects]),
        mapping=dict(objects=[dict(source_object_id=o['source_object_id'],source_object_name=o['source_object_name'],
            columns=[dict(source_name=name,source_ordinal=c['source_ordinal'],column_identity=c['column_key'],approved_type=c['pg_type'])
                for name,c in zip(o['source_columns'],o['columns'],strict=True)]) for o in objects]),
        remaining_budget=dict(objects=[dict(source_object_id=o['source_object_id'],name=o['source_object_name'],proposed_group='large') for o in objects]))
    for role,doc in docs.items():
        relative=f'datamgmt/contracts/owned-project/{role}.json';description=save(repo/relative,doc)
        packet['bindings'][role]=dict(path=relative,sha256=description['sha256'])
    packet['bindings']['roots']=dict(path='datamgmt/config/roots.yaml',sha256=pin(roots)['sha256'])
    relative='datamgmt/contracts/owned-project/review.json';parent_review=save(repo/relative,packet)
    image_identity=dict(image_id=image,git_revision=revision,user='10001:10001',source_status='dirty')
    preparations=root/'preparations';preparations.mkdir();reviews=root/'reviews';reviews.mkdir();executions=root/'executions';executions.mkdir()
    requests=[]
    for i in range(10 if scenario=='coverage' else 1):
        pid=f'large-p{i+1:02d}';marker=prepare_partition_task(repository_root=repo,review_file=relative,
            expected_review_sha256=parent_review['sha256'],expected_roots_sha256=pin(roots)['sha256'],expected_image_id=image,
            actual_image=image_identity,output_dir=preparations/pid,partition_id=pid)
        names=dict(parent_scope='parent.scope.draft.json',parent_budget='parent.budget.draft.json',
            partition_selection='partition.selection.draft.json',draft_scope='scope.draft.json',draft_budget='budget.draft.json',draft_request='request.draft.json')
        files={role:pin(marker.parent/name) for role,name in names.items()}
        files.update(preparation=pin(marker),parent_review=parent_review,roots=pin(roots),certificate=certificate)
        selected=save(reviews/(pid+'-selection.json'),dict(version=1,status='SELECTED_PROJECT_PARTITION_REVIEW_METADATA',
            source_mode='project_snapshot',partition_id=pid,attempt_id=f'owned-{scenario}-{pid}-first',files=files,expected_manifest_sha256=request['manifest_sha256']))
        reviewed=prepare_project_partition_review(selection_file=Path(selected['path']),expected_selection_sha256=selected['sha256'],
            actual_image=image_identity,output_dir=reviews/pid)
        requests.append(str(materialize_project_partition_request(review_file=reviewed,expected_review_sha256=pin(reviewed)['sha256'],
            actual_image=image_identity,output_dir=executions/pid,result_file=root/'results/batch.json',scratch_parent=root/'results/disk-scratch')))
    (root/'results').mkdir()
    request_list=root/'requests.json';save(request_list,requests)
    golden_path=root/'project-golden.json';save(golden_path,dict(version=1,synthetic_only=True,real_source_read=False,
        test_fixture_only=True,objects=selected_golden,rows_per_table=1000 if scenario=='coverage' else rows,
        row_frame_bytes=None if scenario in ('coverage','reader-multi-merge') else 65573))
    receipt=root/'fixture-receipt.json';save(receipt,dict(version=1,test_fixture_only=True,real_source_read=False,new_real_expectations=0,scenario=scenario))
    return dict(requests=request_list,golden=golden_path,receipt=receipt,sqlite=db)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--image',required=True)
    parser.add_argument('--revision',required=True);parser.add_argument('--scenario',required=True,choices=('coverage','wide-fit','wide-over','reader-multi-merge'))
    args=parser.parse_args();root=Path('/data/var/run/project');root.mkdir()
    result=build(root,image=args.image,revision=args.revision,scenario=args.scenario)
    print(json.dumps({k:str(v) for k,v in result.items()}))

"""Fixed artificial widths, first bigint column, remaining nullable text columns.

Only our newly created SQLite fixture is writable. Golden digests use a hand
encoder, not the installed production row encoder or sorter.
"""
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import sys

from xiangrugu_datamgmt.identity import source_object_id
from xiangrugu_datamgmt.naming import allocate_columns
from xiangrugu_datamgmt.synthetic_readonly_probe import prepare
from xiangrugu_datamgmt.snapshots import digest, inventory
from xiangrugu_datamgmt.sqlite_values import SQLiteValueLimits
from xiangrugu_datamgmt.unordered_values import UnorderedLimits


def seed(root,image,revision):
    rows=1000
    blueprint=dict(objects=[dict(representative_of=f'fixed-{i}',columns=[dict(pg_type='bigint' if n==0 or (i==0 and n<4) else 'text',allow_null_value=(n!=0 and (i!=0 or n not in (2,3)))) for n in range(width)]) for i,width in enumerate([8,11,34,6,29,42,12,10,28,55])])
    assert len(blueprint['objects'])==10 and sum(len(o['columns']) for o in blueprint['objects'])==235
    request=prepare(root,fixture_mount=Path('/data/var/input'),image_id=image,git_revision=revision)
    fixture=root/'fixture'; snapshot=fixture/'snapshots'/request['snapshot_id']
    db=snapshot/request['relative_path']
    assert db.resolve()==db and snapshot.resolve()==snapshot
    
    def bind(path,document):
        path.write_text(json.dumps(document,sort_keys=True,ensure_ascii=True))
        return hashlib.sha256(path.read_bytes()).hexdigest()
    
    def value(column,pattern,ordinal):
        if column['allow_null_value'] and pattern%7==0:
            return None
        if column['pg_type']=='bigint':
            return (-2**63,2**63-1,0,-17,2**53+1,13,32,4096)[(pattern+ordinal)%8]
        if column['pg_type']=='double precision':
            return (-1.25,0.0,2.5,13.125)[(pattern+ordinal)%4]
        return ('','汉字','é','e\u0301','line\nfeed','\x00inside','duplicate','value_'+'X'*32)[(pattern+ordinal)%8]
    
    def hand_frame(columns,values):
        cells=[]
        for column,item in zip(columns,values,strict=True):
            if item is None:
                cells.append(b'\x00')
            elif column['pg_type']=='bigint':
                cells.append(b'\x02'+struct.pack('>q',item))
            elif column['pg_type']=='double precision':
                cells.append(b'\x03'+struct.pack('>d',item))
            else:
                raw=item.encode('utf-8')
                cells.append(b'\x01'+len(raw).to_bytes(8,'big')+raw)
        payload=b''.join(cells)
        return b'R'+len(columns).to_bytes(4,'big')+len(payload).to_bytes(8,'big')+payload
    
    def row_values(columns,index):
        # Keep eight integer boundary rows. Every 97th later row repeats its predecessor.
        key=index-1 if index >= 32 and index % 97 == 0 else index
        values=[value(column,key % 32,ordinal) for ordinal,column in enumerate(columns)]
        if key >= 8:
            identity_column=next(ordinal for ordinal,column in enumerate(columns)
                                 if column['pg_type']=='bigint')
            values[identity_column]=key if key >= 32 else -1000000-key
        return tuple(values)
    
    scope_path=fixture/Path(request['scope_file']).name
    scope=json.loads(scope_path.read_text()); objects=[]; budgets=[]; golden=[]
    with sqlite3.connect(db) as connection:
        # These two tables were just created by the fixed artificial seed helper.
        connection.execute('DROP TABLE artificial_values')
        connection.execute('DROP TABLE empty_values')
        for index,definition in enumerate(blueprint['objects']):
            name=f'artificial_large_{index:02d}'
            names=[f'c_{n:03d}' for n in range(len(definition['columns']))]
            identity=source_object_id(relative_path=request['relative_path'],archive_chain=[],object_name=name,carrier='sqlite')
            allocated=allocate_columns(names,object_id=identity)
            columns=[dict(source_ordinal=n,column_key=allocated[n].identity,
                pg_type=c['pg_type'],allow_null_value=c['allow_null_value']) for n,c in enumerate(definition['columns'])]
            sql_types={'bigint':'INTEGER','double precision':'REAL','text':'TEXT'}
            declarations=[f'"{column_name}" {sql_types[column["pg_type"]]}' + ('' if column['allow_null_value'] else ' NOT NULL')
                for column_name,column in zip(names,columns,strict=True)]
            connection.execute(f'CREATE TABLE "{name}" ({", ".join(declarations)})')
            connection.executemany(f'INSERT INTO "{name}" VALUES ({", ".join("?" for _ in names)})',
                (row_values(columns,n) for n in range(rows-1,-1,-1)))
            counts=Counter()
            for index_row in range(rows):
                counts[hand_frame(columns,row_values(columns,index_row))]+=1
            assert len(counts) > rows*0.9
            schema_raw=json.dumps([[c['source_ordinal'],c['column_key'],c['pg_type'],c['allow_null_value']]
                for c in columns],ensure_ascii=True,separators=(',',':')).encode('ascii')
            schema_hash=hashlib.sha256(schema_raw).digest()
            expected=hashlib.sha256(b'XRGSET\x00\x01'+bytes.fromhex(identity)+schema_hash)
            for frame,count in sorted(counts.items()):
                for _ in range(count): expected.update(frame)
            expected.update(b'E'+rows.to_bytes(8,'big'))
            objects.append(dict(source_object_id=identity,source_object_name=name,source_columns=names,columns=columns))
            budgets.append(dict(source_object_id=identity,
                read_limits=asdict(SQLiteValueLimits(max_file_bytes=2**30,max_columns=64,max_rows=rows,
                    max_cells=rows*len(columns),max_cell_bytes=2**20,max_value_bytes=256*2**20,
                    max_vm_steps=1000000000,max_seconds=1800)),
                sort_limits=asdict(UnorderedLimits(max_rows=rows,max_columns=64,max_field_bytes=2**20,
                    max_row_bytes=2**20,max_stream_bytes=256*2**20,chunk_bytes=2*2**20,chunk_rows=4096,
                    merge_fan_in=16,max_temp_bytes=2**30,max_temp_files=1024,max_seconds=1800,workers=1))))
            golden.append(dict(source_object_id=identity,source_object_name=name,representative_of=definition['representative_of'],
                columns=len(columns),expected_count=rows,field_count=rows*len(columns),expected_sha256=expected.hexdigest(),
                schema_hash=schema_hash.hex(),distinct_artificial_frames=len(counts)))
    
    members=inventory(snapshot)
    selected=next(m for m in members if m['path']==request['relative_path'])
    certificate_path=fixture/Path(request['certificate']).name
    certificate=json.loads(certificate_path.read_text())
    certificate.update(members=members,manifest_sha256=digest(members))
    request.update(expected_size=selected['size'],expected_sha256=selected['sha256'],manifest_sha256=certificate['manifest_sha256'])
    request['certificate_sha256']=bind(certificate_path,certificate)
    scope.update(source=selected,objects=objects)
    request['scope_sha256']=bind(scope_path,scope)
    budget_path=fixture/Path(request['budget_file']).name
    request['budget_sha256']=bind(budget_path,dict(version=2,group='large',max_seconds=1800,objects=budgets))
    request['scratch_parent']=str(root/'disk-scratch')
    approval_path=fixture/'approval.json'; approval=json.loads(approval_path.read_text())
    approval['request_sha256']=digest({k:v for k,v in request.items() if k not in ('approval_file','approval_sha256')})
    request['approval_sha256']=bind(approval_path,approval)
    bind(fixture/'readonly-request.json',request)
    bind(fixture/'golden.json',dict(version=1,status='HAND_ENCODED_ARTIFICIAL_GOLDEN',synthetic_only=True,
        real_source_read=False,objects=golden,rows_per_table=rows,total_rows=10*rows,total_fields=235*rows,
        blueprint_sha256=hashlib.sha256(json.dumps(blueprint,sort_keys=True).encode()).hexdigest()))
    return request, scope, budgets, golden


def build(root, *, image, revision):
    """Only construct fixed data in a private candidate output mount."""
    from xiangrugu_datamgmt.task_partition import prepare_partition_task
    root=Path(root)
    if not root.is_absolute() or '..' in root.parts or not str(root).startswith('/data/var/run/') and str(root)!='/data/var/run':
        raise ValueError('artificial_output')
    request,scope,budgets,golden=seed(root,image,revision)
    fixture=root/'fixture'
    from xiangrugu_datamgmt.snapshots import canonical_json
    descriptor=fixture/'descriptor.json'
    descriptor.write_text(canonical_json(dict(version=1,artificial_only=True,fixture='fixed-ten-single-table-v1'))+'\n')
    request['bindings']['descriptor']['sha256']=hashlib.sha256(descriptor.read_bytes()).hexdigest()
    repo=root/'metadata-repository';repo.mkdir()
    def save(path,doc):
        path.parent.mkdir(parents=True,exist_ok=True)
        from xiangrugu_datamgmt.snapshots import write_json_exclusive
        write_json_exclusive(path,doc)
        return hashlib.sha256(path.read_bytes()).hexdigest()
    authority=dict(source_read_authorized=False,postgresql_authorized=False,contract_frozen=False,ready_for_import=False)
    roots=repo/'datamgmt/config/roots.yaml';roots.parent.mkdir(parents=True)
    roots.write_bytes((fixture/'readonly-roots.yaml').read_bytes())
    objects=[dict(obj,schema_hash=g['schema_hash'],expected_count=None,expected_sha256=None,
                  read_limits=budget['read_limits'],sort_limits=budget['sort_limits'])
             for obj,budget,g in zip(scope['objects'],budgets,golden,strict=True)]
    parent_scope=dict(snapshot_id=request['snapshot_id'],member=scope['source'],objects=10,columns=235)
    packet=dict(version=1,status='METADATA_READINESS_SUPPLEMENT_NOT_EXECUTABLE',git_revision=revision,**authority,
        scope=parent_scope,verified_artificial_deadlines=dict(candidate_seconds=1800,host_seconds=1830,transport_seconds=1880,real_mode_activated=False),bindings={})
    docs=dict(original_scope_review=dict(group='large',rule_id=request['rule_id'],scope=parent_scope,objects=objects,**authority),
        preparation=dict(objects=[dict(source_object_id=o['source_object_id'],source_object_name=o['source_object_name'],columns=o['columns'],schema_hash=o['schema_hash']) for o in objects]),
        mapping=dict(objects=[dict(source_object_id=o['source_object_id'],source_object_name=o['source_object_name'],columns=[dict(source_name=name,source_ordinal=c['source_ordinal'],column_identity=c['column_key'],approved_type=c['pg_type']) for name,c in zip(o['source_columns'],o['columns'],strict=True)]) for o in objects]),
        remaining_budget=dict(objects=[dict(source_object_id=o['source_object_id'],name=o['source_object_name'],proposed_group='large') for o in objects]))
    for role,doc in docs.items():
        relative=f'datamgmt/contracts/artificial/{role}.json'
        packet['bindings'][role]=dict(path=relative,sha256=save(repo/relative,doc))
    packet['bindings']['roots']=dict(path='datamgmt/config/roots.yaml',sha256=hashlib.sha256(roots.read_bytes()).hexdigest())
    relative='datamgmt/contracts/artificial/review.json';pin=save(repo/relative,packet)
    preparation=root/'preparations';preparation.mkdir()
    mount=Path('/data/var/input')
    def copy(name,path):
        target=fixture/name
        if target.exists():
            assert target.read_bytes()==path.read_bytes()
        else:
            target.write_bytes(path.read_bytes())
        return dict(path=str(mount/name),sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    requests=[]
    for index in range(10):
        pid=f'large-p{index+1:02d}';prefix=f'partition-{index+1:02d}'
        marker=prepare_partition_task(repository_root=repo,review_file=relative,expected_review_sha256=pin,
            expected_roots_sha256=packet['bindings']['roots']['sha256'],expected_image_id=image,
            actual_image=dict(image_id=image,git_revision=revision,user='10001:10001',source_status='dirty'),
            output_dir=preparation/pid,partition_id=pid)
        bindings=dict(descriptor=request['bindings']['descriptor'],parent_scope=copy('parent-scope.json',marker.parent/'parent.scope.draft.json'),
            parent_budget=copy('parent-budget.json',marker.parent/'parent.budget.draft.json'),
            partition_selection=copy(prefix+'-selection.json',marker.parent/'partition.selection.draft.json'))
        copy(prefix+'-preparation.json',marker)
        for key in ('scope','budget','request'):
            copy(prefix+'-draft-'+key+'.json',marker.parent/(key+'.draft.json'))
        child_scope=dict(version=1,source_read_authorized=False,synthetic_data_authorized=True,
            snapshot_id=request['snapshot_id'],source=scope['source'],rule_id=request['rule_id'],
            postgresql_authorized=False,ready_for_import=False,bindings={k:v['sha256'] for k,v in bindings.items()},objects=[scope['objects'][index]])
        child_budget=dict(version=2,group='large',max_seconds=1800,objects=[budgets[index]])
        child=dict(request,bindings=bindings,output='/data/var/run/batch.json',scratch_parent='/data/var/run/disk-scratch')
        child['scope_file']=str(mount/(prefix+'-scope.json'));child['scope_sha256']=save(fixture/(prefix+'-scope.json'),child_scope)
        child['budget_file']=str(mount/(prefix+'-budget.json'));child['budget_sha256']=save(fixture/(prefix+'-budget.json'),child_budget)
        approval=dict(version=1,status='APPROVED_READONLY_BATCH',source_mode='artificial',source_read_authorized=False,
            synthetic_data_authorized=True,stationary_readonly_window=True,postgresql_authorized=False,ready_for_import=False,
            request_sha256=digest({k:v for k,v in child.items() if k not in ('approval_file','approval_sha256')}))
        child['approval_file']=str(mount/(prefix+'-approval.json'));child['approval_sha256']=save(fixture/(prefix+'-approval.json'),approval)
        path=fixture/(prefix+'-request.json');save(path,child);requests.append(path)
    return requests


if __name__=='__main__':
    build(Path('/data/var/run'),image=sys.argv[1],revision=sys.argv[2])
    

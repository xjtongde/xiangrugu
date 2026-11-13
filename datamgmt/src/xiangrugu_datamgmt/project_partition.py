"""Pinned project-partition metadata; no source access or human authorization."""
import argparse
import copy
from dataclasses import dataclass
from functools import wraps
import hashlib
import os
from pathlib import Path
import re

from .batch_execution import read_metadata, _json, _check_cancel
from .config import load_config
from .readonly_batch import _path, _hash, _validate_members
from .snapshots import canonical_json, digest, write_json_exclusive


FLAGS=('source_read_authorized','postgresql_authorized','contract_frozen','ready_for_import')
GENERATED={'parent_scope':'parent.scope.draft.json','parent_budget':'parent.budget.draft.json',
    'partition_selection':'partition.selection.draft.json','draft_scope':'scope.draft.json',
    'draft_budget':'budget.draft.json','draft_request':'request.draft.json'}
FILES=set(GENERATED)|{'preparation','parent_review','roots','certificate'}
BINDINGS={'parent_scope','parent_budget','partition_selection','descriptor'}
REQUEST_KEYS={'roots','snapshot_id','relative_path','expected_size','expected_sha256',
    'certificate','certificate_sha256','manifest_sha256','output','image_id','git_revision',
    'rule_id','scope_file','scope_sha256','scratch_parent','roots_sha256','budget_file',
    'budget_sha256','source_mode','bindings','approval_file','approval_sha256','lifecycle_seconds'}


def require(condition):
    if not condition:raise ValueError('project_partition_identity')


def same(left,right):
    return canonical_json(left)==canonical_json(right)


def checked(function):
    @wraps(function)
    def call(*args,**kwargs):
        try:return function(*args,**kwargs)
        except FileExistsError:raise
        except (KeyError,TypeError,IndexError,OSError) as error:
            raise ValueError('project_partition_identity') from error
    return call


def _read(description,inputs,cancelled):
    _check_cancel(cancelled)
    require(type(description) is dict and description.keys()=={'path','sha256'} and _hash(description['sha256']))
    path=_path(description['path']);raw=read_metadata(path)
    require(hashlib.sha256(raw).hexdigest()==description['sha256'])
    if path in inputs:require(inputs[path]==raw)
    inputs[path]=raw
    return raw


def _load(description,inputs,cancelled):
    document=_json(_read(description,inputs,cancelled));require(type(document) is dict)
    return document


def _pin(path):
    return dict(path=str(path),sha256=hashlib.sha256(read_metadata(path)).hexdigest())


@dataclass(frozen=True)
class ProjectPartitionMetadata:
    partition_id: str
    attempt_id: str
    parent_scope: dict
    parent_budget: dict
    descriptor: dict
    input_bytes: dict


def recheck_project_partition_metadata(metadata,*,cancelled=lambda:False):
    for path,raw in metadata.input_bytes.items():
        _check_cancel(cancelled);require(read_metadata(path)==raw)
    _check_cancel(cancelled)


def _base(files,partition_id,attempt_id,image,manifest,inputs,cancelled):
    from .task_preparation import _validate_preparation
    require(type(files) is dict and files.keys()==FILES)
    require(type(partition_id) is str and re.fullmatch(r'large-p(?:0[1-9]|10)',partition_id))
    require(type(attempt_id) is str and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',attempt_id))
    require(len({d['path'] for d in files.values() if d is not None})==len(files)-(files['certificate'] is None))
    docs={role:_load(desc,inputs,cancelled) for role,desc in files.items() if role not in ('roots','certificate')}
    _read(files['roots'],inputs,cancelled)
    config=load_config(Path(files['roots']['path']),environ={})
    require(config.source.host!='synthetic')
    record=docs['preparation'];packet=docs['parent_review']
    selected_image=record['controller_checked_candidate_identity']
    if image is not None:require(same(image,selected_image))
    relative=packet['bindings']['roots']['path']
    require(type(relative) is str and relative.startswith('datamgmt/config/') and '\\' not in relative
        and not any(p in ('','.','..') for p in relative.split('/')))
    root_file=Path(files['roots']['path']);parts=Path(relative).parts
    require(root_file.parts[-len(parts):]==parts)
    repository=root_file.parents[len(parts)-1]
    review_path=Path(files['parent_review']['path']).relative_to(repository).as_posix()
    validated=_validate_preparation(repository_root=repository,review_file=review_path,
        expected_review_sha256=files['parent_review']['sha256'],expected_roots_sha256=files['roots']['sha256'],
        expected_image_id=selected_image['image_id'],actual_image=selected_image,
        output_dir=Path(files['preparation']['path']).parent)
    for path,raw in validated['inputs'].items():
        if path in inputs:require(inputs[path]==raw)
        inputs[path]=raw
    parent=docs['parent_scope'];parent_budget=docs['parent_budget'];index=int(partition_id[-2:])-1
    require(same(parent,validated['scope']) and same(parent_budget,validated['budget'])
        and parent_budget['group']=='large' and len(parent['objects'])==10
        and sum(len(o['columns']) for o in parent['objects'])==235)
    base_folder=Path(files['preparation']['path']).parent
    require(all(Path(files[role]['path'])==base_folder/name for role,name in GENERATED.items()))
    generated={name:files[role]['sha256'] for role,name in GENERATED.items()}
    require(record.keys()==validated['record'].keys()|{'parent_objects','parent_columns','partition_id','parent_review_sha256'})
    require(same(record['generated'],generated) and record['status']=='DRAFT_PARTITION_METADATA_PREPARATION'
        and record['parent_review_sha256']==files['parent_review']['sha256'] and record['partition_id']==partition_id
        and record['parent_objects']==10 and record['parent_columns']==235 and record['objects']==1
        and record['columns']==len(parent['objects'][index]['columns']))
    require(all(type(record[k]) is int for k in ('parent_objects','parent_columns','objects','columns')))
    for key,value in validated['record'].items():
        if key not in ('status','objects','columns','generated'):require(same(record.get(key),value))
    selection=dict(version=1,status='DRAFT_PARTITION_SELECTION_NOT_AUTHORIZED',**{k:False for k in FLAGS},
        partition_id=partition_id,parent_review_sha256=files['parent_review']['sha256'],
        parent_scope_sha256=files['parent_scope']['sha256'],parent_budget_sha256=files['parent_budget']['sha256'],
        source_object_id=parent['objects'][index]['source_object_id'])
    require(same(docs['partition_selection'],selection))
    bindings={k:files[k] for k in ('parent_scope','parent_budget','partition_selection')}
    expected_scope=copy.deepcopy(parent);expected_scope['objects']=parent['objects'][index:index+1]
    expected_scope['bindings'].update({k:v['sha256'] for k,v in bindings.items()})
    expected_budget=copy.deepcopy(parent_budget);expected_budget['objects']=parent_budget['objects'][index:index+1]
    expected_request=copy.deepcopy(validated['request']);expected_request['bindings']=bindings
    require(same(docs['draft_scope'],expected_scope) and same(docs['draft_budget'],expected_budget)
        and same(docs['draft_request'],expected_request))
    cert=None
    if files['certificate'] is not None:
        cert=_load(files['certificate'],inputs,cancelled);_validate_members(cert['members'])
        require(cert['version']==1 and type(cert['version']) is int and cert['status']=='VERIFIED'
            and cert['snapshot_id']==parent['snapshot_id'] and cert['source_path']==str(config.source.path)
            and cert['manifest_sha256']==digest(cert['members'])
            and [m for m in cert['members'] if m.get('path')==parent['source']['path']]==[parent['source']])
        if manifest is not None:require(_hash(manifest) and cert['manifest_sha256']==manifest)
    elif manifest is not None:require(_hash(manifest))
    descriptor=dict(version=1,status='PROJECT_PARTITION_METADATA_SELECTION',source_mode='project_snapshot',
        partition_id=partition_id,attempt_id=attempt_id,preparation=files['preparation'],parent_review=files['parent_review'],
        parent_scope_sha256=files['parent_scope']['sha256'],parent_budget_sha256=files['parent_budget']['sha256'],
        partition_selection_sha256=files['partition_selection']['sha256'],image=image,snapshot_id=parent['snapshot_id'],
        source=parent['source'],roots_sha256=files['roots']['sha256'],
        certificate_sha256=None if cert is None else files['certificate']['sha256'],manifest_sha256=manifest,
        rule_id=parent['rule_id'],**{k:False for k in FLAGS})
    metadata=ProjectPartitionMetadata(partition_id,attempt_id,parent,parent_budget,descriptor,inputs)
    recheck_project_partition_metadata(metadata,cancelled=cancelled)
    return metadata,config


def _selection(description,image,inputs,cancelled):
    chosen=_load(description,inputs,cancelled)
    require(chosen.keys()=={'version','status','source_mode','partition_id','attempt_id','files','expected_manifest_sha256'}
        and type(chosen['version']) is int and chosen['version']==1
        and chosen['status']=='SELECTED_PROJECT_PARTITION_REVIEW_METADATA' and chosen['source_mode']=='project_snapshot')
    metadata,config=_base(chosen['files'],chosen['partition_id'],chosen['attempt_id'],image,
        chosen['expected_manifest_sha256'],inputs,cancelled)
    missing=[name for name,value in (('certificate',chosen['files']['certificate']),
        ('manifest',chosen['expected_manifest_sha256']),('image',image)) if value is None]
    return chosen,metadata,config,missing


def _output(path,config):
    path=Path(path)
    require(path.is_absolute() and not any(path==p or p in path.parents for p in (config.source.path,config.snapshot_root)))
    path=_path(str(path));require(path.parent.is_dir())
    if path.exists():raise FileExistsError('project_partition_output')
    return path


def _publish(out,name,document,generated,metadata,cancelled):
    stage=out/('.'+name+'.incomplete');write_json_exclusive(stage,document)
    recheck_project_partition_metadata(metadata,cancelled=cancelled)
    for file,pin in generated.items():require(hashlib.sha256(read_metadata(out/file)).hexdigest()==pin)
    require(read_metadata(stage)==(canonical_json(document)+'\n').encode('utf-8'))
    _check_cancel(cancelled);os.link(stage,out/name)
    return out/name


def _review_template():
    return dict(status='DRAFT_PROJECT_PARTITION_REQUEST_REVIEW',source_mode='project_snapshot',
        **{k:False for k in FLAGS},approval_file=None,approval_sha256=None,output=None,scratch_parent=None,
        scope_file=None,scope_sha256=None,budget_file=None,budget_sha256=None)


@checked
def prepare_project_partition_review(*,selection_file,expected_selection_sha256,actual_image,output_dir,cancelled=lambda:False):
    selection=dict(path=str(selection_file),sha256=expected_selection_sha256)
    chosen,metadata,config,missing=_selection(selection,actual_image,{},cancelled)
    out=_output(output_dir,config);out.mkdir()
    template=_review_template()
    generated={}
    for name,doc in (('descriptor.review.json',metadata.descriptor),('request.review.json',template)):
        write_json_exclusive(out/name,doc);generated[name]=_pin(out/name)['sha256']
    record=dict(version=1,status='DRAFT_PROJECT_PARTITION_REVIEW_NOT_EXECUTABLE',selection=selection,
        actual_image=actual_image,missing=missing,generated=generated,**{k:False for k in FLAGS})
    return _publish(out,'review.json',record,generated,metadata,cancelled)


@checked
def materialize_project_partition_request(*,review_file,expected_review_sha256,actual_image,output_dir,result_file,scratch_parent,cancelled=lambda:False):
    inputs={};review=_load(dict(path=str(review_file),sha256=expected_review_sha256),inputs,cancelled)
    require(review.keys()=={'version','status','selection','actual_image','missing','generated',*FLAGS}
        and type(review['version']) is int and review['version']==1
        and review['status']=='DRAFT_PROJECT_PARTITION_REVIEW_NOT_EXECUTABLE' and review['missing']==[]
        and same(actual_image,review['actual_image']) and all(review[k] is False for k in FLAGS))
    chosen,metadata,config,missing=_selection(review['selection'],actual_image,inputs,cancelled);require(not missing)
    require(review['generated'].keys()=={'descriptor.review.json','request.review.json'})
    for name,pin in review['generated'].items():_read(dict(path=str(Path(review_file).parent/name),sha256=pin),inputs,cancelled)
    descriptor_path=Path(review_file).parent/'descriptor.review.json'
    require(same(_json(inputs[descriptor_path]),metadata.descriptor))
    require(same(_json(inputs[Path(review_file).parent/'request.review.json']),_review_template()))
    result=Path(result_file);scratch=Path(scratch_parent)
    for path in (result,scratch):
        require(config.evidence_root in path.parents and not any(path==p or p in path.parents for p in (config.source.path,config.snapshot_root)))
        _path(str(path))
    require(result!=scratch and result not in inputs and scratch not in inputs)
    out=_output(output_dir,config);out.mkdir();index=int(metadata.partition_id[-2:])-1
    files=chosen['files'];bindings={k:files[k] for k in ('parent_scope','parent_budget','partition_selection')}
    bindings['descriptor']=_pin(descriptor_path)
    scope={k:v for k,v in metadata.parent_scope.items() if k not in ('status','contract_frozen')}
    scope.update(source_read_authorized=True,synthetic_data_authorized=False,objects=metadata.parent_scope['objects'][index:index+1],
        bindings={k:v['sha256'] for k,v in bindings.items()})
    budget={k:v for k,v in metadata.parent_budget.items() if k!='status'}
    budget['objects']=metadata.parent_budget['objects'][index:index+1]
    write_json_exclusive(out/'scope.json',scope);write_json_exclusive(out/'budget.json',budget)
    request=dict(source_mode='project_snapshot',snapshot_id=metadata.descriptor['snapshot_id'],relative_path=metadata.descriptor['source']['path'],
        expected_size=metadata.descriptor['source']['size'],expected_sha256=metadata.descriptor['source']['sha256'],
        rule_id=metadata.descriptor['rule_id'],image_id=actual_image['image_id'],git_revision=actual_image['git_revision'],
        lifecycle_seconds=1800,manifest_sha256=chosen['expected_manifest_sha256'],bindings=bindings,output=str(result),scratch_parent=str(scratch))
    for role,key in (('roots','roots'),('certificate','certificate'),('scope','scope_file'),('budget','budget_file')):
        desc=files[role] if role in files else _pin(out/(role+'.json'))
        request[key]=desc['path'];request[{'scope_file':'scope_sha256','budget_file':'budget_sha256'}.get(key,key+'_sha256')]=desc['sha256']
    approval=dict(version=1,status='APPROVED_READONLY_BATCH',source_mode='project_snapshot',source_read_authorized=True,
        synthetic_data_authorized=False,stationary_readonly_window=True,postgresql_authorized=False,ready_for_import=False,request_sha256=digest(request))
    write_json_exclusive(out/'approval.json',approval)
    request.update(approval_file=str(out/'approval.json'),approval_sha256=_pin(out/'approval.json')['sha256'])
    generated={name:_pin(out/name)['sha256'] for name in ('scope.json','budget.json','approval.json')}
    return _publish(out,'request.json',request,generated,metadata,cancelled)


@checked
def validate_project_partition_request(*,request,controller_evidence,cancelled=lambda:False):
    if (type(request) is dict and request.get('source_mode')=='project_snapshot'
            and type(request.get('bindings')) is dict and request['bindings'].keys()!=BINDINGS):
        raise ValueError('large_real_disabled')
    require(type(request) is dict and request.keys()==REQUEST_KEYS and request.get('source_mode')=='project_snapshot'
        and type(controller_evidence) is dict
        and controller_evidence.keys()=={'controller_request_sha256','controller_verified_image','controller_lifecycle_seconds'}
        and _hash(controller_evidence['controller_request_sha256'])
        and type(controller_evidence['controller_lifecycle_seconds']) is int and controller_evidence['controller_lifecycle_seconds']==1800
        and request.get('lifecycle_seconds')==1800 and type(request['lifecycle_seconds']) is int)
    bindings=request['bindings'];require(type(bindings) is dict and bindings.keys()==BINDINGS)
    inputs={};descriptor=_load(bindings['descriptor'],inputs,cancelled)
    files={k:bindings[k] for k in ('parent_scope','parent_budget','partition_selection')}
    files.update(preparation=descriptor['preparation'],parent_review=descriptor['parent_review'],
        roots=dict(path=request['roots'],sha256=request['roots_sha256']),
        certificate=dict(path=request['certificate'],sha256=request['certificate_sha256']))
    base=Path(files['preparation']['path']).parent;record=_load(files['preparation'],inputs,cancelled)
    for role in ('draft_scope','draft_budget','draft_request'):
        name=GENERATED[role];files[role]=dict(path=str(base/name),sha256=record['generated'][name])
    metadata,config=_base(files,descriptor['partition_id'],descriptor['attempt_id'],
        controller_evidence['controller_verified_image'],request['manifest_sha256'],inputs,cancelled)
    destinations=[_path(request[k]) for k in ('output','scratch_parent')]
    require(destinations[0]!=destinations[1])
    for path in destinations:
        require(config.evidence_root in path.parents and path not in inputs
            and not any(path==p or p in path.parents for p in (config.source.path,config.snapshot_root)))
    require(same(descriptor,metadata.descriptor) and descriptor['image']['image_id']==request['image_id']
        and descriptor['image']['git_revision']==request['git_revision'])
    scope=_load(dict(path=request['scope_file'],sha256=request['scope_sha256']),inputs,cancelled)
    budget=_load(dict(path=request['budget_file'],sha256=request['budget_sha256']),inputs,cancelled)
    approval=_load(dict(path=request['approval_file'],sha256=request['approval_sha256']),inputs,cancelled)
    index=int(metadata.partition_id[-2:])-1
    expected_scope={k:v for k,v in metadata.parent_scope.items() if k not in ('status','contract_frozen')}
    expected_scope.update(source_read_authorized=True,synthetic_data_authorized=False,
        objects=metadata.parent_scope['objects'][index:index+1],bindings={k:v['sha256'] for k,v in bindings.items()})
    expected_budget={k:v for k,v in metadata.parent_budget.items() if k!='status'}
    expected_budget['objects']=metadata.parent_budget['objects'][index:index+1]
    require(same(scope,expected_scope) and same(budget,expected_budget))
    for key,value in dict(snapshot_id=descriptor['snapshot_id'],relative_path=descriptor['source']['path'],
        expected_size=descriptor['source']['size'],expected_sha256=descriptor['source']['sha256'],rule_id=descriptor['rule_id']).items():require(same(request.get(key),value))
    expected_approval=dict(version=1,status='APPROVED_READONLY_BATCH',source_mode='project_snapshot',source_read_authorized=True,
        synthetic_data_authorized=False,stationary_readonly_window=True,postgresql_authorized=False,ready_for_import=False,
        request_sha256=digest({k:v for k,v in request.items() if k not in ('approval_file','approval_sha256')}))
    require(same(approval,expected_approval))
    recheck_project_partition_metadata(metadata,cancelled=cancelled)
    return metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',type=Path,required=True);parser.add_argument('--selection-sha256',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    for name in ('actual-image-id','git-revision','image-user','source-status'):parser.add_argument('--'+name)
    args=parser.parse_args();values=[args.actual_image_id,args.git_revision,args.image_user,args.source_status]
    if any(values) and not all(values):parser.error('actual image identity must be complete')
    image=None if not any(values) else dict(image_id=values[0],git_revision=values[1],user=values[2],source_status=values[3])
    prepare_project_partition_review(selection_file=args.selection,expected_selection_sha256=args.selection_sha256,
        actual_image=image,output_dir=args.output_dir)
    return 0


if __name__=='__main__':raise SystemExit(main())

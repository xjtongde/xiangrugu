"""Closed, value-free diagnostics; worker failure is distinct from stop reason."""
import errno
import hashlib
from pathlib import Path

from .batch_execution import read_metadata, _json
from .snapshots import SnapshotError
from .sqlite_diagnostic import SQLiteDiagnosticError
from .sqlite_values import SQLiteValueReadError
from .unordered_values import UnorderedValueError, valid_digest

STAGES = frozenset(('task_preflight', 'request_preflight', 'snapshot_verify',
    'batch_preflight', 'batch_digest_before', 'object_read_sort', 'batch_digest_after',
    'metadata_recheck', 'stage_save', 'task_staged'))
CODES = {
    'control': frozenset(('real_execution_closed', 'controller_pin', 'controller_request_identity',
        'controller_image_identity', 'controller_request_changed', 'controller_source_mode',
        'readonly_mount', 'cancelled', 'lifecycle_budget', 'lifecycle_timeout',
        'request', 'controller_evidence', 'source_mode', 'path', 'input_identity', 'approval',
        'bindings', 'path_alias', 'binding_identity', 'output_path', 'artificial_roots',
        'evidence_root', 'source_identity', 'snapshot_alias', 'certificate_scope',
        'certificate_member', 'scope_authority', 'budget', 'small_budget', 'medium_budget',
        'scope_object', 'budget_object', 'metadata_changed', 'metadata_path_or_budget',
        'metadata_budget', 'duplicate_key', 'nonfinite')),
    'cache': frozenset(('read_cache_unavailable', 'read_cache_advice', 'read_cache_policy')),
    'sqlite': frozenset(('invalid_identity', 'invalid_scope', 'unsafe_path', 'sidecar_present',
        'readonly_settings_unavailable', 'input_error', 'cancelled', 'time_limit', 'vm_limit',
        'file_limit', 'identity_mismatch', 'source_changed', 'unsupported_object',
        'column_scope_mismatch', 'nullability_mismatch', 'row_or_cell_limit', 'null_not_allowed',
        'storage_type_mismatch', 'invalid_utf8', 'value_byte_limit', 'source_io_error',
        'sqlite_error', 'column_limit', 'batch_closed', 'batch_incomplete', 'batch_concurrency',
        'metadata_limit', 'output_limit', 'object_limit')),
    'sort': frozenset(('structure', 'unsupported_type', 'budget', 'count', 'temp_corrupt',
        'timeout', 'input_error', 'cancelled', 'scratch_path', 'io_error', 'disk_full', 'cleanup_error')),
    'snapshot': frozenset(('snapshot_verification_failed',)),
    'os': frozenset(('io_error', 'disk_full', 'permission_denied', 'output_exists')),
    'internal': frozenset(('controlled_task_failed',)),
}

def classify(error):
    """Follow only explicit causes of our generic wrappers, never raw messages."""
    seen = set()
    for _ in range(8):
        if id(error) in seen:
            break
        seen.add(id(error))
        if type(error) in (SQLiteValueReadError, SQLiteDiagnosticError, UnorderedValueError):
            domain = 'sort' if type(error) is UnorderedValueError else 'sqlite'
            code = error.code
            if code == 'input_error' and error.__cause__ is not None:
                error = error.__cause__
                continue
            if type(code) is str and code in CODES[domain]:
                return domain, code
            break
        if type(error) is ValueError and len(error.args) == 1 and type(error.args[0]) is str:
            for domain in ('control', 'cache'):
                if error.args[0] in CODES[domain]:
                    return domain, error.args[0]
        if isinstance(error, SnapshotError):
            return 'snapshot', 'snapshot_verification_failed'
        if isinstance(error, OSError):
            if isinstance(error, FileExistsError):
                return 'os', 'output_exists'
            return 'os', {errno.ENOSPC: 'disk_full', errno.EACCES: 'permission_denied',
                          errno.EPERM: 'permission_denied'}.get(error.errno, 'io_error')
        break
    return 'internal', 'controlled_task_failed'

class FailureTrace:
    def __init__(self):
        self.stage, self.object_index, self.completed_objects = 'task_preflight', None, 0

    def advance(self, stage, object_index=None, completed_objects=0):
        if (type(stage) is not str or stage not in STAGES or type(completed_objects) is not int
                or not 0 <= completed_objects <= 75
                or (object_index is not None and (type(object_index) is not int
                    or not 1 <= object_index <= 75 or object_index <= completed_objects))):
            raise ValueError('diagnostic_stage')
        self.stage, self.object_index, self.completed_objects = stage, object_index, completed_objects

    def failure(self, error, request_sha256, source_mode):
        domain, code = classify(error)
        return dict(version=1, status='CONTROLLED_TASK_FAILURE',
            request_sha256=request_sha256 if valid_digest(request_sha256) else None,
            source_mode=source_mode, domain=domain, code=code, stage=self.stage,
            object_index=self.object_index, completed_objects=self.completed_objects,
            ready_for_import=False, raw_values_emitted=False)

def read_worker_failure(path, expected_request_sha256, source_mode):
    """A missing/invalid diagnostic never changes the supervision stop reason."""
    if path is None:
        return None, None, 'not_requested'
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return None, None, 'missing'
    try:
        raw = read_metadata(path)
        if len(raw) > 4096:
            raise ValueError('diagnostic_budget')
        value = _json(raw)
        keys = {'version', 'status', 'request_sha256', 'source_mode', 'domain', 'code', 'stage',
                'object_index', 'completed_objects', 'ready_for_import', 'raw_values_emitted'}
        if (type(value) is not dict or value.keys() != keys or type(value['version']) is not int
                or value['version'] != 1 or value['status'] != 'CONTROLLED_TASK_FAILURE'
                or not valid_digest(value['request_sha256'])
                or value['request_sha256'] != expected_request_sha256
                or value['source_mode'] != source_mode or type(value['domain']) is not str
                or value['domain'] not in CODES or type(value['code']) is not str
                or value['code'] not in CODES[value['domain']] or type(value['stage']) is not str
                or value['stage'] not in STAGES or value['ready_for_import'] is not False
                or value['raw_values_emitted'] is not False):
            raise ValueError('diagnostic_invalid')
        FailureTrace().advance(value['stage'], value['object_index'], value['completed_objects'])
        return value, hashlib.sha256(raw).hexdigest(), 'valid'
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        return None, None, 'invalid'

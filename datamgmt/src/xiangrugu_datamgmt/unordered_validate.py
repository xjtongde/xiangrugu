"""Independent typed inputs; exact complete-row multiplicities, never hash equality."""
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
from itertools import groupby

from .unordered_values import (UnorderedSchema, UnorderedValueError,
                               header_bytes, schema_bytes, trailer_bytes, valid_digest)
from .value_sort import SortProgress, SortWorkspace, sort_rows


@dataclass(frozen=True)
class UnorderedEvidence:
    kind: str
    reference: str
    sha256: str

    def __post_init__(self):
        if (type(self.kind) is not str or self.kind not in ("synthetic", "source", "target")
                or type(self.reference) is not str or not self.reference
                or not valid_digest(self.sha256)):
            raise UnorderedValueError("structure")


@dataclass(frozen=True)
class UnorderedInput:
    schema: UnorderedSchema
    rows: object
    evidence: UnorderedEvidence

    def __post_init__(self):
        if type(self.schema) is not UnorderedSchema or type(self.evidence) is not UnorderedEvidence:
            raise UnorderedValueError("structure")


@dataclass(frozen=True)
class RowDifference:
    row_sha256: str
    frame_bytes: int
    source_count: int
    target_count: int
    code: str


@dataclass(frozen=True)
class UnorderedReport:
    _data: dict

    def to_dict(self) -> dict:
        return deepcopy(self._data)


def row_digest(frame):
    return hashlib.sha256(frame).hexdigest()


class _ManagedRows:
    """One close owner even when sorting exits before the other input starts."""
    def __init__(self, rows):
        self.rows, self.closed = rows, False

    def __next__(self):
        return next(self.rows)

    def close(self):
        if not self.closed:
            self.closed = True
            close = getattr(self.rows, "close", None)
            if close is not None:
                close()


def _close_inputs(owned, data):
    for side, rows in owned.items():
        try:
            rows.close()
        except Exception:
            data.update(result="comparison_error", partial=True, error_code="input_error",
                        error_side=side, source_sha256=None, target_sha256=None)


def _groups(sorted_rows, digest, workspace):
    frames = sorted_rows.iter_frames()
    try:
        for frame, group in groupby(frames):
            count = 0
            for item in group:
                workspace.check()
                count += 1
                if count >= 2**64:
                    raise UnorderedValueError("count")
                digest.update(item)
            yield frame, count
    finally:
        frames.close()


def compare_unordered(expected, source, target, *, limits, scratch_parent, cancelled=None) -> UnorderedReport:
    if (type(expected) is not UnorderedSchema or type(source) is not UnorderedInput
            or type(target) is not UnorderedInput):
        raise UnorderedValueError("structure")
    data = {
        "format_version": "sqlite-unordered-values-v1", "source_object_id": expected.source_object_id,
        "schema_hash": hashlib.sha256(schema_bytes(expected)).hexdigest(),
        "source_evidence": asdict(source.evidence), "target_evidence": asdict(target.evidence),
        "partial": True, "source_count": None, "target_count": None,
        "source_fields": None, "target_fields": None,
        "source_stream_bytes": None, "target_stream_bytes": None,
        "source_sha256": None, "target_sha256": None,
        "difference_patterns": 0, "missing_rows": 0, "excess_rows": 0, "differences": [],
        "details_truncated": False, "limits": asdict(limits), "resource_stats": {},
        "cleanup_complete": True, "residual_directory": None,
        "result": "comparison_error", "error_code": None, "error_side": None,
        "scan_index": None, "column_key": None,
    }
    for side in ("source", "target"):
        data[side+"_progress"] = asdict(SortProgress()) | {"comparison_complete": False}
    owned = {"source": _ManagedRows(source.rows), "target": _ManagedRows(target.rows)}
    if source.schema != expected or target.schema != expected:
        data["error_code"] = "structure"
        _close_inputs(owned, data)
        return UnorderedReport(data)
    workspace = None
    left = right = None
    completed = False
    hashes = {side: hashlib.sha256(header_bytes(expected)) for side in ("source", "target")}
    try:
        workspace = SortWorkspace(scratch_parent, limits, cancelled=cancelled)
        with workspace:
            a = sort_rows(expected, owned["source"], workspace=workspace, side="source")
            b = sort_rows(expected, owned["target"], workspace=workspace, side="target")
            left = _groups(a, hashes["source"], workspace)
            right = _groups(b, hashes["target"], workspace)
            try:
                x, y = next(left, None), next(right, None)
                while x is not None or y is not None:
                    workspace.check()
                    if y is None or (x is not None and x[0] < y[0]):
                        frame, n = x
                        wanted, actual = n, 0
                        x = next(left, None)
                    elif x is None or y[0] < x[0]:
                        frame, n = y
                        wanted, actual = 0, n
                        y = next(right, None)
                    else:
                        frame, wanted, actual = x[0], x[1], y[1]
                        x, y = next(left, None), next(right, None)
                    if wanted != actual:
                        data["difference_patterns"] += 1
                        data["missing_rows"] += max(wanted-actual, 0)
                        data["excess_rows"] += max(actual-wanted, 0)
                        if len(data["differences"]) < limits.max_differences:
                            code = "missing" if actual == 0 else "excess" if wanted == 0 else "count_mismatch"
                            data["differences"].append(asdict(RowDifference(
                                row_digest(frame), len(frame), wanted, actual, code)))
                        else:
                            data["details_truncated"] = True
            finally:
                left.close()
                right.close()
            workspace.check()
            if not all(workspace.progress[side].sort_complete for side in ("source", "target")):
                raise UnorderedValueError("temp_corrupt")
            for side, out in (("source", a), ("target", b)):
                hashes[side].update(trailer_bytes(out.row_count))
                data[side+"_count"] = out.row_count
                data[side+"_fields"] = out.field_count
                data[side+"_stream_bytes"] = out.stream_bytes
            completed = True
        data["partial"] = False
        data["result"] = "comparison_failed" if data["difference_patterns"] else "comparison_equal"
        if data["result"] == "comparison_equal":
            for side in ("source", "target"):
                data[side+"_sha256"] = hashes[side].hexdigest()
    except UnorderedValueError as error:
        data.update(error_code=error.code, error_side=error.side,
                    scan_index=error.scan_index, column_key=error.column_key)
    except Exception:
        data["error_code"] = "input_error"
    finally:
        _close_inputs(owned, data)
        for side in ("source", "target"):
            p = workspace.progress.get(side, SortProgress()) if workspace else SortProgress()
            data[side+"_progress"] = asdict(p) | {"comparison_complete": completed}
        data["resource_stats"] = asdict(workspace.stats) if workspace else {}
        data["cleanup_complete"] = workspace.cleanup_complete if workspace and workspace.path is not None else True
        if not data["cleanup_complete"]:
            data["residual_directory"] = str(workspace.path)
    return UnorderedReport(data)

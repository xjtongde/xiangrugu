"""Pure ordered comparison of independent typed inputs, not G0-G7 acceptance."""
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
import hashlib

from .canonical import (
    ValueContractError, ValueLimits, ValueSchema, ValueStreamState,
    check_cancelled, next_row, schema_bytes, valid_digest,
)


@dataclass(frozen=True)
class ValueEvidence:
    kind: str
    reference: str
    sha256: str

    def __post_init__(self):
        if (type(self.kind) is not str or self.kind not in ("synthetic", "source", "target")
                or type(self.reference) is not str or not self.reference.strip()
                or not valid_digest(self.sha256)):
            raise ValueContractError("structure")


@dataclass(frozen=True)
class ValueInput:
    schema: ValueSchema
    rows: Iterator[tuple[object, ...]]
    evidence: ValueEvidence

    def __post_init__(self):
        if (type(self.schema) is not ValueSchema or type(self.evidence) is not ValueEvidence
                or not isinstance(self.rows, Iterator)):
            raise ValueContractError("structure")


@dataclass(frozen=True)
class ValueDifference:
    rownum: int | None
    column_key: str | None
    code: str
    expected_type: str | None = None
    actual_type: str | None = None
    expected_bytes: int | None = None
    actual_bytes: int | None = None
    expected_sha256: str | None = None
    actual_sha256: str | None = None


@dataclass(frozen=True)
class ComparisonReport:
    format_version: int
    source_object_id: str
    schema_hash: str
    source_evidence: ValueEvidence
    target_evidence: ValueEvidence
    source_count: int
    target_count: int
    source_partial: bool
    target_partial: bool
    source_sha256: str | None
    target_sha256: str | None
    compared_fields: int
    difference_count: int
    differences: tuple[ValueDifference, ...]
    details_truncated: bool
    limits: ValueLimits
    result: str
    error_code: str | None

    def to_dict(self) -> dict:
        result = asdict(self)
        result["differences"] = [asdict(item) for item in self.differences]
        return result


def _cell_description(cell):
    kind = {0: "null", 1: "text", 2: "bigint"}[cell[0]]
    overhead = 9 if cell[0] == 1 else 1
    return kind, len(cell) - overhead, hashlib.sha256(cell).hexdigest()


def compare_ordered(expected: ValueSchema, source: ValueInput, target: ValueInput, *,
                    expected_count: int, limits: ValueLimits,
                    cancelled: Callable[[], bool] | None = None) -> ComparisonReport:
    if type(expected_count) is not int or not 0 <= expected_count <= limits.max_rows:
        raise ValueContractError("count")
    differences = []
    total = 0
    error_code = None
    compared_fields = 0
    states = [None, None]
    summaries = [None, None]
    done = [False, False]

    def add(difference):
        nonlocal total, error_code
        total += 1
        if error_code is None:
            error_code = difference.code
        if len(differences) < limits.max_differences:
            differences.append(difference)

    def report():
        counts = [state.row_count if state else 0 for state in states]
        return ComparisonReport(
            expected.format_version, expected.source_object_id,
            hashlib.sha256(schema_bytes(expected)).hexdigest(),
            source.evidence, target.evidence, *counts,
            summaries[0] is None, summaries[1] is None,
            summaries[0].sha256 if summaries[0] else None,
            summaries[1].sha256 if summaries[1] else None,
            compared_fields, total, tuple(differences), total > len(differences),
            limits, "comparison_failed" if total else "comparison_equal", error_code,
        )

    if source.schema != expected or target.schema != expected:
        add(ValueDifference(None, None, "structure"))
        return report()
    inputs = (source, target)
    for side in (0, 1):
        try:
            states[side] = ValueStreamState(expected, limits)
        except ValueContractError as error:
            add(ValueDifference(error.rownum, error.column_key, error.code))
            done[side] = True

    while not all(done):
        try:
            check_cancelled(cancelled)
        except ValueContractError as error:
            add(ValueDifference(None, None, error.code))
            return report()
        encoded = [None, None]
        for side in (0, 1):
            if done[side]:
                continue
            try:
                check_cancelled(cancelled)
            except ValueContractError as error:
                add(ValueDifference(None, None, error.code))
                return report()
            try:
                values = next_row(inputs[side].rows)
            except StopIteration:
                # Even the final EOF must not turn a concurrent cancellation into success.
                try:
                    check_cancelled(cancelled)
                except ValueContractError as error:
                    add(ValueDifference(None, None, error.code))
                    return report()
                summaries[side] = states[side].finish()
                done[side] = True
                continue
            except ValueContractError as error:
                add(ValueDifference(states[side].row_count + 1, None, error.code))
                done[side] = True
                continue
            try:
                encoded[side] = states[side].accept(values)
            except ValueContractError as error:
                add(ValueDifference(error.rownum, error.column_key, error.code))
                done[side] = True
        left, right = encoded
        if left is not None and right is not None:
            for column, a, b in zip(expected.columns, left.cells, right.cells, strict=True):
                compared_fields += 1
                if a != b:
                    ak, al, ah = _cell_description(a)
                    bk, bl, bh = _cell_description(b)
                    add(ValueDifference(left.rownum, column.column_key, "value",
                                        ak, bk, al, bl, ah, bh))
        elif left is not None or right is not None:
            row = left if left is not None else right
            add(ValueDifference(row.rownum, None, "count"))
    for summary in summaries:
        if summary is not None and summary.row_count != expected_count:
            add(ValueDifference(None, None, "count"))
    return report()

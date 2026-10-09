"""Bounded source-byte expectation bridge, without file/DB I/O or importer."""
from dataclasses import replace
import hashlib

from .canonical import ValueColumn, ValueContractError, ValueLimits, ValueSchema, summarize_rows, valid_digest
from .identity import source_object_id
from .naming import allocate_columns
from .source_text import TextReadError, TextReadLimits, read_utf8_tsv


def schema_from_approved(obj: dict, decision: dict):
    """Bind explicit approved text columns to an exact outer-file reading decision.

    This is a non-executable sidecar projection, not ReleaseContract validation.
    Schema/table approval is intentionally not promoted to import readiness.
    """
    try:
        if any(obj[key] is not True for key in (
            "source_column_types_approved", "source_column_nullable_approved",
            "source_column_mapping_approved", "derived_rownum_mapping_approved",
        )):
            raise ValueError()
        selector = obj["selector"]
        if (obj["rule_id"] != decision["rule_id"]
                or obj["reading_decision_rule_id"] != decision["rule_id"]
                or any(selector[key] != decision[key] for key in (
                    "relative_path", "archive_chain", "archive_ordinals"))
                or selector["archive_chain"] != [] or selector["archive_ordinals"] != []
                or obj["carrier"] != "tsv" or obj["raw_expected"]["kind"] != "file"
                or not valid_digest(decision["raw_sha256"])
                or type(decision["raw_size"]) is not int or decision["raw_size"] < 0
                or obj["raw_expected"]["sha256"] != decision["raw_sha256"]
                or obj["raw_expected"]["size"] != decision["raw_size"]
                or type(decision["bom_as_signature"]) is not bool
                or type(decision["backslash_escape"]) is not bool
                or decision["codec"] != ("utf-8-sig" if decision["bom_as_signature"] else "utf-8")):
            raise ValueError()
        identity = source_object_id(relative_path=selector["relative_path"], archive_chain=[],
                                    object_name=obj["object_name"], carrier="tsv")
        if identity != obj["source_object_id"]:
            raise ValueError()
        count = obj["source_record_count"]
        if type(count) is not int or not 0 <= count <= ValueLimits().max_rows:
            raise ValueError()
        derived = obj["derived_columns"]
        if (len(derived) != 1 or derived[0]["mapping_approved"] is not True
                or derived[0]["target_name"] != "__src_rownum"
                or derived[0]["target_type"] != "bigint"
                or derived[0]["origin"] != "one-based data record order excluding header"
                or derived[0]["range"] != [1, count]):
            raise ValueError()
        columns = obj["source_columns"]
        if not 1 <= len(columns) < ValueLimits().max_columns:
            raise ValueError()
        header = tuple(column["original_name"] for column in columns)
        if any(type(name) is not str for name in header):
            raise ValueError()
        maps = allocate_columns(list(header), object_id=identity)
        encoded_columns = []
        for ordinal, (column, mapping) in enumerate(zip(columns, maps, strict=True), 1):
            if (type(column["source_column_ordinal"]) is not int
                    or column["source_column_ordinal"] != ordinal
                    or column["column_id"] != mapping.identity
                    or column["target_name"] != mapping.target
                    or column["target_type"] != "text" or column["nullable"] is not False
                    or any(column[key] is not True for key in (
                        "type_approved", "nullable_approved", "column_mapping_approved"))
                    # UTF-8-SIG applies once to file start, never per field.
                    or column["encoding"] != dict(codec="utf-8", errors="strict",
                                                  column=header[ordinal-1],
                                                  object_name=obj["object_name"])):
                raise ValueError()
            encoded_columns.append(ValueColumn(mapping.identity, mapping.target, "text", False))
        encoded_columns.append(ValueColumn("derived:__src_rownum", "__src_rownum", "bigint", False))
        return ValueSchema(identity, tuple(encoded_columns)), header
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueContractError("structure") from None


def summarize_text_values(raw: bytes, *, schema: ValueSchema,
                          expected_header: tuple[str, ...], expected_raw_sha256: str,
                          expected_raw_size: int, expected_count: int,
                          bom_as_signature: bool, backslash_escape: bool,
                          limits: ValueLimits = ValueLimits(),
                          read_limits: TextReadLimits = TextReadLimits()):
    """Exclude the verified header; preserve every text value and derive rownum.

    A summary is returned only after exact source bytes, full parse, header,
    count and normal value-stream completion. It is not import acceptance.
    """
    if (type(raw) is not bytes or type(schema) is not ValueSchema
            or type(limits) is not ValueLimits or type(read_limits) is not TextReadLimits
            or type(expected_header) is not tuple
            or any(type(name) is not str for name in expected_header)
            or len(expected_header) != len(schema.columns) - 1
            or any(column.pg_type != "text" for column in schema.columns[:-1])
            or not valid_digest(expected_raw_sha256)
            or type(expected_raw_size) is not int or expected_raw_size < 0
            or type(bom_as_signature) is not bool or type(backslash_escape) is not bool):
        raise ValueContractError("structure")
    if type(expected_count) is not int or not 0 <= expected_count <= limits.max_rows:
        raise ValueContractError("count")
    if len(raw) > read_limits.max_bytes or len(schema.columns) > limits.max_columns:
        raise ValueContractError("budget")
    if len(raw) != expected_raw_size or hashlib.sha256(raw).hexdigest() != expected_raw_sha256:
        raise ValueContractError("source_bytes")
    bounded_read = replace(
        read_limits, max_records=min(read_limits.max_records, limits.max_rows + 1),
        max_columns=min(read_limits.max_columns, limits.max_columns),
        max_field_bytes=min(read_limits.max_field_bytes, limits.max_field_bytes),
    )
    try:
        records = read_utf8_tsv(raw, bom_as_signature=bom_as_signature,
                               backslash_escape=backslash_escape, limits=bounded_read)
    except TextReadError as error:
        code = "budget" if error.code.endswith("_limit") else "source_syntax"
        raise ValueContractError(code, rownum=error.record_ordinal) from None
    if not records or records[0] != expected_header:
        raise ValueContractError("structure")
    if len(records) - 1 != expected_count:
        raise ValueContractError("count")
    rows = (records[index] + (index,) for index in range(1, len(records)))
    return summarize_rows(schema, rows, limits=limits)

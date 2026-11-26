"""Versioned release assertions, not authority to read sources or write a DB."""
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from jsonschema.validators import extend
from referencing import Registry
from referencing.exceptions import NoSuchResource, Unresolvable
from referencing.jsonschema import DRAFT202012
import yaml

from .config import UniqueLoader
from .identity import canonical_relative_path
from .model import Digest, Disposition, FrozenRecord

Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
Token = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")]
Count = Annotated[int, Field(ge=0, strict=True)]
_SCHEMA_STEP_LIMIT = 2_000_000


class ContractError(ValueError):
    pass


class ContractRecord(FrozenRecord):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True,
                              revalidate_instances="always")


class MemberSelector(ContractRecord):
    relative_path: Text
    archive_chain: tuple[Text, ...] = ()
    archive_ordinals: tuple[Count, ...] = ()

    @model_validator(mode="after")
    def exact_paths(self):
        if len(self.archive_chain) != len(self.archive_ordinals):
            raise ValueError("Physical archive ordinals must describe every container level")
        for path in (self.relative_path, *self.archive_chain):
            # Brackets are literal filename bytes, notably XLSX package members.
            # The ledger compares full location tuples; it never expands glob syntax.
            if any(character in path for character in "*?"):
                raise ValueError("Star and question-mark selectors are unsupported")
        return self

    @property
    def location(self):
        return self.relative_path, self.archive_chain, self.archive_ordinals


class MemberExpectation(ContractRecord):
    kind: Literal["file", "directory", "symlink", "special"]
    sha256: Digest | None
    size: Count | None
    signature: Literal["unknown", "zip", "sqlite", "ole", "tiff", "pdf"]


class ColumnEncoding(ContractRecord):
    object_name: Text
    column: Text
    codec: Text
    errors: Literal["strict"] = "strict"

    @field_validator("codec")
    @classmethod
    def known_codec(cls, value):
        try:
            # Nonempty input makes bytes.decode enforce the text-codec boundary.
            # A proper multibyte codec may reject this one-byte probe; that is valid.
            b"\x00".decode(value, errors="strict")
        except UnicodeError:
            pass
        except (LookupError, TypeError) as error:
            raise ValueError("A known bytes-to-text codec is required") from error
        return value


class ColumnMapping(ContractRecord):
    """Ordered source->target column mapping with approved width/scale (optional extension)."""
    ordinal: Count
    source_column: Text
    target_column: Text
    pg_type: Annotated[str, Field(pattern=r"^(text|bigint|numeric\([1-9][0-9]*,[0-9]+\)|double precision)$")]
    nullable: bool
    source_width_bytes: Count | None = None
    source_decimals: Count | None = None

    @model_validator(mode="after")
    def consistent_width_scale(self):
        if self.ordinal < 1:
            raise ValueError("Column ordinals are one-based")
        if self.source_width_bytes is not None and self.source_width_bytes < 1:
            raise ValueError("Approved source width must be positive")
        if self.pg_type.startswith("numeric("):
            precision, scale = self.pg_type[len("numeric("):-1].split(",")
            if self.source_width_bytes != int(precision) or self.source_decimals != int(scale):
                raise ValueError("numeric width/scale must equal the approved source width and decimals")
        elif self.source_decimals not in (None, 0):
            raise ValueError("Non-numeric columns cannot declare nonzero decimals")
        return self


class DerivedRownum(ContractRecord):
    """Fixed semantics: one-based physical source row number, never nullable."""
    target_column: Literal["__src_rownum"]
    pg_type: Literal["bigint"]
    nullable: Literal[False]
    origin: Literal["one_based_physical_source_row"]


class DuplicateReconciliation(ContractRecord):
    """Duplicate accounting on actual value columns, excluding the unique source rownum."""
    key: Literal["value_columns_excluding_src_rownum"]
    expected_groups: Count
    expected_extra_rows: Count
    count_includes_duplicates: Literal[True]

    @model_validator(mode="after")
    def consistent_arithmetic(self):
        if self.expected_groups == 0 and self.expected_extra_rows != 0:
            raise ValueError("Extra duplicate rows require at least one duplicate group")
        if self.expected_groups > 0 and self.expected_extra_rows < self.expected_groups:
            raise ValueError("Every duplicate group contributes at least one extra row")
        return self


class GeometryExpectation(ContractRecord):
    """Spatial geometry expectation with canonical digest and original-coordinate storage."""
    geometry_type: Literal["Point"]
    dimensions: Literal[2]
    srid: Annotated[int, Field(ge=1, strict=True)]
    canonical_format: Literal["XRGGEOM-v1"]
    expected_sha256: Digest
    coordinate_storage: Literal["preserve_original_ieee754_xy_no_swap_or_transform"]


class PrimaryKey(ContractRecord):
    """Ordered composite primary key: target columns in declared source PK order.

    The order is semantically significant (it mirrors the source PK declaration order),
    so it is stored as an explicit ordered tuple rather than a set.
    """
    columns: Annotated[tuple[Text, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_columns(self):
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("Primary key columns must be unique")
        return self


class ObjectTarget(ContractRecord):
    object_name: Text
    schema_name: Literal["cbdb", "chgis", "harv"] = Field(alias="schema")
    table: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")]
    expected_count: Count | None
    expected_sha256: Digest | None
    columns: tuple[ColumnMapping, ...] | None = None
    derived_rownum: DerivedRownum | None = None
    duplicate_reconciliation: DuplicateReconciliation | None = None
    geometry: GeometryExpectation | None = None
    primary_key: PrimaryKey | None = None

    @model_validator(mode="after")
    def extended_mapping_consistency(self):
        if self.primary_key is not None and self.columns is None:
            raise ValueError("primary_key requires an explicit columns mapping")
        if self.columns is not None:
            ordinals = [column.ordinal for column in self.columns]
            if ordinals != list(range(1, len(ordinals) + 1)):
                raise ValueError("Column ordinals must be contiguous and ordered from 1")
            if len({column.target_column for column in self.columns}) != len(self.columns):
                raise ValueError("Target column names must be unique within a mapping")
            if len({column.source_column for column in self.columns}) != len(self.columns):
                raise ValueError("Source column identities must be unique within a mapping")
            if self.derived_rownum is not None and any(
                    column.target_column == self.derived_rownum.target_column for column in self.columns):
                raise ValueError("Derived rownum column must not collide with mapped source columns")
            if self.primary_key is not None:
                mapped = {column.target_column: column for column in self.columns}
                missing = [name for name in self.primary_key.columns if name not in mapped]
                if missing:
                    raise ValueError(f"Primary key columns must be mapped target columns: {missing}")
                nullable_pk = [name for name in self.primary_key.columns if mapped[name].nullable]
                if nullable_pk:
                    raise ValueError(f"Primary key columns must be NOT NULL: {nullable_pk}")
        return self


class DispositionRule(ContractRecord):
    rule_id: Token
    selector: MemberSelector
    expected: MemberExpectation
    disposition: Disposition
    reason: Text
    format_family: Token
    encodings: tuple[ColumnEncoding, ...]
    targets: tuple[ObjectTarget, ...]
    validator: Token
    mirror_of: Token | None = None
    mirror_evidence_sha256: Digest | None = None

    @model_validator(mode="after")
    def consistent_action(self):
        if self.disposition != Disposition.BLOCKED:
            canonical_relative_path(self.selector.relative_path)
            for path in self.selector.archive_chain:
                canonical_relative_path(path[:-1] if self.expected.kind == "directory" and path.endswith("/") else path)
            if self.expected.kind == "file" and (self.expected.sha256 is None or self.expected.size is None):
                raise ValueError("Every readable file requires raw byte assertions")
            if self.expected.kind in ("symlink", "special"):
                raise ValueError("Unsupported source kinds must be BLOCKED")
        if self.disposition == Disposition.IMPORT:
            if self.expected.kind != "file" or not self.targets:
                raise ValueError("IMPORT requires a file and explicit logical targets")
        elif self.targets:
            raise ValueError("Only IMPORT can have business targets")
        if self.disposition == Disposition.MIRROR:
            if self.expected.kind != "file" or self.mirror_of is None or self.mirror_evidence_sha256 is None:
                raise ValueError("MIRROR requires primary rule and byte equality evidence")
        elif self.mirror_of is not None or self.mirror_evidence_sha256 is not None:
            raise ValueError("Mirror fields are exclusive to MIRROR")
        target_names = [target.object_name for target in self.targets]
        encoding_keys = [(encoding.object_name, encoding.column) for encoding in self.encodings]
        if len(set(target_names)) != len(target_names) or len(set(encoding_keys)) != len(encoding_keys):
            raise ValueError("Object and column declarations must be unique")
        if self.disposition == Disposition.IMPORT and any(name not in target_names for name, _ in encoding_keys):
            raise ValueError("Column encodings must belong to declared logical objects")
        return self


class ContractReview(ContractRecord):
    approved_by: Text
    approved_at: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")]
    approval_ref: Text

    @field_validator("approved_at")
    @classmethod
    def valid_timestamp(cls, value):
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value


class ContractException(ContractRecord):
    rule_id: Token
    code: Literal["checksum_nul", "checksum_path_binding"]
    raw_sha256: Digest
    reason: Text


class ReleaseContract(ContractRecord):
    version: Annotated[int, Field(strict=True, ge=1, le=1)]
    release_id: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*$")]
    source_version: Text
    inventory_sha256: Digest
    status: Literal["draft", "frozen"]
    review: ContractReview | None
    exceptions: tuple[ContractException, ...] = ()
    rules: Annotated[tuple[DispositionRule, ...], Field(min_length=1)]

    @field_validator("release_id")
    @classmethod
    def calendar_date(cls, value):
        date.fromisoformat(value[:10])
        return value

    @model_validator(mode="after")
    def release_consistency(self):
        ids = [rule.rule_id for rule in self.rules]
        if len(set(ids)) != len(ids):
            raise ValueError("Rule identities must be unique")
        if self.status == "frozen":
            if self.review is None:
                raise ValueError("Frozen contracts require an explicit review record")
            if any(target.expected_count is None or target.expected_sha256 is None for rule in self.rules for target in rule.targets):
                raise ValueError("Frozen contracts require complete logical object expectations")
            for rule in self.rules:
                if rule.rule_id in FIRST_BATCH_RULES:
                    _check_first_batch_rule(rule)
        return self

    def canonical_bytes(self):
        document = self.model_dump(mode="json", by_alias=True)
        document["rules"].sort(key=lambda rule: rule["rule_id"])
        document["exceptions"].sort(key=lambda exception: (exception["rule_id"], exception["code"], exception["raw_sha256"]))
        for rule in document["rules"]:
            rule["targets"].sort(key=lambda target: target["object_name"])
            rule["encodings"].sort(key=lambda encoding: (encoding["object_name"], encoding["column"]))
            for target in rule["targets"]:
                # Digest compatibility: absent optional extensions must not alter pre-extension digests.
                for key in ("columns", "derived_rownum", "duplicate_reconciliation", "geometry",
                            "primary_key"):
                    if target.get(key) is None:
                        target.pop(key, None)
        return json.dumps(document, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @property
    def sha256(self):
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


FIRST_BATCH_RULES = ("m002709", "m002717", "m004812", "m006642", "m008002", "m008003", "m008004")
FIRST_BATCH_SPATIAL_RULES = ("m002709", "m002717")
FIRST_BATCH_APPROVED_SRID = 4326


def _check_first_batch_rule(rule) -> None:
    """Per-rule first-batch extension requirements; shared by candidate and frozen gates."""
    if rule.disposition != Disposition.IMPORT:
        raise ContractError(f"{rule.rule_id}: first-batch rules must be IMPORT")
    if len(rule.targets) != 1:
        raise ContractError(f"{rule.rule_id}: exactly one logical target per first-batch rule")
    target = rule.targets[0]
    for field in ("columns", "derived_rownum", "duplicate_reconciliation"):
        if getattr(target, field) is None:
            raise ContractError(f"{rule.rule_id}: missing required extension field {field}")
    if not target.columns:
        raise ContractError(f"{rule.rule_id}: column mapping must not be empty")
    if target.expected_count is None or target.expected_sha256 is None:
        raise ContractError(f"{rule.rule_id}: expected_count and expected_sha256 are required")
    reconciliation = target.duplicate_reconciliation
    if target.expected_count < reconciliation.expected_groups + reconciliation.expected_extra_rows:
        raise ContractError(f"{rule.rule_id}: duplicate reconciliation exceeds expected_count")
    if rule.rule_id in FIRST_BATCH_SPATIAL_RULES:
        if target.geometry is None:
            raise ContractError(f"{rule.rule_id}: spatial object requires a geometry expectation")
        if target.geometry.srid != FIRST_BATCH_APPROVED_SRID:
            raise ContractError(f"{rule.rule_id}: geometry SRID must be the approved 4326")
    elif target.geometry is not None:
        raise ContractError(f"{rule.rule_id}: text object must not carry a geometry expectation")


def validate_first_batch_seven(contract: ReleaseContract) -> None:
    """Dedicated first-batch validation: missing or contradictory extension fields fail closed.

    Separate from general parsing so existing contracts keep their original rules.
    """
    if contract.status != "draft":
        raise ContractError("First-batch candidate must be unfrozen (draft)")
    if sorted(rule.rule_id for rule in contract.rules) != sorted(FIRST_BATCH_RULES):
        raise ContractError("Exactly the seven first-batch rules are required")
    for rule in contract.rules:
        _check_first_batch_rule(rule)


def contract_schema():
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **ReleaseContract.model_json_schema()}


def _check_json_domain(value):
    """Reject YAML-only types, recursive aliases and excessive expansion."""
    nodes = 0

    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        if depth > 128 or nodes > 1_000_000:
            raise ContractError("JSON document exceeds validation budget")
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise ContractError("JSON object keys must be strings")
            for child in item.values():
                visit(child, depth + 1)
        elif type(item) is list:
            for child in item:
                visit(child, depth + 1)
        elif type(item) is float:
            if not math.isfinite(item):
                raise ContractError("JSON numbers must be finite")
        elif item is not None and type(item) not in (str, int, bool):
            raise ContractError("Document contains non-JSON values")

    visit(value, 0)


def _deny_schema_retrieval(uri):
    raise NoSuchResource(ref=uri)


def _check_schema_references(schema):
    pending = [schema]
    schema_nodes = set()
    references = []
    while pending:
        item = pending.pop()
        schema_nodes.add(id(item))
        if type(item) is bool:
            continue
        if "$id" in item:
            raise ContractError("Schema base identifiers are not supported")
        if "$schema" in item and item["$schema"] != Draft202012Validator.META_SCHEMA["$id"]:
            raise ContractError("Only Draft 2020-12 is supported")
        if item is not schema and "$schema" in item:
            raise ContractError("Nested dialect declarations are not supported")
        for keyword in ("$ref", "$dynamicRef"):
            if keyword in item and not item[keyword].startswith("#"):
                raise ContractError("Only local fragment references are supported")
            if keyword in item:
                references.append(item[keyword])
        # Draft-specific Schema positions, not const/default/examples data.
        pending.extend(DRAFT202012.subresources_of(item))
    resolver = Registry(retrieve=_deny_schema_retrieval).resolver_with_root(
        DRAFT202012.create_resource(schema),
    )
    for reference in references:
        target = resolver.lookup(reference).contents
        if id(target) not in schema_nodes or target is schema:
            raise ContractError("References must target declared non-root Schema nodes")


def validate_contract_document(document, schema):
    """Independent raw JSON Schema gate. Never invokes the contract model."""
    try:
        _check_json_domain(document)
        _check_json_domain(schema)
        if type(schema) is not dict or schema.get("$schema") != Draft202012Validator.META_SCHEMA["$id"]:
            raise ContractError("Only explicit Draft 2020-12 schemas are supported")
        Draft202012Validator.check_schema(schema)
        _check_schema_references(schema)
        steps = 0

        def bounded(keyword):
            def apply(validator, value, instance, subschema):
                nonlocal steps
                steps += 1
                if steps > _SCHEMA_STEP_LIMIT:
                    raise ContractError("Schema validation exceeds execution budget")
                yield from keyword(validator, value, instance, subschema)
            return apply

        validator_type = extend(
            Draft202012Validator,
            {name: bounded(keyword) for name, keyword in Draft202012Validator.VALIDATORS.items()},
        )
        validator_type(schema, registry=Registry(retrieve=_deny_schema_retrieval)).validate(document)
    except (SchemaError, ValidationError, Unresolvable, ValueError, TypeError, AttributeError, RecursionError):
        # jsonschema exception messages/chains contain the rejected instance.
        raise ContractError("Invalid JSON Schema or raw contract document") from None


def _json_mapping(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("Contract keys must be unique")
        result[key] = value
    return result


def load_contract(path: Path) -> ReleaseContract:
    """Strict local JSON/YAML loader. No source or database access."""
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(16 * 1024**2 + 1)
        if len(raw) > 16 * 1024**2:
            raise ContractError("Contract exceeds size budget")
        text = raw.decode("utf-8", errors="strict")
        data = json.loads(text, object_pairs_hook=_json_mapping) if Path(path).suffix.lower() == ".json" else yaml.load(text, Loader=UniqueLoader)
        validate_contract_document(data, contract_schema())
        return ReleaseContract.model_validate(data)
    except (OSError, ValueError, yaml.YAMLError, RecursionError) as error:
        raise ContractError("Invalid or unreadable release contract") from None

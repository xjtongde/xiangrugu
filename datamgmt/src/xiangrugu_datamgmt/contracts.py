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


class ObjectTarget(ContractRecord):
    object_name: Text
    schema_name: Literal["cbdb", "chgis", "harv"] = Field(alias="schema")
    table: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")]
    expected_count: Count | None
    expected_sha256: Digest | None


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
    code: Literal["checksum_nul"]
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
        return self

    def canonical_bytes(self):
        document = self.model_dump(mode="json", by_alias=True)
        document["rules"].sort(key=lambda rule: rule["rule_id"])
        document["exceptions"].sort(key=lambda exception: (exception["rule_id"], exception["code"], exception["raw_sha256"]))
        for rule in document["rules"]:
            rule["targets"].sort(key=lambda target: target["object_name"])
            rule["encodings"].sort(key=lambda encoding: (encoding["object_name"], encoding["column"]))
        return json.dumps(document, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @property
    def sha256(self):
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


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

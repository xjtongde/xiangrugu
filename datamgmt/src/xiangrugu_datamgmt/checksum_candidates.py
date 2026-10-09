"""Validate draft checksum proposals without applying inventory exceptions.

Only exterior ledgers are supported. Caller supplies exact raw ledger bytes
from a verified snapshot; this API opens no files and performs no name search.
There is deliberately no runtime/activation API. Frozen release integration
remains a separate gate; preview success never changes strict inventory evidence.
"""
import hashlib
from pathlib import PurePosixPath
import re
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .contracts import ContractRecord, Count, Digest, Text, Token
from .identity import canonical_relative_path
from .inventory import InventoryManifest

PositiveCount = Annotated[int, Field(gt=0, strict=True)]


class ChecksumCandidate(ContractRecord):
    rule_id: Token
    ledger: Text
    raw_sha256: Digest
    raw_size: PositiveCount
    reason: Text

    @field_validator("ledger")
    @classmethod
    def relative_ledger(cls, value):
        return canonical_relative_path(value)


class TrailingNulCandidate(ChecksumCandidate):
    kind: Literal["trailing_nul"]
    valid_lines: PositiveCount
    trailing_nul_bytes: PositiveCount


class PathBindingCandidate(ChecksumCandidate):
    kind: Literal["exact_path_binding"]
    line: PositiveCount
    raw_name: Text
    declared_target: Text
    resolved_target: Text
    expected_sha256: Digest
    expected_size: Count

    @field_validator("declared_target", "resolved_target")
    @classmethod
    def relative_target(cls, value):
        return canonical_relative_path(value)


CandidateRule = Annotated[TrailingNulCandidate | PathBindingCandidate, Field(discriminator="kind")]


class ChecksumCandidates(ContractRecord):
    version: Literal[1]
    status: Literal["draft"]
    release_id: Token
    source_version: Text
    inventory_sha256: Digest
    rules: Annotated[tuple[CandidateRule, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def unambiguous_rules(self):
        if len({r.rule_id for r in self.rules}) != len(self.rules):
            raise ValueError("duplicate candidate rule id")
        if len({r.ledger for r in self.rules}) != len(self.rules):
            raise ValueError("multiple candidates for one ledger are unsupported")
        return self


def _record(line):
    match = re.fullmatch(r"([0-9a-fA-F]{64}) ([ *])(.*)", line.decode("utf-8", errors="strict"))
    if not match:
        raise ValueError("invalid prefix checksum record")
    digest, _, raw_name = match.groups()
    name = raw_name[2:] if raw_name.startswith("./") else raw_name
    canonical_relative_path(name)
    return digest.lower(), raw_name, name


def preview_checksum_candidates(manifest: InventoryManifest, candidates: ChecksumCandidates,
                                raw_ledgers: dict[str, bytes]):
    candidates = ChecksumCandidates.model_validate(candidates)
    if manifest.sha256 != candidates.inventory_sha256:
        raise ValueError("candidate inventory digest differs")
    checks = []
    for rule in candidates.rules:
        entries = [e for e in manifest.entries if e.relative_path == rule.ledger
                   and not e.archive_chain and not e.archive_ordinals]
        raw = raw_ledgers.get(rule.ledger)
        if (len(entries) != 1 or entries[0].kind != "file" or type(raw) is not bytes
                or len(raw) != rule.raw_size or hashlib.sha256(raw).hexdigest() != rule.raw_sha256
                or (entries[0].size, entries[0].sha256) != (rule.raw_size, rule.raw_sha256)):
            raise ValueError("raw ledger bytes or inventory assertions differ")
        assertions = [c for c in manifest.checksums if c.ledger == rule.ledger
                      and not c.archive_chain and not c.archive_ordinals]
        check = {"rule_id": rule.rule_id, "kind": rule.kind, "ledger": rule.ledger,
                 "raw_sha256": rule.raw_sha256, "raw_size": len(raw)}
        if isinstance(rule, TrailingNulCandidate):
            prefix, tail = raw[:-rule.trailing_nul_bytes], raw[-rule.trailing_nul_bytes:]
            if (len(tail) != rule.trailing_nul_bytes or tail.count(b"\0") != len(tail) or b"\0" in prefix
                    or not prefix.endswith(b"\n") or prefix.count(b"\n") != rule.valid_lines):
                raise ValueError("prefix or exact trailing NUL bytes differ")
            lines = prefix[:-1].split(b"\n")
            records = [_record(line) for line in lines]
            if len({name for _, _, name in records}) != len(records):
                raise ValueError("duplicate prefix checksum record")
            if len(assertions) != len(records):
                raise ValueError("prefix assertion count differs")
            for number, ((digest, raw_name, name), assertion) in enumerate(zip(records, assertions), 1):
                target = str(PurePosixPath(rule.ledger).parent / name)
                if (assertion.line, assertion.raw_name, assertion.target, assertion.expected_sha256,
                    assertion.matched) != (number, raw_name, target, digest, True):
                    raise ValueError("prefix checksum assertions are not all matched")
            check.update(valid_lines=len(records), trailing_nul_bytes=len(tail),
                         tail_offset=len(prefix), prefix_assertions_matched=len(records))
        else:
            lines = raw.split(b"\n")
            if rule.line > len(lines):
                raise ValueError("binding line is absent")
            digest, raw_name, name = _record(lines[rule.line - 1])
            declared = str(PurePosixPath(rule.ledger).parent / name)
            expected = [c for c in assertions if c.line == rule.line]
            if (digest, raw_name, declared) != (rule.expected_sha256, rule.raw_name, rule.declared_target):
                raise ValueError("binding declaration differs from raw ledger")
            if (len(expected) != 1 or expected[0].matched
                    or (expected[0].raw_name, expected[0].target, expected[0].expected_sha256)
                    != (raw_name, declared, digest)):
                raise ValueError("binding strict assertion differs")
            if any(e.relative_path == declared and not e.archive_chain for e in manifest.entries):
                raise ValueError("declared target exists; binding cannot mask it")
            resolved = [e for e in manifest.entries if e.relative_path == rule.resolved_target
                        and not e.archive_chain and not e.archive_ordinals]
            if (len(resolved) != 1 or resolved[0].kind != "file"
                    or (resolved[0].size, resolved[0].sha256) != (rule.expected_size, digest)):
                raise ValueError("explicit resolved target size or digest differs")
            check.update(line=rule.line, raw_name=raw_name, declared_target=declared,
                         resolved_target=rule.resolved_target, expected_size=rule.expected_size,
                         expected_sha256=digest, strict_assertion_matched=False)
        checks.append(check)
    return {"version": 1, "status": "DRAFT_PREVIEW_ONLY", "release_id": candidates.release_id,
            "source_version": candidates.source_version, "inventory_sha256": manifest.sha256,
            "candidate_checks_passed": True, "runtime_applied": False, "ready_for_import": False,
            "strict_inventory_complete": manifest.complete, "strict_issue_count": len(manifest.issues),
            "checks": checks}

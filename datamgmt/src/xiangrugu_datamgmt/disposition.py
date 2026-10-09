"""Deterministic full-member accounting; never executes a declared validator."""
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json

from .contracts import ReleaseContract
from .inventory import InventoryEntry
from .model import Disposition


@dataclass(frozen=True)
class LedgerIssue:
    code: str
    rule_id: str = ""
    relative_path: str = ""
    archive_chain: tuple[str, ...] = ()
    archive_ordinals: tuple[int, ...] = ()


@dataclass(frozen=True)
class DispositionRecord:
    member: InventoryEntry
    rule_ids: tuple[str, ...]
    disposition: Disposition | None
    reason: str
    explained: bool


@dataclass(frozen=True)
class Coverage:
    total: int
    matched: int
    unmatched: int
    multiple: int
    unexplained: int
    blocked: int
    errors: int

    @property
    def percent(self):
        return 100 * self.matched / self.total if self.total else 0

    @property
    def conforms(self):
        return self.total > 0 and self.matched == self.total and not (self.unmatched or self.multiple or self.unexplained or self.blocked or self.errors)


@dataclass(frozen=True)
class DispositionLedger:
    release_id: str
    inventory_sha256: str
    contract_sha256: str
    status: str
    records: tuple[DispositionRecord, ...]
    issues: tuple[LedgerIssue, ...]

    @classmethod
    def evaluate(cls, manifest, contract: ReleaseContract):
        # Revalidate even typed inputs built via model_construct/model_copy.
        contract = ReleaseContract.model_validate(contract.model_dump(by_alias=True))
        issues = []
        if manifest.sha256 != contract.inventory_sha256:
            issues.append(LedgerIssue("inventory_mismatch"))
        if not manifest.complete:
            issues.append(LedgerIssue("incomplete_inventory"))
        if not manifest.entries:
            issues.append(LedgerIssue("empty_inventory"))
        # Exceptions are declarations only until the narrowly scoped Task 6 reader exists.
        if contract.exceptions:
            issues.append(LedgerIssue("exception_not_implemented"))
        by_location = defaultdict(list)
        by_id = {rule.rule_id: rule for rule in contract.rules}
        for rule in contract.rules:
            by_location[rule.selector.location].append(rule)
        used = set()
        records = []
        target_locations = {}
        primary_bytes = {}
        for rule in sorted(contract.rules, key=lambda item: item.rule_id):
            if rule.disposition == Disposition.IMPORT:
                identity = rule.expected.sha256, rule.expected.size
                if identity in primary_bytes:
                    issues.append(LedgerIssue("mirror_required", rule.rule_id))
                primary_bytes[identity] = rule.rule_id
            for target in rule.targets:
                location = target.schema_name, target.table
                if location in target_locations:
                    issues.append(LedgerIssue("target_collision", rule.rule_id))
                target_locations[location] = rule.rule_id
            if rule.disposition == Disposition.MIRROR:
                primary = by_id.get(rule.mirror_of)
                if primary is None or primary.disposition != Disposition.IMPORT or (rule.expected.sha256, rule.expected.size) != (primary.expected.sha256, primary.expected.size):
                    issues.append(LedgerIssue("invalid_mirror", rule.rule_id))
        seen = set()
        for member in sorted(manifest.entries, key=lambda item: (item.relative_path, item.archive_chain, item.archive_ordinals)):
            location = member.relative_path, member.archive_chain, member.archive_ordinals
            if location in seen:
                issues.append(LedgerIssue("duplicate_inventory_location", relative_path=member.relative_path,
                                          archive_chain=member.archive_chain, archive_ordinals=member.archive_ordinals))
            seen.add(location)
            matches = sorted(by_location.get(location, ()), key=lambda rule: rule.rule_id)
            used.update(rule.rule_id for rule in matches)
            if len(matches) != 1:
                issues.append(LedgerIssue("unmatched_member" if not matches else "multiple_matches", relative_path=member.relative_path,
                                          archive_chain=member.archive_chain, archive_ordinals=member.archive_ordinals))
                records.append(DispositionRecord(member, tuple(rule.rule_id for rule in matches), None, "", False))
                continue
            rule = matches[0]
            expected = rule.expected
            explained = (member.kind, member.sha256, member.size, member.signature) == (expected.kind, expected.sha256, expected.size, expected.signature)
            if not explained:
                issues.append(LedgerIssue("stale_assertion", rule.rule_id, *location))
            records.append(DispositionRecord(member, (rule.rule_id,), rule.disposition, rule.reason, explained))
        for rule_id in sorted(set(by_id) - used):
            issues.append(LedgerIssue("unused_rule", rule_id))
        return cls(contract.release_id, manifest.sha256, contract.sha256, contract.status, tuple(records),
                   tuple(sorted(issues, key=lambda issue: (issue.code, issue.rule_id, issue.relative_path, issue.archive_chain, issue.archive_ordinals))))

    def coverage(self):
        return Coverage(total=len(self.records), matched=sum(len(record.rule_ids) == 1 for record in self.records),
                        unmatched=sum(not record.rule_ids for record in self.records), multiple=sum(len(record.rule_ids) > 1 for record in self.records),
                        unexplained=sum(not record.explained for record in self.records),
                        blocked=sum(record.disposition == Disposition.BLOCKED for record in self.records), errors=len(self.issues))

    @property
    def ready_for_import(self):
        """Contract gate only. Not a G0-G7 certificate or external authorization."""
        return self.status == "frozen" and self.coverage().conforms

    def canonical_bytes(self):
        from dataclasses import asdict
        return json.dumps(asdict(self), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @property
    def sha256(self):
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

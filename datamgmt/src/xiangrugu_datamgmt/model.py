"""Immutable records for source provenance, runs, artifacts and validation."""
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .identity import member_id, canonical_relative_path

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Revision = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
RequiredText = Annotated[str, Field(min_length=1)]


class Disposition(str, Enum):
    IMPORT = "IMPORT"
    MIRROR = "MIRROR"
    NON_TABULAR = "NON_TABULAR"
    BLOCKED = "BLOCKED"


class FrozenRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)


class SourceMember(FrozenRecord):
    release_id: RequiredText
    relative_path: str
    archive_chain: tuple[str, ...] = ()
    sha256: Digest
    size: int = Field(ge=0, strict=True)
    carrier: RequiredText
    disposition: Disposition

    @field_validator("relative_path")
    @classmethod
    def canonical_path(cls, value):
        return canonical_relative_path(value)

    @field_validator("archive_chain")
    @classmethod
    def canonical_archive_chain(cls, value):
        for member in value:
            canonical_relative_path(member)
        return value

    @property
    def source_member_id(self) -> str:
        return member_id(release_id=self.release_id, relative_path=self.relative_path, archive_chain=self.archive_chain, sha256=self.sha256)


class ImportRun(FrozenRecord):
    run_id: RequiredText
    release_id: RequiredText
    vcs_ref: Revision
    config_sha256: Digest
    state: RequiredText  # Task 8 owns transition rules, not this value record.


class Artifact(FrozenRecord):
    artifact_id: RequiredText
    run_id: RequiredText
    kind: RequiredText
    relative_path: str
    sha256: Digest
    size: int = Field(ge=0, strict=True)

    @field_validator("relative_path")
    @classmethod
    def canonical_path(cls, value):
        return canonical_relative_path(value)


class ValidationResult(FrozenRecord):
    run_id: RequiredText
    gate: Literal["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"]
    status: Literal["CONFORMS", "FAILED", "BLOCKED"]
    evidence_sha256: Digest
    checked: int = Field(ge=0, strict=True)
    mismatches: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def consistent_result(self):
        if self.mismatches > self.checked or (self.status == "CONFORMS" and self.mismatches):
            raise ValueError("Validation counts contradict the result")
        return self

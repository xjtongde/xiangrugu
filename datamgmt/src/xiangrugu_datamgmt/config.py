"""Load deployment values from the authoritative roots file without connecting."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator
import yaml


class ConfigError(ValueError):
    pass


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class SourceRoot(StrictModel):
    path: Path
    host: str
    role: Literal["authoritative-source"]

    @field_validator("path")
    @classmethod
    def absolute_path(cls, value: Path) -> Path:
        if not value.is_absolute() or ".." in value.parts:
            raise ValueError("An absolute source path is required")
        return value


class TargetConfig(StrictModel):
    instance: Literal["pg32b"]
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    database: Literal["xiangrugu"]
    user: str = Field(min_length=1)
    password: SecretStr | None = Field(default=None, exclude=True, repr=False)
    password_file: Path | None = Field(default=None, exclude=True, repr=False)

    @field_validator("port")
    @classmethod
    def avoid_production_port(cls, value: int) -> int:
        if value == 5432:
            raise ValueError("The pg32 production port is forbidden")
        return value


class RuntimeConfig(StrictModel):
    source: SourceRoot
    target: TargetConfig
    snapshot_root: Path
    evidence_root: Path

    @field_validator("snapshot_root", "evidence_root")
    @classmethod
    def absolute_path(cls, value: Path) -> Path:
        return SourceRoot.absolute_path(value)


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ConfigError("YAML keys must be unique strings")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def reject_yaml_secrets(value) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in {"password", "pgpassword", "token", "secret", "private_key"}:
                raise ConfigError("Secrets must not be stored in roots YAML")
            reject_yaml_secrets(child)
    elif isinstance(value, list):
        for child in value:
            reject_yaml_secrets(child)


def load_config(path: Path, *, environ: Mapping[str, str] | None = None) -> RuntimeConfig:
    env = os.environ if environ is None else environ
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueLoader)
        reject_yaml_secrets(raw)
        if raw["version"] != 1:
            raise ConfigError("Unsupported roots version")
        source = raw["roots"]["usedata"]
        target = {key: raw["target"][key] for key in ("instance", "host", "port", "database", "user")}
        for key in ("host", "port", "database", "user"):
            if "PG" + key.upper() in env:
                target[key] = env["PG" + key.upper()]
        if env.get("PGPASSWORD") and env.get("PGPASSWORD_FILE"):
            raise ConfigError("Choose one runtime password source")
        target["password"] = env.get("PGPASSWORD")
        target["password_file"] = env.get("PGPASSWORD_FILE")
        snapshot = raw["deployment"]["source_snapshots"]
        return RuntimeConfig(
            source=SourceRoot(**{key: source[key] for key in ("path", "host", "role")}),
            target=TargetConfig(**target),
            snapshot_root=env.get("XIANGRUGU_SNAPSHOT_ROOT", snapshot["container_root"]),
            evidence_root=env.get("XIANGRUGU_EVIDENCE_ROOT", snapshot["container_evidence_root"]),
        )
    except ConfigError:
        raise
    except (yaml.YAMLError, ValidationError, KeyError, TypeError, OSError) as error:
        # Do not include YAML fragments, secret values or Pydantic input payloads.
        raise ConfigError("Invalid runtime configuration") from None

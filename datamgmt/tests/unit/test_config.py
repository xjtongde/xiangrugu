from pathlib import Path

import pytest

from xiangrugu_datamgmt.config import ConfigError, load_config


ROOTS = Path(__file__).parents[2] / "config" / "roots.yaml"


def test_repository_config_defaults():
    config = load_config(ROOTS, environ={})
    assert str(config.snapshot_root) == "/data/imports/usedata"
    assert config.source.path == Path("/mnt/wd61workmetadata/usedata")
    assert config.target.database == "xiangrugu"
    assert config.target.port == 5433


def test_environment_overrides_and_password_redaction():
    config = load_config(ROOTS, environ={"PGHOST": "db.example", "PGPORT": "6543", "PGPASSWORD": "synthetic-password", "XIANGRUGU_SNAPSHOT_ROOT": "/test/snapshots"})
    assert config.target.host == "db.example"
    assert config.target.port == 6543
    assert config.snapshot_root == Path("/test/snapshots")
    assert "synthetic-password" not in repr(config)
    assert "synthetic-password" not in config.model_dump_json()


@pytest.mark.parametrize("environment", [{"PGDATABASE": "cbdb"}, {"PGPORT": "5432"}, {"PGPASSWORD": "x", "PGPASSWORD_FILE": "/secret"}, {"XIANGRUGU_SNAPSHOT_ROOT": "relative"}])
def test_invalid_environment_is_rejected(environment):
    with pytest.raises(ConfigError):
        load_config(ROOTS, environ=environment)


@pytest.mark.parametrize("tail", ["password: synthetic-secret\n", "version: 999\n"])
def test_yaml_secrets_and_duplicate_keys_are_rejected(tmp_path, tail):
    bad = tmp_path / "roots.yaml"
    bad.write_text(ROOTS.read_text(encoding="utf-8") + tail, encoding="utf-8")
    with pytest.raises(ConfigError) as error:
        load_config(bad, environ={})
    assert "synthetic-secret" not in str(error.value)

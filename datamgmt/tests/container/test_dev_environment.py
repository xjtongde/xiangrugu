"""Contract for the persistent development environment on host 32."""

from __future__ import annotations

from pathlib import Path

import yaml


PROJECT_ROOT = Path("/app")


def test_compose_declares_a_real_isolated_dev_process() -> None:
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    dev = compose["services"]["dev"]

    assert dev["image"] == "xiangrugu:dev"
    assert dev["container_name"] == "xiangrugu-dev"
    assert dev["working_dir"] == "/workspace"
    assert dev["restart"] == "unless-stopped"
    assert dev["network_mode"] == "none"
    assert dev["read_only"] is True
    assert dev["command"][:3] == ["python", "-m", "xiangrugu_datamgmt.devwatch"]
    assert "sleep" not in " ".join(dev["command"])
    assert "tail" not in " ".join(dev["command"])


def test_dev_mounts_only_controlled_source_and_non_source_data() -> None:
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    volumes = compose["services"]["dev"]["volumes"]
    by_target = {volume["target"]: volume for volume in volumes}

    assert by_target["/workspace"] == {
        "type": "bind",
        "source": "/opt/mydocker/xiangrugu/deploy",
        "target": "/workspace",
        "read_only": True,
    }
    assert by_target["/data/persistent"]["source"] == "/opt/mydocker/xiangrugu/data/persistent"
    assert by_target["/data/var"]["source"] == "/opt/mydocker/xiangrugu/data/var"
    assert "/data/imports" not in by_target


def test_sync_script_excludes_repository_and_sensitive_runtime_state() -> None:
    script = (PROJECT_ROOT / "scripts" / "sync-dev.ps1").read_text(encoding="utf-8")

    for excluded in (".git", ".env", ".secrets", "data", "usedata"):
        assert excluded in script
    assert "git ls-files" in script

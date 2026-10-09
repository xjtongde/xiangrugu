"""Runtime-image and Compose isolation contract for Task 1."""

from __future__ import annotations

import os
from pathlib import Path

import yaml


PROJECT_ROOT = Path("/app")


def test_image_contains_offline_crs_dependency_and_bundled_catalog():
    """Dropping the locked parser/catalog or enabling PROJ network fails."""
    from pyproj import CRS, network
    assert network.is_network_enabled() is False
    assert CRS.from_epsg(4326).is_geographic


def test_image_contains_the_installed_project_package() -> None:
    """Removing the packaged application from the image must make this fail."""
    assert (PROJECT_ROOT / "datamgmt" / "src" / "xiangrugu_datamgmt").is_dir()


def test_image_process_is_not_root() -> None:
    """Changing Dockerfile USER back to root must make this test fail."""
    assert os.geteuid() != 0


def test_compose_keeps_source_mount_confined_to_development() -> None:
    """Only the development service may read the controlled source mirror."""
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    allowed_bind_sources = {
        "/opt/mydocker/xiangrugu/data/persistent",
        "/opt/mydocker/xiangrugu/data/var",
        "/opt/mydocker/xiangrugu/data/imports",
        "/opt/mydocker/xiangrugu/deploy",
    }

    for service_name, service in services.items():
        for volume in service.get("volumes", []):
            assert isinstance(volume, dict), "Compose volumes must use the auditable long syntax"
            assert volume.get("source") in allowed_bind_sources
            assert not str(volume.get("target", "")).startswith("/app")
            if volume.get("source") == "/opt/mydocker/xiangrugu/deploy":
                assert service_name == "dev"
                assert volume.get("target") == "/workspace"
                assert volume.get("read_only") is True

    assert services["test-db"].get("volumes", []) == []


def test_project_snapshot_volume_is_readonly_without_dynamic_source_propagation():
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    imports = next(volume for volume in compose["services"]["app"]["volumes"] if volume["target"] == "/data/imports")
    assert imports["read_only"] is True
    assert "bind" not in imports

"""Structural guards for the layering rules in CLAUDE.md.

These run in CI so a boundary violation fails the build rather than review.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "portfolio"

EXPECTED_PACKAGES = (
    "core",
    "interfaces",
    "features",
    "features/providers",
    "features/importers",
    "features/reports",
    "features/roundup",
    "api",
)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def _python_files(package: str) -> list[Path]:
    return sorted((SRC / package).rglob("*.py"))


def test_expected_packages_exist() -> None:
    for package in EXPECTED_PACKAGES:
        assert (SRC / package / "__init__.py").is_file(), f"missing package: {package}"


def test_core_does_not_import_features() -> None:
    for path in _python_files("core"):
        offenders = {m for m in _imported_modules(path) if m.startswith("portfolio.features")}
        assert not offenders, f"{path} imports from features: {sorted(offenders)}"


def test_features_do_not_import_core_internals() -> None:
    """Features reach core capabilities through AppContext or an interface, never directly."""
    for path in _python_files("features"):
        offenders = {m for m in _imported_modules(path) if m.startswith("portfolio.core.")}
        assert not offenders, f"{path} imports core internals: {sorted(offenders)}"


def test_interfaces_hold_no_implementation_imports() -> None:
    for path in _python_files("interfaces"):
        offenders = {
            m
            for m in _imported_modules(path)
            if m.startswith(("portfolio.features", "portfolio.core", "portfolio.api"))
        }
        assert not offenders, f"{path} must stay implementation-free: {sorted(offenders)}"


def test_environment_is_read_only_by_settings() -> None:
    """Config travels through `Settings`/`AppContext`; `os.environ` reads are banned in src/."""
    banned = {"environ", "getenv", "putenv", "unsetenv"}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr in banned
                and isinstance(node.value, ast.Name)
                and node.value.id == "os"
            ):
                raise AssertionError(f"{path}:{node.lineno} reads os.{node.attr} directly")
            if isinstance(node, ast.ImportFrom) and node.module == "os":
                offenders = {alias.name for alias in node.names} & banned
                assert not offenders, f"{path}:{node.lineno} imports {sorted(offenders)} from os"

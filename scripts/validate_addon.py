#!/usr/bin/env python3
"""Validate ``rayforge-addon.yaml`` before committing or tagging.

Checks the manifest schema, that the declared backend/frontend modules
point at real files, that asset paths exist, and that the dependency-free
core imports cleanly. Run from the repository root::

    python3 scripts/validate_addon.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "rayforge-addon.yaml"

REQUIRED = {
    "name": str,
    "display_name": str,
    "description": str,
    "api_version": int,
    "author": dict,
    "provides": dict,
}
REQUIRED_AUTHOR = {"name": str, "email": str}
PROVIDES_KINDS = {"backend", "frontend"}


class ValidationError(Exception):
    """Raised when the manifest or the repository is inconsistent."""


def load_manifest() -> dict:
    try:
        import yaml
    except ImportError as error:  # pragma: no cover
        raise ValidationError(
            "PyYAML is required: pip install -r requirements-dev.txt"
        ) from error
    if not MANIFEST.exists():
        raise ValidationError(f"{MANIFEST.name} not found.")
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValidationError(f"{MANIFEST.name} must contain a mapping.")
    return data


def check_schema(data: dict) -> None:
    for key, expected in REQUIRED.items():
        if key not in data:
            raise ValidationError(f"missing required key: '{key}'")
        if not isinstance(data[key], expected):
            raise ValidationError(
                f"'{key}' must be {expected.__name__}, "
                f"got {type(data[key]).__name__}"
            )
    author = data["author"]
    for key, expected in REQUIRED_AUTHOR.items():
        if key not in author or not isinstance(author[key], expected):
            raise ValidationError(f"author.{key} is missing or not a string")
        if not str(author[key]).strip():
            raise ValidationError(f"author.{key} must not be empty")
    if data["api_version"] < 1:
        raise ValidationError("api_version must be a positive integer")
    if not data["name"].isidentifier():
        raise ValidationError(
            f"name '{data['name']}' is not a valid Python module name"
        )
    provides = data["provides"]
    if not provides:
        raise ValidationError("'provides' must not be empty")
    for key, value in provides.items():
        if key in PROVIDES_KINDS and not isinstance(value, str):
            raise ValidationError(f"provides.{key} must be a string")
        if key == "assets":
            if not isinstance(value, list):
                raise ValidationError("provides.assets must be a list")


def check_modules(data: dict) -> None:
    package = data["name"]
    if not (ROOT / package).is_dir():
        raise ValidationError(
            f"package directory '{package}/' does not exist; "
            "the name must match the directory"
        )

    provides = data["provides"]
    for kind in PROVIDES_KINDS:
        dotted = provides.get(kind)
        if not dotted:
            continue
        parts = dotted.split(".")
        module_file = ROOT.joinpath(*parts).with_suffix(".py")
        package_init = ROOT.joinpath(*parts, "__init__.py")
        if not module_file.exists() and not package_init.exists():
            raise ValidationError(
                f"provides.{kind} = '{dotted}' does not resolve to a file"
            )
        if not dotted.startswith(f"{package}."):
            raise ValidationError(
                f"provides.{kind} must live inside '{package}/'"
            )

    for asset in provides.get("assets", []):
        path = ROOT / str(asset.get("path", "")).lstrip("./")
        if not path.exists():
            raise ValidationError(f"asset path '{asset.get('path')}' is missing")


def check_core_is_dependency_free() -> None:
    """The core package must not import Rayforge, GTK or other extras."""
    forbidden = ("gi", "rayforge", "raygeo", "numpy", "pyvips", "cairo")
    for source in sorted((ROOT / "puzzle_maker" / "core").glob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
            else:
                continue
            for name in names:
                if name in forbidden:
                    raise ValidationError(
                        f"{source.relative_to(ROOT)} imports '{name}'; "
                        "the core must stay dependency-free"
                    )


def check_core_imports() -> None:
    sys.path.insert(0, str(ROOT))
    from puzzle_maker.core import PuzzleParams, puzzle_to_svg

    svg = puzzle_to_svg(PuzzleParams(columns=2, rows=2, seed=1))
    if "<svg" not in svg or svg.count("<path") != 1:
        raise ValidationError("the generator produced an unexpected SVG")


def main() -> int:
    try:
        data = load_manifest()
        check_schema(data)
        check_modules(data)
        check_core_is_dependency_free()
        check_core_imports()
    except ValidationError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"OK: {data['display_name']} ({data['name']}), "
          f"api_version {data['api_version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

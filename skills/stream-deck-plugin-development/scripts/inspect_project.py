#!/usr/bin/env python3
"""Inspect a Stream Deck plugin project and emit deterministic JSON evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
from typing import Any


EXCLUDED_PARTS = {
    ".git",
    ".next",
    ".turbo",
    "__pycache__",
    "coverage",
    "dist",
    "node_modules",
}
LOCKFILE_NAMES = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "bun.lockb")
SOURCE_SUFFIXES = {".cjs", ".js", ".jsx", ".mjs", ".ts", ".tsx"}
CONTROLLER_ORDER = {"Keypad": 0, "Encoder": 1, "Neo": 2}
NEO_MINIMUM = "7.6"


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read JSON object {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(root: pathlib.Path, path: pathlib.Path) -> str:
    return path.relative_to(root).as_posix()


def has_symlink_component(root: pathlib.Path, path: pathlib.Path) -> bool:
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def discover_manifest(project: pathlib.Path, selected: pathlib.Path | None) -> pathlib.Path:
    if selected is not None:
        candidate = selected.expanduser()
        if not candidate.is_absolute():
            candidate = project / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(project)
        except ValueError as error:
            raise ValueError("--manifest must resolve inside the project") from error
        if not candidate.is_file():
            raise ValueError(f"Manifest does not exist: {candidate}")
        if has_symlink_component(project, candidate):
            raise ValueError("--manifest must not traverse a symlink")
        return candidate

    manifests = []
    for path in project.rglob("manifest.json"):
        relative = path.relative_to(project)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.parent.name.endswith(".sdPlugin") and not has_symlink_component(project, path):
            manifests.append(path.resolve())
    manifests.sort(key=lambda path: relative_path(project, path))
    if not manifests:
        raise ValueError("No *.sdPlugin/manifest.json found in the project")
    if len(manifests) > 1:
        choices = ", ".join(relative_path(project, path) for path in manifests)
        raise ValueError(f"Found multiple manifests; pass --manifest with one of: {choices}")
    return manifests[0]


def find_package(project: pathlib.Path, manifest: pathlib.Path) -> pathlib.Path | None:
    current = manifest.parent
    while True:
        package = current / "package.json"
        if package.is_file() and not package.is_symlink():
            return package
        if current == project:
            return None
        if project not in current.parents:
            return None
        current = current.parent


def dependency_range(package: dict[str, Any]) -> str | None:
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        values = package.get(section)
        if isinstance(values, dict) and isinstance(values.get("@elgato/streamdeck"), str):
            return values["@elgato/streamdeck"]
    return None


def locked_sdk_versions(lockfile: pathlib.Path) -> list[str]:
    if lockfile.name != "package-lock.json":
        return []
    lock = load_json(lockfile)
    versions: set[str] = set()
    packages = lock.get("packages")
    if isinstance(packages, dict):
        entry = packages.get("node_modules/@elgato/streamdeck")
        if isinstance(entry, dict) and isinstance(entry.get("version"), str):
            versions.add(entry["version"])
    dependencies = lock.get("dependencies")
    if isinstance(dependencies, dict):
        entry = dependencies.get("@elgato/streamdeck")
        if isinstance(entry, dict) and isinstance(entry.get("version"), str):
            versions.add(entry["version"])
    return sorted(versions)


def declared_path(
    project: pathlib.Path,
    bundle: pathlib.Path,
    value: Any,
) -> tuple[dict[str, Any] | None, bool]:
    if not isinstance(value, str) or not value.strip():
        return None, False
    raw = value.strip()
    path = pathlib.Path(raw)
    if path.is_absolute():
        return {"path": raw, "exists": False}, True
    resolved = (bundle / path).resolve()
    try:
        resolved.relative_to(bundle)
        relative = relative_path(project, resolved)
    except ValueError:
        return {"path": raw, "exists": False}, True
    return {"path": relative, "exists": resolved.is_file()}, False


def encoder_layout(
    project: pathlib.Path,
    bundle: pathlib.Path,
    action: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    encoder = action.get("Encoder")
    declared = encoder.get("layout") if isinstance(encoder, dict) else None
    if not isinstance(declared, str) or not declared.strip():
        return {"kind": "none", "declared": None, "path": None, "exists": None}, False
    declared = declared.strip()
    if declared.startswith("$"):
        return {"kind": "built_in", "declared": declared, "path": None, "exists": None}, False
    status, escaped = declared_path(project, bundle, declared)
    assert status is not None
    return {"kind": "relative_path", "declared": declared, **status}, escaped


def version_tuple(value: Any) -> tuple[int, ...]:
    if not isinstance(value, str):
        return ()
    match = re.match(r"^\s*(\d+(?:\.\d+)*)", value)
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def source_uuid_references(project: pathlib.Path, uuid: str) -> list[str]:
    if not uuid:
        return []
    matches = []
    for path in project.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        relative = path.relative_to(project)
        if any(part in EXCLUDED_PARTS or part.endswith(".sdPlugin") for part in relative.parts):
            continue
        if has_symlink_component(project, path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if uuid in text:
            matches.append(relative.as_posix())
    return sorted(matches)


def inspect_project(
    project_value: pathlib.Path,
    manifest_value: pathlib.Path | None,
) -> dict[str, Any]:
    project = project_value.expanduser().resolve()
    if not project.is_dir():
        raise ValueError(f"Project directory does not exist: {project}")
    manifest_path = discover_manifest(project, manifest_value)
    manifest = load_json(manifest_path)
    bundle = manifest_path.parent
    package_path = find_package(project, manifest_path)
    package = load_json(package_path) if package_path else {}
    package_root = package_path.parent if package_path else project
    lockfiles = [package_root / name for name in LOCKFILE_NAMES if (package_root / name).is_file()]
    locked_versions = sorted({version for path in lockfiles for version in locked_sdk_versions(path)})
    installed_package = package_root / "node_modules" / "@elgato" / "streamdeck" / "package.json"
    installed = load_json(installed_package) if installed_package.is_file() else {}
    findings: list[dict[str, Any]] = []

    code_path, code_escaped = declared_path(project, bundle, manifest.get("CodePath"))
    if code_path is None:
        code_path = {"path": None, "exists": False}
        findings.append({"code": "missing-code-path", "state": "CONFLICT", "subject": "manifest.CodePath"})
    elif code_escaped:
        findings.append({"code": "outside-bundle-path", "state": "CONFLICT", "subject": "manifest.CodePath"})
    elif not code_path["exists"]:
        findings.append({"code": "missing-code-file", "state": "CONFLICT", "subject": code_path["path"]})

    plugin_uuid = str(manifest.get("UUID", ""))
    root_pi = manifest.get("PropertyInspectorPath")
    actions = []
    controller_surfaces: set[str] = set()
    for index, raw_action in enumerate(manifest.get("Actions", [])):
        if not isinstance(raw_action, dict):
            continue
        action_uuid = str(raw_action.get("UUID", ""))
        raw_controllers = raw_action.get("Controllers") or ["Keypad"]
        controllers = [str(value) for value in raw_controllers if isinstance(value, str)]
        controllers = sorted(dict.fromkeys(controllers), key=lambda value: (CONTROLLER_ORDER.get(value, 99), value))
        controller_surfaces.update(controllers)
        pi_value = raw_action.get("PropertyInspectorPath", root_pi)
        pi_status, pi_escaped = declared_path(project, bundle, pi_value)
        declared_by = "action" if "PropertyInspectorPath" in raw_action else "root" if root_pi else "none"
        property_inspector = {
            "declared_by": declared_by,
            "path": pi_status["path"] if pi_status else None,
            "exists": pi_status["exists"] if pi_status else None,
        }
        if pi_escaped:
            findings.append({"code": "outside-bundle-path", "state": "CONFLICT", "subject": f"action[{index}].PropertyInspectorPath"})
        elif pi_status and not pi_status["exists"]:
            findings.append({"code": "missing-property-inspector", "state": "CONFLICT", "subject": pi_status["path"]})
        layout, layout_escaped = encoder_layout(project, bundle, raw_action)
        if layout_escaped:
            findings.append({"code": "outside-bundle-path", "state": "CONFLICT", "subject": f"action[{index}].Encoder.layout"})
        elif layout["kind"] == "relative_path" and not layout["exists"]:
            findings.append({"code": "missing-encoder-layout", "state": "CONFLICT", "subject": layout["path"]})
        uuid_state = "MATCH" if plugin_uuid and action_uuid.startswith(plugin_uuid + ".") else "MISMATCH"
        if uuid_state == "MISMATCH":
            findings.append({"code": "action-uuid-prefix", "state": "CONFLICT", "subject": action_uuid})
        actions.append(
            {
                "name": str(raw_action.get("Name", "")),
                "uuid": action_uuid,
                "uuid_prefix_state": uuid_state,
                "controllers": controllers,
                "visible_in_actions_list": raw_action.get("VisibleInActionsList", True) is not False,
                "property_inspector": property_inspector,
                "encoder_layout": layout,
                "lexical_source_uuid_references": source_uuid_references(project, action_uuid),
            }
        )

    software = manifest.get("Software") if isinstance(manifest.get("Software"), dict) else {}
    nodejs = manifest.get("Nodejs") if isinstance(manifest.get("Nodejs"), dict) else {}
    minimum_host = str(software.get("MinimumVersion", "")) or None
    if "Neo" in controller_surfaces and version_tuple(minimum_host) < version_tuple(NEO_MINIMUM):
        findings.append(
            {
                "code": "neo-host-floor",
                "state": "CONFLICT",
                "subject": "Neo controller",
                "declared_minimum": minimum_host,
                "required_minimum": NEO_MINIMUM,
            }
        )
    os_values = []
    for value in manifest.get("OS", []):
        if isinstance(value, dict):
            os_values.append(
                {
                    "platform": value.get("Platform"),
                    "minimum_version": value.get("MinimumVersion"),
                }
            )
    os_values.sort(key=lambda value: str(value.get("platform", "")))
    if not package_path:
        findings.append({"code": "missing-package", "state": "UNVERIFIED", "subject": "package.json"})

    findings.sort(key=lambda item: (str(item.get("code", "")), str(item.get("subject", ""))))
    return {
        "schema_version": 1,
        "project_root": ".",
        "manifest": {
            "path": relative_path(project, manifest_path),
            "sha256": sha256_file(manifest_path),
            "plugin_uuid": plugin_uuid,
            "plugin_version": str(manifest.get("Version", "")),
            "code_path": code_path,
        },
        "package": {
            "path": relative_path(project, package_path) if package_path else None,
            "name": package.get("name"),
            "version": package.get("version"),
            "scripts": package.get("scripts") if isinstance(package.get("scripts"), dict) else {},
            "lockfiles": [
                {"path": relative_path(project, path), "sha256": sha256_file(path)}
                for path in sorted(lockfiles)
            ],
        },
        "sdk": {
            "declared_range": dependency_range(package),
            "locked_versions": locked_versions,
            "installed_version": installed.get("version") if isinstance(installed.get("version"), str) else None,
            "installed_package_path": relative_path(project, installed_package) if installed_package.is_file() else None,
        },
        "actions": actions,
        "compatibility": {
            "minimum_host": minimum_host,
            "node_version": nodejs.get("Version"),
            "sdk_version": manifest.get("SDKVersion"),
            "os": os_values,
            "controller_surfaces": sorted(controller_surfaces, key=lambda value: (CONTROLLER_ORDER.get(value, 99), value)),
            "runtime_proof": "UNVERIFIED",
            "required_runtime_proofs": [
                "Build and package the exact source under review",
                "Run the exact package on the declared minimum Stream Deck and operating systems",
                "Verify each declared controller on applicable simulated or physical hardware",
            ],
        },
        "findings": findings,
    }


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--project", default=".", help="plugin project directory")
    value.add_argument("--manifest", help="manifest path when project discovery is ambiguous")
    value.add_argument("--output", help="write the report to a new file instead of stdout")
    return value


def output_path(value: str) -> pathlib.Path:
    path = pathlib.Path(os.path.abspath(pathlib.Path(value).expanduser()))
    current = pathlib.Path(path.anchor)
    user_controlled = False
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink() and user_controlled:
            raise FileExistsError(f"Refusing symlink output path component {current}")
        if current.exists() and os.access(current, os.W_OK):
            user_controlled = True
    return path


def write_output(path: pathlib.Path, content: str) -> None:
    path = output_path(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path = output_path(str(path))
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise FileExistsError(f"Refusing to overwrite {path}") from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)


def main() -> int:
    args = parser().parse_args()
    try:
        report = inspect_project(
            pathlib.Path(args.project),
            pathlib.Path(args.manifest) if args.manifest else None,
        )
        content = render_json(report)
        if args.output:
            output = output_path(args.output)
            write_output(output, content)
            print(output)
        else:
            sys.stdout.write(content)
        return 0
    except (FileExistsError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

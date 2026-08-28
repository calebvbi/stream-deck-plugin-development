#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import re
import runpy
import subprocess
import sys
import tempfile
from collections import defaultdict


ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "stream-deck-plugin-development"
FRONTMATTER_KEYS = {"description", "license", "metadata", "name"}
ALLOWED_TOP_LEVEL = {"SKILL.md", "references", "scripts"}
ALLOWED_SCRIPTS = {
    "bundle_self_containment.py",
    "inspect_project.py",
    "qa_matrix.py",
}
PUBLIC_ROOT_FILES = {
    ".github/workflows/validate.yml",
    ".gitignore",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
    "scripts/validate_publication.py",
}
FORBIDDEN_NAMES = {".DS_Store", "Thumbs.db", "__pycache__"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}
PROJECT_MARKERS = (
    "/" + "users/",
    "/" + "volumes/",
    "extreme" + " ssd",
    "." + "codex/",
    "." + "agents/",
    "streamdeck-plugin-" + "sdk-skill",
    "com.elgato." + "openai-codex",
)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{16,}\b"),
    re.compile(r"\b[A-Fa-f0-9]{40}\b"),
    re.compile(r"\b[A-Fa-f0-9]{64}\b"),
    re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
)
PUBLIC_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{16,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
)
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ROUTE = re.compile(r"`(references/[^`]+\.md)`")
FENCE = re.compile(r"^\s*~~~|^\s*\x60\x60\x60")


def relative_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    )


def tree_hash(root: pathlib.Path) -> str:
    digest = hashlib.sha256()
    for path in relative_files(root):
        relative = path.relative_to(root).as_posix().encode()
        digest.update(relative)
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def parse_frontmatter(path: pathlib.Path) -> tuple[dict[str, str], list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}, ["SKILL.md must start with YAML frontmatter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, ["SKILL.md frontmatter is not closed"]
    values: dict[str, str] = {}
    keys: set[str] = set()
    for line in lines[1:end]:
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        keys.add(key.strip())
        values[key.strip()] = value.strip().strip('"').strip("'")
    errors = []
    unknown = sorted(keys - FRONTMATTER_KEYS)
    if unknown:
        errors.append(f"unsupported frontmatter keys: {unknown}")
    return values, errors


def markdown_without_fences(text: str) -> str:
    kept = []
    inside = False
    for line in text.splitlines():
        if FENCE.match(line):
            inside = not inside
            continue
        if not inside:
            kept.append(line)
    return "\n".join(kept)


def validate_helper_guards(errors: list[str]) -> None:
    helpers = SKILL / "scripts"
    qa_namespace = runpy.run_path(str(helpers / "qa_matrix.py"))
    unsafe_class = qa_namespace["status_class"]('PASS" onmouseover="alert(1)')
    if not re.fullmatch(r"[a-z0-9-]+", unsafe_class):
        errors.append("qa_matrix.py emits unsafe HTML class names")

    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        target = root / "target.json"
        link = root / "output.json"
        try:
            link.symlink_to(target)
        except (NotImplementedError, OSError):
            return
        for script_name in ("inspect_project.py", "qa_matrix.py"):
            namespace = runpy.run_path(str(helpers / script_name))
            try:
                namespace["output_path"](str(link))
            except FileExistsError:
                continue
            errors.append(f"{script_name} accepts a leaf-symlink output path")

        real_parent = root / "real-parent"
        real_parent.mkdir()
        linked_parent = root / "linked-parent"
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        for script_name in ("inspect_project.py", "qa_matrix.py"):
            namespace = runpy.run_path(str(helpers / script_name))
            try:
                namespace["output_path"](str(linked_parent / "output.json"))
            except FileExistsError:
                continue
            errors.append(f"{script_name} accepts a parent-symlink output path")

        plugin = root / "fixture.sdPlugin"
        plugin.mkdir()
        (plugin / "manifest.json").write_text(
            json.dumps({"PropertyInspectorPath": "pi.html", "Actions": []}),
            encoding="utf-8",
        )
        (plugin / "pi.html").write_text(
            "<iframe srcdoc='<script src=\"https://example.invalid/x.js\"></script>'></iframe>"
            "<script src=\"data:text/javascript,alert(1)\"></script>",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, str(helpers / "bundle_self_containment.py"), str(plugin)],
            check=False,
            capture_output=True,
            text=True,
        )
        try:
            report = json.loads(result.stdout)
        except json.JSONDecodeError:
            errors.append("bundle_self_containment.py did not emit JSON for unsafe inline resources")
        else:
            codes = {finding.get("code") for finding in report.get("findings", [])}
            for expected in {"INLINE_EXECUTABLE_RESOURCE", "UNSAFE_DATA_RESOURCE"}:
                if expected not in codes:
                    errors.append(
                        f"bundle_self_containment.py misses {expected.lower()}"
                    )


def validate() -> tuple[list[str], dict[str, object]]:
    errors: list[str] = []
    if not SKILL.is_dir():
        return [f"missing skill directory: {SKILL}"], {}
    if any(path.is_symlink() for path in SKILL.rglob("*")):
        errors.append("skill payload must not contain symlinks")

    repository_files = relative_files(ROOT)
    repository_names = {path.relative_to(ROOT).as_posix() for path in repository_files}
    missing_public_files = sorted(PUBLIC_ROOT_FILES - repository_names)
    if missing_public_files:
        errors.append(f"missing public repository files: {missing_public_files}")
    unexpected_public_files = sorted(
        name
        for name in repository_names
        if name not in PUBLIC_ROOT_FILES
        and not name.startswith("skills/stream-deck-plugin-development/")
    )
    if unexpected_public_files:
        errors.append(f"unexpected public repository files: {unexpected_public_files}")
    for path in ROOT.rglob("*"):
        if ".git" in path.relative_to(ROOT).parts:
            continue
        if path.is_symlink():
            errors.append(f"public repository must not contain symlinks: {path.relative_to(ROOT)}")

    public_markdown = [path for path in repository_files if path.suffix == ".md"]
    for path in repository_files:
        if path.suffix not in {"", ".md", ".py", ".yml", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for marker in PROJECT_MARKERS:
            if marker in lowered:
                errors.append(f"{path.relative_to(ROOT)} contains private marker {marker!r}")
        for pattern in PUBLIC_SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(
                    f"{path.relative_to(ROOT)} matches sensitive pattern {pattern.pattern!r}"
                )
    for path in public_markdown:
        text = path.read_text(encoding="utf-8")
        for target in LINK.findall(text):
            clean = target.split("#", 1)[0]
            if not clean or "://" in clean or clean.startswith(("mailto:", "app:")):
                continue
            resolved = (path.parent / clean).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"{path.relative_to(ROOT)} links outside the repository: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)} has missing link: {target}")

    skill_file = SKILL / "SKILL.md"
    frontmatter, frontmatter_errors = parse_frontmatter(skill_file)
    errors.extend(frontmatter_errors)
    name = frontmatter.get("name", "")
    if name != SKILL.name:
        errors.append("frontmatter name must match the skill directory")
    if len(name) > 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        errors.append("frontmatter name must use portable lowercase hyphen syntax")
    description = frontmatter.get("description", "")
    if not description:
        errors.append("frontmatter description is required")
    if len(description) > 1024:
        errors.append("frontmatter description exceeds 1024 characters")
    if len(skill_file.read_text(encoding="utf-8").splitlines()) > 500:
        errors.append("SKILL.md exceeds 500 lines")

    top_level = {path.name for path in SKILL.iterdir()}
    unexpected = sorted(top_level - ALLOWED_TOP_LEVEL)
    if unexpected:
        errors.append(f"unexpected payload entries: {unexpected}")

    for path in SKILL.rglob("*"):
        relative = path.relative_to(SKILL)
        if any(part in FORBIDDEN_NAMES for part in relative.parts):
            errors.append(f"generated or platform file is not allowed: {relative}")
        if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"generated Python file is not allowed: {relative}")
        if not path.is_file():
            continue
        if relative == pathlib.Path("SKILL.md"):
            continue
        if relative.parent == pathlib.Path("references") and path.suffix == ".md":
            continue
        if relative.parent == pathlib.Path("scripts") and relative.name in ALLOWED_SCRIPTS:
            continue
        errors.append(f"unexpected payload file: {relative}")

    markdown_files = sorted(SKILL.rglob("*.md"))
    text_files = [path for path in relative_files(SKILL) if path.suffix in {".md", ".py"}]
    routed_references = {
        (SKILL / target).resolve()
        for target in ROUTE.findall(skill_file.read_text(encoding="utf-8"))
    }
    for route in sorted(routed_references):
        if not route.exists():
            errors.append(f"SKILL.md routes to missing reference: {route.relative_to(SKILL.resolve())}")
    paragraphs: dict[str, list[str]] = defaultdict(list)
    for path in text_files:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for marker in PROJECT_MARKERS:
            if marker in lowered:
                errors.append(f"{path.relative_to(SKILL)} contains private marker {marker!r}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"{path.relative_to(SKILL)} matches sensitive pattern {pattern.pattern!r}")
        if path.suffix != ".md":
            continue
        for target in LINK.findall(text):
            clean = target.split("#", 1)[0]
            if not clean or "://" in clean or clean.startswith(("mailto:", "app:")):
                continue
            resolved = (path.parent / clean).resolve()
            try:
                resolved.relative_to(SKILL.resolve())
            except ValueError:
                errors.append(f"{path.relative_to(SKILL)} links outside the skill: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{path.relative_to(SKILL)} has missing link: {target}")
            if path == skill_file and resolved.parent == (SKILL / "references").resolve():
                routed_references.add(resolved)
        for paragraph in re.split(r"\n\s*\n", markdown_without_fences(text)):
            normalized = re.sub(r"\s+", " ", paragraph.strip())
            if len(normalized) >= 120 and not normalized.startswith("|"):
                paragraphs[normalized].append(str(path.relative_to(SKILL)))

    for reference in sorted((SKILL / "references").glob("*.md")):
        if reference.resolve() not in routed_references:
            errors.append(f"reference is not routed directly from SKILL.md: {reference.name}")
    for paragraph, paths in paragraphs.items():
        if len(set(paths)) > 1:
            errors.append(f"duplicate paragraph in {sorted(set(paths))}: {paragraph[:120]}")

    for script_name in sorted(ALLOWED_SCRIPTS):
        helper = SKILL / "scripts" / script_name
        if not helper.is_file():
            errors.append(f"missing scripts/{script_name}")
            continue
        if not os.access(helper, os.X_OK):
            errors.append(f"scripts/{script_name} must be executable")
        try:
            ast.parse(helper.read_text(encoding="utf-8"))
        except SyntaxError as error:
            errors.append(f"scripts/{script_name} has invalid syntax: {error}")
        result = subprocess.run(
            [sys.executable, str(helper), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            errors.append(f"scripts/{script_name} --help failed: {result.stderr.strip()}")

    validate_helper_guards(errors)

    files = relative_files(SKILL)
    details: dict[str, object] = {
        "skill": SKILL.name,
        "files": len(files),
        "markdown_files": len(markdown_files),
        "repository_files": len(repository_files),
        "tree_sha256": tree_hash(SKILL),
    }
    return errors, details


def main() -> int:
    errors, details = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(json.dumps({"status": "fail", "errors": len(errors), **details}, sort_keys=True))
        return 1
    print(json.dumps({"status": "pass", **details}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

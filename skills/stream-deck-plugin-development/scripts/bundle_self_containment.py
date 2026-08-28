#!/usr/bin/env python3
"""Verify that a Stream Deck bundle's static Property Inspector resources are local."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import stat
import sys
import urllib.parse
from collections import deque
from dataclasses import dataclass
from html.parser import HTMLParser


MAX_MANIFEST_BYTES = 1024 * 1024
MAX_TEXT_BYTES = 8 * 1024 * 1024
MAX_TOTAL_TEXT_BYTES = 32 * 1024 * 1024
MAX_RESOURCES = 512
_READ_BITS = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
_DRIVE_PATH = re.compile(r"^[A-Za-z]:[/\\]")
_IDENTIFIER_START = re.compile(r"[A-Za-z_$]")
_IDENTIFIER_PART = re.compile(r"[A-Za-z0-9_$]")


@dataclass(frozen=True)
class BundleFinding:
    code: str
    source: pathlib.PurePosixPath
    line: int
    column: int
    resource_kind: str
    reference: str

    @property
    def sort_key(self) -> tuple[str, int, int, str, str, str]:
        return (
            self.source.as_posix(),
            self.line,
            self.column,
            self.resource_kind,
            self.code,
            self.reference,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "source": self.source.as_posix(),
            "line": self.line,
            "column": self.column,
            "resource_kind": self.resource_kind,
            "reference": self.reference,
        }


@dataclass(frozen=True)
class BundleReport:
    plugin: pathlib.PurePosixPath
    entrypoints: tuple[pathlib.PurePosixPath, ...]
    inspected_resources: tuple[pathlib.PurePosixPath, ...]
    findings: tuple[BundleFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict[str, object]:
        return {
            "plugin": self.plugin.as_posix(),
            "entrypoints": [path.as_posix() for path in self.entrypoints],
            "inspected_resources": [path.as_posix() for path in self.inspected_resources],
            "findings": [finding.to_dict() for finding in self.findings],
            "passed": self.passed,
        }


@dataclass(frozen=True)
class _Reference:
    source: pathlib.PurePosixPath
    reference: str
    line: int
    column: int
    resource_kind: str


@dataclass(frozen=True)
class _PendingResource:
    relative: pathlib.PurePosixPath
    path: pathlib.Path
    parser: str | None


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str
    index: int


class _HTMLResources(HTMLParser):
    def __init__(self, source: pathlib.PurePosixPath) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.references: list[_Reference] = []
        self.inline_css: list[tuple[str, int, int]] = []
        self.inline_javascript: list[tuple[str, int, int]] = []
        self._capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        values = {key.lower(): value for key, value in attrs if value is not None}
        line, column = self.getpos()
        column += 1
        if style := values.get("style"):
            self.inline_css.append((style, line, column))
        if name == "base" and "href" in values:
            self._add(values["href"], line, column, "html-base")
            return
        if name == "script":
            if source := values.get("src"):
                self._add(source, line, column, "script")
            else:
                self._capture = "javascript"
            return
        if name == "style":
            self._capture = "css"
            return
        if name == "iframe" and "srcdoc" in values:
            self._add("<srcdoc>", line, column, "inline-frame")
        attributes = {
            "link": (("href", "stylesheet"),),
            "img": (("src", "image"), ("srcset", "srcset")),
            "source": (("src", "media"), ("srcset", "srcset")),
            "video": (("src", "media"), ("poster", "image")),
            "audio": (("src", "media"),),
            "track": (("src", "media"),),
            "iframe": (("src", "frame"),),
            "embed": (("src", "frame"),),
            "object": (("data", "frame"),),
            "input": (("src", "image"),),
            "image": (("href", "image"), ("xlink:href", "image")),
            "use": (("href", "image"), ("xlink:href", "image")),
        }
        for attribute, kind in attributes.get(name, ()):
            value = values.get(attribute)
            if not value:
                continue
            if kind == "srcset":
                for candidate in _srcset_urls(value):
                    self._add(candidate, line, column, "image")
            else:
                self._add(value, line, column, kind)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self._capture = None

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"}:
            self._capture = None

    def handle_data(self, data: str) -> None:
        if not self._capture or not data:
            return
        line, column = self.getpos()
        target = self.inline_css if self._capture == "css" else self.inline_javascript
        target.append((data, line, column + 1))

    def _add(self, reference: str, line: int, column: int, kind: str) -> None:
        self.references.append(
            _Reference(self.source, reference, line, column, kind)
        )


class _Inspector:
    def __init__(self, plugin_root: pathlib.Path) -> None:
        self.root = plugin_root
        self.plugin = pathlib.PurePosixPath(plugin_root.name or "plugin.sdPlugin")
        self.entrypoints: set[pathlib.PurePosixPath] = set()
        self.inspected: set[pathlib.PurePosixPath] = set()
        self.findings: list[BundleFinding] = []
        self.pending: deque[_PendingResource] = deque()
        self.scheduled: set[pathlib.PurePosixPath] = set()
        self.total_text_bytes = 0
        self.resource_limit_reported = False

    def inspect(self) -> BundleReport:
        manifest = self._load_manifest()
        if manifest is not None:
            self._load_entrypoints(manifest)
            self._walk()
        return BundleReport(
            plugin=self.plugin,
            entrypoints=tuple(sorted(self.entrypoints, key=lambda path: path.as_posix())),
            inspected_resources=tuple(
                sorted(self.inspected, key=lambda path: path.as_posix())
            ),
            findings=tuple(sorted(set(self.findings), key=lambda finding: finding.sort_key)),
        )

    def _load_manifest(self) -> dict[str, object] | None:
        source = pathlib.PurePosixPath("manifest.json")
        if self.root.is_symlink() or not self.root.is_dir():
            self._add("MANIFEST_INVALID", source, 1, 1, "manifest", "manifest.json")
            return None
        path = self.root / "manifest.json"
        if path.is_symlink() or not path.is_file():
            self._add("MANIFEST_INVALID", source, 1, 1, "manifest", "manifest.json")
            return None
        try:
            mode = path.stat().st_mode
            if mode & _READ_BITS == 0:
                raise PermissionError
            raw = path.read_bytes()
            if len(raw) > MAX_MANIFEST_BYTES:
                raise ValueError
            value = json.loads(raw.decode("utf-8-sig"))
        except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
            self._add("MANIFEST_INVALID", source, 1, 1, "manifest", "manifest.json")
            return None
        if not isinstance(value, dict):
            self._add("MANIFEST_INVALID", source, 1, 1, "manifest", "manifest.json")
            return None
        return value

    def _load_entrypoints(self, manifest: dict[str, object]) -> None:
        values: list[object] = []
        if "PropertyInspectorPath" in manifest:
            values.append(manifest["PropertyInspectorPath"])
        actions = manifest.get("Actions", [])
        if not isinstance(actions, list):
            self._add(
                "MANIFEST_INVALID",
                pathlib.PurePosixPath("manifest.json"),
                1,
                1,
                "manifest",
                "Actions",
            )
            return
        for action in actions:
            if isinstance(action, dict) and "PropertyInspectorPath" in action:
                values.append(action["PropertyInspectorPath"])
        for value in values:
            if not isinstance(value, str) or not value.strip():
                self._add(
                    "INVALID_PROPERTY_INSPECTOR_PATH",
                    pathlib.PurePosixPath("manifest.json"),
                    1,
                    1,
                    "property-inspector",
                    "<invalid-entrypoint>",
                )
                continue
            reference = _Reference(
                pathlib.PurePosixPath("manifest.json"), value, 1, 1, "property-inspector"
            )
            resolved = self._resolve(reference)
            if resolved is not None:
                relative, path = resolved
                self._schedule(relative, path, "html", reference)

    def _walk(self) -> None:
        while self.pending:
            resource = self.pending.popleft()
            self.inspected.add(resource.relative)
            if resource.parser is None:
                continue
            text = self._read_text(resource)
            if text is None:
                continue
            if resource.parser == "html":
                parser = _HTMLResources(resource.relative)
                parser.feed(text)
                parser.close()
                for reference in parser.references:
                    self._follow(reference)
                for value, line, column in parser.inline_css:
                    self._consume_scan(_scan_css(value, resource.relative, line, column))
                for value, line, column in parser.inline_javascript:
                    self._consume_scan(
                        _scan_javascript(value, resource.relative, line, column)
                    )
            elif resource.parser == "css":
                self._consume_scan(_scan_css(text, resource.relative))
            else:
                self._consume_scan(_scan_javascript(text, resource.relative))

    def _consume_scan(
        self, result: tuple[list[_Reference], list[BundleFinding]]
    ) -> None:
        references, findings = result
        self.findings.extend(findings)
        for reference in references:
            self._follow(reference)

    def _follow(self, reference: _Reference) -> None:
        resolved = self._resolve(reference)
        if resolved is None:
            return
        relative, path = resolved
        parser = _parser_for(reference.resource_kind, relative)
        self._schedule(relative, path, parser, reference)

    def _schedule(
        self,
        relative: pathlib.PurePosixPath,
        path: pathlib.Path,
        parser: str | None,
        reference: _Reference,
    ) -> None:
        if relative in self.scheduled:
            return
        if len(self.scheduled) >= MAX_RESOURCES:
            if not self.resource_limit_reported:
                self.resource_limit_reported = True
                self._add(
                    "RESOURCE_LIMIT_EXCEEDED",
                    reference.source,
                    reference.line,
                    reference.column,
                    reference.resource_kind,
                    _safe_reference(reference.reference, "RESOURCE_LIMIT_EXCEEDED"),
                )
            return
        self.scheduled.add(relative)
        self.pending.append(_PendingResource(relative, path, parser))

    def _read_text(self, resource: _PendingResource) -> str | None:
        try:
            raw = resource.path.read_bytes()
        except OSError:
            self._add(
                "UNREADABLE_RESOURCE",
                resource.relative,
                1,
                1,
                resource.parser or "resource",
                resource.relative.as_posix(),
            )
            return None
        if len(raw) > MAX_TEXT_BYTES:
            self._add(
                "FILE_SIZE_LIMIT_EXCEEDED",
                resource.relative,
                1,
                1,
                resource.parser or "resource",
                resource.relative.as_posix(),
            )
            return None
        self.total_text_bytes += len(raw)
        if self.total_text_bytes > MAX_TOTAL_TEXT_BYTES:
            self._add(
                "RESOURCE_LIMIT_EXCEEDED",
                resource.relative,
                1,
                1,
                resource.parser or "resource",
                resource.relative.as_posix(),
            )
            return None
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            self._add(
                "UNREADABLE_RESOURCE",
                resource.relative,
                1,
                1,
                resource.parser or "resource",
                resource.relative.as_posix(),
            )
            return None

    def _resolve(
        self, reference: _Reference
    ) -> tuple[pathlib.PurePosixPath, pathlib.Path] | None:
        if reference.resource_kind == "inline-frame":
            self._reference_finding("INLINE_EXECUTABLE_RESOURCE", reference)
            return None
        if reference.resource_kind == "html-base":
            self._reference_finding("UNSUPPORTED_BASE_HREF", reference)
            return None
        raw = reference.reference.strip()
        if not raw:
            self._reference_finding("MALFORMED_REFERENCE", reference)
            return None
        lowered = raw.lower()
        if raw.startswith("#"):
            return None
        if lowered.startswith("data:"):
            if reference.resource_kind in {
                "property-inspector",
                "script",
                "module-import",
                "stylesheet",
                "css-import",
                "frame",
            }:
                self._reference_finding("UNSAFE_DATA_RESOURCE", reference)
            return None
        if raw.startswith("//"):
            self._reference_finding("REMOTE_RESOURCE", reference)
            return None
        if _DRIVE_PATH.match(raw):
            self._reference_finding("DRIVE_PATH", reference)
            return None
        if raw.startswith("\\\\"):
            self._reference_finding("UNC_PATH", reference)
            return None
        if "\\" in raw:
            self._reference_finding("BACKSLASH_PATH", reference)
            return None
        if raw.startswith("~") or _contains_private_variable(raw):
            self._reference_finding("PRIVATE_PATH", reference)
            return None
        try:
            parsed = urllib.parse.urlsplit(raw)
        except ValueError:
            self._reference_finding("MALFORMED_REFERENCE", reference)
            return None
        scheme = parsed.scheme.lower()
        if scheme in {"http", "https"}:
            self._reference_finding("REMOTE_RESOURCE", reference)
            return None
        if scheme:
            self._reference_finding("UNSAFE_SCHEME", reference)
            return None
        decoded = urllib.parse.unquote(parsed.path)
        if "\x00" in decoded:
            self._reference_finding("NUL_PATH", reference)
            return None
        if _DRIVE_PATH.match(decoded):
            self._reference_finding("DRIVE_PATH", reference)
            return None
        if decoded.startswith("\\\\"):
            self._reference_finding("UNC_PATH", reference)
            return None
        if "\\" in decoded:
            self._reference_finding("BACKSLASH_PATH", reference)
            return None
        if decoded.startswith("~") or _contains_private_variable(decoded):
            self._reference_finding("PRIVATE_PATH", reference)
            return None
        target = pathlib.PurePosixPath(decoded)
        if target.is_absolute():
            self._reference_finding("ABSOLUTE_PATH", reference)
            return None
        if ".." in target.parts:
            self._reference_finding("PATH_TRAVERSAL", reference)
            return None
        if not target.parts or target.as_posix() in {"", "."}:
            return None
        relative = reference.source.parent.joinpath(target)
        if reference.resource_kind == "property-inspector":
            self.entrypoints.add(relative)
        located = self._locate(relative, reference)
        if located is None:
            return None
        return relative, located

    def _locate(
        self, relative: pathlib.PurePosixPath, reference: _Reference
    ) -> pathlib.Path | None:
        current = self.root
        parts = relative.parts
        for index, part in enumerate(parts):
            try:
                entries = list(current.iterdir())
            except OSError:
                self._reference_finding("UNREADABLE_RESOURCE", reference)
                return None
            exact = next((entry for entry in entries if entry.name == part), None)
            if exact is None:
                if any(entry.name.casefold() == part.casefold() for entry in entries):
                    self._reference_finding("CASE_MISMATCH", reference)
                else:
                    self._reference_finding("MISSING_RESOURCE", reference)
                return None
            if exact.is_symlink():
                self._reference_finding("SYMLINK_RESOURCE", reference)
                return None
            try:
                mode = exact.stat().st_mode
            except OSError:
                self._reference_finding("UNREADABLE_RESOURCE", reference)
                return None
            if mode & _READ_BITS == 0:
                self._reference_finding("UNREADABLE_RESOURCE", reference)
                return None
            if index < len(parts) - 1:
                if not stat.S_ISDIR(mode):
                    self._reference_finding("MISSING_RESOURCE", reference)
                    return None
                current = exact
            elif not stat.S_ISREG(mode):
                self._reference_finding("MISSING_RESOURCE", reference)
                return None
            else:
                return exact
        self._reference_finding("MISSING_RESOURCE", reference)
        return None

    def _reference_finding(self, code: str, reference: _Reference) -> None:
        self._add(
            code,
            reference.source,
            reference.line,
            reference.column,
            reference.resource_kind,
            _safe_reference(reference.reference, code),
        )

    def _add(
        self,
        code: str,
        source: pathlib.PurePosixPath,
        line: int,
        column: int,
        resource_kind: str,
        reference: str,
    ) -> None:
        self.findings.append(
            BundleFinding(code, source, max(1, line), max(1, column), resource_kind, reference)
        )


def inspect_bundle_self_containment(plugin_root: pathlib.Path) -> BundleReport:
    return _Inspector(plugin_root).inspect()


def _parser_for(kind: str, path: pathlib.PurePosixPath) -> str | None:
    if kind in {"property-inspector", "frame"}:
        return "html"
    if kind in {"stylesheet", "css-import"}:
        return "css"
    if kind in {"script", "module-import"}:
        return "javascript"
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix == ".css":
        return "css"
    if suffix in {".js", ".mjs", ".cjs"}:
        return "javascript"
    return None


def _contains_private_variable(value: str) -> bool:
    upper = value.upper()
    return any(
        marker in upper
        for marker in ("$HOME", "${HOME}", "%USERPROFILE%", "$USERPROFILE")
    )


def _safe_reference(reference: str, code: str) -> str:
    placeholders = {
        "ABSOLUTE_PATH": "<absolute-path>",
        "DRIVE_PATH": "<drive-path>",
        "UNC_PATH": "<unc-path>",
        "BACKSLASH_PATH": "<backslash-path>",
        "PRIVATE_PATH": "<private-path>",
        "NUL_PATH": "<nul-path>",
        "UNSAFE_SCHEME": "<unsafe-scheme>",
        "UNSUPPORTED_BASE_HREF": "<base-href>",
        "INLINE_EXECUTABLE_RESOURCE": "<inline-executable-resource>",
        "UNSAFE_DATA_RESOURCE": "<data-resource>",
    }
    return placeholders.get(code, reference)


def _srcset_urls(value: str) -> tuple[str, ...]:
    urls: list[str] = []
    index = 0
    length = len(value)
    while index < length:
        while index < length and (value[index].isspace() or value[index] == ","):
            index += 1
        if index >= length:
            break
        if value[index] in {'"', "'"}:
            url, index = _quoted(value, index)
        else:
            start = index
            if value[index : index + 5].lower() == "data:":
                while index < length and not value[index].isspace():
                    index += 1
            else:
                while index < length and not value[index].isspace() and value[index] != ",":
                    index += 1
            url = value[start:index]
        if url:
            urls.append(url)
        while index < length and value[index] != ",":
            index += 1
    return tuple(urls)


def _scan_css(
    text: str,
    source: pathlib.PurePosixPath,
    base_line: int = 1,
    base_column: int = 1,
) -> tuple[list[_Reference], list[BundleFinding]]:
    references: list[_Reference] = []
    index = 0
    length = len(text)
    while index < length:
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = length if end < 0 else end + 2
            continue
        if text[index] in {'"', "'"}:
            _, index = _quoted(text, index)
            continue
        if text[index : index + 7].lower() == "@import" and _word_end(text, index + 7):
            start = index
            index = _skip_css_space(text, index + 7)
            value, index = _css_import_value(text, index)
            if value:
                line, column = _position(text, start, base_line, base_column)
                references.append(_Reference(source, value, line, column, "css-import"))
            continue
        if text[index : index + 3].lower() == "url" and _word_end(text, index + 3):
            opening = _skip_css_space(text, index + 3)
            if opening < length and text[opening] == "(":
                start = index
                value, index = _css_url_value(text, opening + 1)
                if value:
                    line, column = _position(text, start, base_line, base_column)
                    references.append(_Reference(source, value, line, column, "css-url"))
                continue
        index += 1
    return references, []


def _css_import_value(text: str, index: int) -> tuple[str, int]:
    if text[index : index + 3].lower() == "url" and _word_end(text, index + 3):
        opening = _skip_css_space(text, index + 3)
        if opening < len(text) and text[opening] == "(":
            return _css_url_value(text, opening + 1)
    if index < len(text) and text[index] in {'"', "'"}:
        return _quoted(text, index)
    start = index
    while index < len(text) and not text[index].isspace() and text[index] != ";":
        index += 1
    return text[start:index], index


def _css_url_value(text: str, index: int) -> tuple[str, int]:
    index = _skip_css_space(text, index)
    if index < len(text) and text[index] in {'"', "'"}:
        value, index = _quoted(text, index)
        index = _skip_css_space(text, index)
    else:
        start = index
        while index < len(text) and text[index] != ")":
            index += 1
        value = text[start:index].strip()
    while index < len(text) and text[index] != ")":
        index += 1
    return value, min(len(text), index + 1)


def _skip_css_space(text: str, index: int) -> int:
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            return len(text) if end < 0 else _skip_css_space(text, end + 2)
        break
    return index


def _scan_javascript(
    text: str,
    source: pathlib.PurePosixPath,
    base_line: int = 1,
    base_column: int = 1,
) -> tuple[list[_Reference], list[BundleFinding]]:
    tokens = _javascript_tokens(text)
    references: list[_Reference] = []
    findings: list[BundleFinding] = []
    for index, token in enumerate(tokens):
        if token.kind != "identifier" or token.value not in {"import", "export"}:
            continue
        if index and tokens[index - 1].value == ".":
            continue
        line, column = _position(text, token.index, base_line, base_column)
        if token.value == "import" and index + 1 < len(tokens):
            following = tokens[index + 1]
            if following.value == ".":
                continue
            if following.value == "(":
                if (
                    index + 3 < len(tokens)
                    and tokens[index + 2].kind == "string"
                    and tokens[index + 3].value == ")"
                ):
                    _module_edge(
                        references,
                        findings,
                        source,
                        tokens[index + 2].value,
                        line,
                        column,
                    )
                else:
                    findings.append(
                        BundleFinding(
                            "NONLITERAL_DYNAMIC_IMPORT",
                            source,
                            line,
                            column,
                            "module-import",
                            "<dynamic-import>",
                        )
                    )
                continue
            if following.kind == "string":
                _module_edge(
                    references, findings, source, following.value, line, column
                )
                continue
        boundary = index + 1
        while boundary < len(tokens) and tokens[boundary].value not in {";"}:
            if (
                tokens[boundary].kind == "identifier"
                and tokens[boundary].value == "from"
                and boundary + 1 < len(tokens)
                and tokens[boundary + 1].kind == "string"
            ):
                _module_edge(
                    references,
                    findings,
                    source,
                    tokens[boundary + 1].value,
                    line,
                    column,
                )
                break
            boundary += 1
    return references, findings


def _module_edge(
    references: list[_Reference],
    findings: list[BundleFinding],
    source: pathlib.PurePosixPath,
    value: str,
    line: int,
    column: int,
) -> None:
    lowered = value.lower()
    is_path = (
        value.startswith(".")
        or value.startswith("/")
        or value.startswith("\\")
        or value.startswith("~")
        or value.startswith("//")
        or lowered.startswith("data:")
        or bool(_DRIVE_PATH.match(value))
        or bool(urllib.parse.urlsplit(value).scheme)
    )
    if not is_path:
        findings.append(
            BundleFinding(
                "BARE_MODULE_SPECIFIER",
                source,
                line,
                column,
                "module-import",
                value,
            )
        )
        return
    references.append(_Reference(source, value, line, column, "module-import"))


def _javascript_tokens(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    index = 0
    while index < len(text):
        character = text[index]
        if character.isspace():
            index += 1
            continue
        if text.startswith("//", index):
            end = text.find("\n", index + 2)
            index = len(text) if end < 0 else end + 1
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 2
            continue
        if character in {'"', "'"}:
            value, end = _quoted(text, index)
            tokens.append(_Token("string", value, index))
            index = end
            continue
        if character == "`":
            _, index = _quoted(text, index, quote="`")
            continue
        if _IDENTIFIER_START.fullmatch(character):
            end = index + 1
            while end < len(text) and _IDENTIFIER_PART.fullmatch(text[end]):
                end += 1
            tokens.append(_Token("identifier", text[index:end], index))
            index = end
            continue
        tokens.append(_Token("punctuation", character, index))
        index += 1
    return tokens


def _quoted(text: str, index: int, quote: str | None = None) -> tuple[str, int]:
    delimiter = quote or text[index]
    index += 1
    value: list[str] = []
    while index < len(text):
        character = text[index]
        if character == "\\" and index + 1 < len(text):
            value.append(text[index + 1])
            index += 2
            continue
        if character == delimiter:
            return "".join(value), index + 1
        value.append(character)
        index += 1
    return "".join(value), index


def _word_end(text: str, index: int) -> bool:
    return index >= len(text) or not _IDENTIFIER_PART.fullmatch(text[index])


def _position(
    text: str, index: int, base_line: int, base_column: int
) -> tuple[int, int]:
    line_offset = text.count("\n", 0, index)
    if line_offset == 0:
        return base_line, base_column + index
    last_newline = text.rfind("\n", 0, index)
    return base_line + line_offset, index - last_newline


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("plugin", help="path to one .sdPlugin directory")
    return value


def main() -> int:
    args = parser().parse_args()
    plugin = pathlib.Path(args.plugin).expanduser().resolve()
    report = inspect_bundle_self_containment(plugin)
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

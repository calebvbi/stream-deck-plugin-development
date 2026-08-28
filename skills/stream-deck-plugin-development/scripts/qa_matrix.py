#!/usr/bin/env python3
"""Create, validate, and render a Stream Deck plugin QA evidence matrix."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import pathlib
import subprocess
import sys
from collections import Counter
from typing import Any


VERDICTS = {"NOT_RUN", "PASS", "FAIL", "APP_BLOCKED", "BLOCKED", "NOT_APPLICABLE"}
GATE_STATES = {"NOT_RUN", "PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE"}
CONTROLLERS = ("Keypad", "Encoder", "Neo")
EVIDENCE_ALIASES = {
    "trigger_received": ("trigger_received", "input_received"),
    "target_before": ("target_before", "app_before"),
    "target_after": ("target_after", "app_after"),
    "surface_after": ("surface_after", "key_face_after"),
}
RELEASE_GATES = (
    "spec_static_unit",
    "package",
    "installed_runtime",
    "vsd",
    "physical_hardware",
    "macos",
    "windows",
    "ci_release",
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: pathlib.Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def write_json(path: pathlib.Path, value: dict[str, Any], force: bool = False) -> None:
    write_output(
        path,
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        force,
    )


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


def write_output(path: pathlib.Path, content: str, force: bool = False) -> None:
    path = output_path(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path = output_path(str(path))
    flags = os.O_WRONLY | os.O_CREAT
    flags |= os.O_TRUNC if force else os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise FileExistsError(
            f"Refusing to overwrite {path}; pass --force to replace it"
        ) from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)


def git_value(cwd: pathlib.Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def repo_identity(manifest: pathlib.Path) -> tuple[str, str, bool]:
    repo_root = git_value(manifest.parent, "rev-parse", "--show-toplevel")
    if not repo_root:
        return "", "", False
    root = pathlib.Path(repo_root)
    sha = git_value(root, "rev-parse", "HEAD")
    dirty = bool(git_value(root, "status", "--porcelain"))
    return str(root), sha, dirty


def manifest_inventory(
    manifest: dict[str, Any], controllers: list[str], include_hidden: bool
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for action in manifest.get("Actions", []):
        if not isinstance(action, dict):
            continue
        action_controllers = action.get("Controllers") or ["Keypad"]
        visible = action.get("VisibleInActionsList", True) is not False
        if not include_hidden and not visible:
            continue
        for controller in controllers:
            if controller in action_controllers:
                rows.append(
                    {
                        "action_name": str(action.get("Name", "")),
                        "action_uuid": str(action.get("UUID", "")),
                        "controller": controller,
                        "visible_in_actions_list": visible,
                    }
                )
    return rows


def build_matrix(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = pathlib.Path(args.manifest).expanduser().resolve()
    manifest = load_json(manifest_path)
    repo_root, git_sha, git_dirty = repo_identity(manifest_path)
    package_path = pathlib.Path(args.package).expanduser().resolve() if args.package else None
    installed_path = (
        pathlib.Path(args.installed_manifest).expanduser().resolve()
        if args.installed_manifest
        else None
    )
    installed_manifest = load_json(installed_path) if installed_path and installed_path.is_file() else {}
    controllers = list(dict.fromkeys(args.controller or CONTROLLERS))
    controlled_system_version = (
        getattr(args, "controlled_system_version", "") or getattr(args, "app_build", "")
    )
    controlled_system = getattr(args, "controlled_system", "") or (
        "application" if controlled_system_version else ""
    )
    inventory = manifest_inventory(manifest, controllers, args.include_hidden)
    rows = []
    for index, action in enumerate(inventory, start=1):
        rows.append(
            {
                "sequence": index,
                "case_id": "primary",
                **action,
                "expected_behavior": "",
                "expected_no_target_mutation": False,
                "precondition": "",
                "settings": "",
                "trigger_timestamp": "",
                "evidence": {
                    "trigger_received": "",
                    "plugin_outcome": "",
                    "target_before": "",
                    "target_after": "",
                    "surface_after": "",
                    "artifacts": [],
                    "notes": "",
                },
                "verdict": "NOT_RUN",
                "blocker": "",
                "owner": "",
            }
        )
    return {
        "schema_version": 2,
        "created_at": utc_now(),
        "candidate": {
            "repo_root": repo_root,
            "git_sha": git_sha,
            "git_dirty_at_init": git_dirty,
            "manifest_path": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "plugin_uuid": str(manifest.get("UUID", "")),
            "plugin_version": str(manifest.get("Version", "")),
            "package_path": str(package_path) if package_path else "",
            "package_sha256": sha256_file(package_path),
            "installed_manifest_path": str(installed_path) if installed_path else "",
            "installed_manifest_sha256": sha256_file(installed_path),
            "installed_plugin_version": str(installed_manifest.get("Version", "")),
            "controlled_system": controlled_system,
            "controlled_system_version": controlled_system_version,
            "stream_deck_version": args.stream_deck_version,
            "device": args.device,
            "profile": args.profile,
            "target_identity": getattr(args, "target", "") or getattr(args, "task", ""),
            "controllers": controllers,
            "include_hidden": args.include_hidden,
            "runtime_restart_timestamp": "",
        },
        "release_gates": {
            name: {"state": "NOT_RUN", "evidence": "", "owner": ""}
            for name in RELEASE_GATES
        },
        "profile_restore": {
            "before_hash": "",
            "after_hash": "",
            "restored": False,
            "notes": "",
        },
        "rows": rows,
        "run_notes": "",
    }


def evidence_text(row: dict[str, Any], key: str) -> str:
    evidence = row.get("evidence")
    if not isinstance(evidence, dict):
        return ""
    for candidate in EVIDENCE_ALIASES.get(key, (key,)):
        value = evidence.get(candidate, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def validate_matrix(
    matrix: dict[str, Any],
    manifest_path: pathlib.Path,
    require_complete: bool,
    require_release: bool,
) -> list[str]:
    errors: list[str] = []
    schema_version = matrix.get("schema_version", 1)
    if schema_version not in {1, 2}:
        errors.append(f"unsupported schema_version {schema_version!r}")
    candidate = matrix.get("candidate") if isinstance(matrix.get("candidate"), dict) else {}
    candidate_controllers = candidate.get("controllers")
    if isinstance(candidate_controllers, list):
        controllers = [str(value) for value in candidate_controllers]
    else:
        controllers = [str(candidate.get("controller", "Keypad"))]
    invalid_controllers = sorted(set(controllers) - set(CONTROLLERS))
    if invalid_controllers:
        errors.append(f"unsupported controllers: {invalid_controllers}")
    include_hidden = bool(candidate.get("include_hidden", False))
    manifest = load_json(manifest_path)
    actual_hash = sha256_file(manifest_path)
    if candidate.get("manifest_sha256") != actual_hash:
        errors.append("manifest hash differs from the candidate lock")
    if require_release:
        require_complete = True
    if require_complete:
        required_identity = {
            "git_sha": candidate.get("git_sha"),
            "manifest_sha256": candidate.get("manifest_sha256"),
            "package_sha256": candidate.get("package_sha256"),
            "installed_manifest_sha256": candidate.get("installed_manifest_sha256"),
            "installed_plugin_version": candidate.get("installed_plugin_version"),
            "controlled_system": candidate.get("controlled_system") or candidate.get("app_build"),
            "stream_deck_version": candidate.get("stream_deck_version"),
            "device": candidate.get("device"),
            "profile": candidate.get("profile"),
            "runtime_restart_timestamp": candidate.get("runtime_restart_timestamp"),
        }
        for key, value in required_identity.items():
            if not str(value or "").strip():
                errors.append(f"candidate identity requires {key}")
        if candidate.get("git_dirty_at_init"):
            errors.append("candidate was initialized from a dirty worktree; SHA is not sufficient identity")
        source_version = str(candidate.get("plugin_version", ""))
        installed_version = str(candidate.get("installed_plugin_version", ""))
        if source_version and installed_version and source_version != installed_version:
            errors.append("installed plugin version differs from the candidate manifest")

    expected = {
        (item["action_uuid"], item["controller"])
        for item in manifest_inventory(manifest, controllers, include_hidden)
    }
    rows = matrix.get("rows")
    if not isinstance(rows, list):
        return errors + ["rows must be an array"]
    observed = {
        (str(row.get("action_uuid", "")), str(row.get("controller", "")))
        for row in rows
        if isinstance(row, dict)
    }
    missing = sorted(expected - observed)
    unexpected = sorted(observed - expected)
    if missing:
        errors.append(f"manifest actions missing from matrix: {missing}")
    if unexpected:
        errors.append(f"matrix actions absent from manifest inventory: {unexpected}")

    case_keys: set[tuple[str, str, str]] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"row {index} must be an object")
            continue
        label = f"row {index} {row.get('action_name', '')} [{row.get('case_id', 'primary')}]"
        case_key = (
            str(row.get("action_uuid", "")),
            str(row.get("controller", "")),
            str(row.get("case_id", "primary")),
        )
        if case_key in case_keys:
            errors.append(f"{label}: duplicate action/controller/case_id")
        case_keys.add(case_key)
        verdict = str(row.get("verdict", ""))
        if verdict not in VERDICTS:
            errors.append(f"{label}: invalid verdict {verdict!r}")
            continue
        if verdict in {"PASS", "APP_BLOCKED"}:
            for key in ("trigger_received", "plugin_outcome", "target_after", "surface_after"):
                if not evidence_text(row, key):
                    errors.append(f"{label}: {verdict} requires evidence.{key}")
            expected_no_target_mutation = bool(
                row.get("expected_no_target_mutation", row.get("expected_no_app_mutation", False))
            )
            if not expected_no_target_mutation and not evidence_text(row, "target_before"):
                errors.append(f"{label}: {verdict} requires evidence.target_before")
        if verdict == "APP_BLOCKED" and not str(row.get("blocker", "")).strip():
            errors.append(f"{label}: APP_BLOCKED requires a concrete blocker")
        if require_release and verdict == "APP_BLOCKED":
            errors.append(f"{label}: APP_BLOCKED cannot certify a release")
        if verdict in {"FAIL", "BLOCKED"} and not (
            str(row.get("blocker", "")).strip() or evidence_text(row, "notes")
        ):
            errors.append(f"{label}: {verdict} requires blocker or evidence.notes")
        if verdict == "NOT_APPLICABLE" and not (
            str(row.get("expected_behavior", "")).strip() and evidence_text(row, "notes")
        ):
            errors.append(f"{label}: NOT_APPLICABLE requires disposition and source/spec notes")
        if require_complete and verdict in {"NOT_RUN", "FAIL", "BLOCKED"}:
            errors.append(f"{label}: incomplete verdict {verdict}")

    gates = matrix.get("release_gates")
    if not isinstance(gates, dict):
        errors.append("release_gates must be an object")
    else:
        for name in RELEASE_GATES:
            gate = gates.get(name)
            if not isinstance(gate, dict):
                errors.append(f"release gate {name} is missing")
                continue
            state = str(gate.get("state", ""))
            if state not in GATE_STATES:
                errors.append(f"release gate {name} has invalid state {state!r}")
            if state != "NOT_RUN" and not str(gate.get("evidence", "")).strip():
                errors.append(f"release gate {name} requires evidence")
            if require_release and state in {"NOT_RUN", "FAIL", "BLOCKED"}:
                errors.append(f"release gate {name} is not closed: {state}")

    restore = matrix.get("profile_restore")
    if not isinstance(restore, dict):
        errors.append("profile_restore must be an object")
    elif require_complete and not restore.get("restored"):
        errors.append("profile restoration is not confirmed")
    return errors


def esc(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value))


def status_class(value: str) -> str:
    normalized = value.lower().replace("_", "-")
    return "".join(
        character if character in "abcdefghijklmnopqrstuvwxyz0123456789-" else "-"
        for character in normalized
    ) or "unknown"


def render_report(matrix: dict[str, Any]) -> str:
    candidate = matrix.get("candidate", {})
    rows = matrix.get("rows", [])
    counts = Counter(str(row.get("verdict", "NOT_RUN")) for row in rows if isinstance(row, dict))
    cards = "".join(
        f'<div class="metric {status_class(name)}"><strong>{counts.get(name, 0)}</strong><span>{esc(name)}</span></div>'
        for name in ("PASS", "APP_BLOCKED", "FAIL", "BLOCKED", "NOT_APPLICABLE", "NOT_RUN")
    )
    identity_rows = "".join(
        f"<tr><th>{esc(key.replace('_', ' ').title())}</th><td><code>{esc(value)}</code></td></tr>"
        for key, value in candidate.items()
        if value not in ("", None, False)
    )
    gate_rows = ""
    for name, gate in matrix.get("release_gates", {}).items():
        state = str(gate.get("state", "NOT_RUN"))
        gate_rows += (
            f"<tr><th>{esc(name.replace('_', ' ').title())}</th>"
            f'<td data-label="State"><span class="pill {status_class(state)}">{esc(state)}</span></td>'
            f"<td data-label=\"Evidence\">{esc(gate.get('evidence', ''))}</td>"
            f"<td data-label=\"Owner\">{esc(gate.get('owner', ''))}</td></tr>"
        )
    matrix_rows = ""
    for row in rows:
        if not isinstance(row, dict):
            continue
        evidence = row.get("evidence", {})
        artifacts = evidence.get("artifacts", []) if isinstance(evidence, dict) else []
        evidence_blob = "\n".join(
            f"{key}: {evidence_text(row, key)}"
            for key in (
                "trigger_received",
                "plugin_outcome",
                "target_before",
                "target_after",
                "surface_after",
                "notes",
            )
            if evidence_text(row, key)
        )
        if artifacts:
            evidence_blob += "\nartifacts: " + json.dumps(artifacts, ensure_ascii=False)
        verdict = str(row.get("verdict", "NOT_RUN"))
        matrix_rows += (
            f"<tr data-verdict=\"{esc(verdict)}\"><td data-label=\"#\">{esc(row.get('sequence'))}</td>"
            f"<td data-label=\"Action\"><strong>{esc(row.get('action_name'))}</strong><br><code>{esc(row.get('action_uuid'))}</code></td>"
            f"<td data-label=\"Case\">{esc(row.get('case_id', 'primary'))}<br>{esc(row.get('controller'))}</td>"
            f"<td data-label=\"Precondition / settings\">{esc(row.get('precondition'))}<br><small>{esc(row.get('settings'))}</small></td>"
            f"<td data-label=\"Expected\">{esc(row.get('expected_behavior'))}</td>"
            f"<td data-label=\"Evidence\"><details><summary>Evidence</summary><pre>{esc(evidence_blob)}</pre></details></td>"
            f'<td data-label="Verdict"><span class="pill {status_class(verdict)}">{esc(verdict)}</span><br><small>{esc(row.get("blocker"))}</small></td></tr>'
        )
    restore = matrix.get("profile_restore", {})
    raw_json = json.dumps(matrix, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stream Deck Plugin QA</title><style>
:root{{--bg:#0b1017;--panel:#131b26;--ink:#edf4ff;--muted:#9aabc0;--line:#293548;--pass:#38d996;--warn:#ffca5c;--fail:#ff667a;--info:#79a8ff}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,sans-serif}} main{{max-width:1440px;margin:auto;padding:clamp(18px,4vw,48px)}}
h1{{font-size:clamp(30px,5vw,56px);line-height:1;margin:.2em 0}} h2{{margin-top:38px}} p,small{{color:var(--muted)}} code,pre{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:24px 0}} .metric,.panel{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}}
.metric strong{{display:block;font-size:30px}} .metric span{{color:var(--muted)}} .metric.pass{{border-color:#286e59}} .metric.app-blocked,.metric.blocked{{border-color:#806628}} .metric.fail{{border-color:#8a3241}}
.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:14px}} table{{width:100%;border-collapse:collapse;min-width:820px}} th,td{{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}} th{{color:#c9d8eb;background:#111925}} td code{{font-size:12px;color:#b9caf0}}
.pill{{display:inline-block;padding:3px 8px;border-radius:999px;background:#27354a;font-size:12px;font-weight:700}} .pill.pass{{background:#164c3b;color:#8ff0c7}} .pill.fail{{background:#5b202d;color:#ffadba}} .pill.app-blocked,.pill.blocked{{background:#57451d;color:#ffe09b}} .pill.not-applicable{{background:#283d61;color:#b8d2ff}}
details summary{{cursor:pointer;color:var(--info)}} pre{{white-space:pre-wrap;min-width:340px;color:#c9d8eb}} .toolbar{{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}} button{{background:#1e2b3d;color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px 10px;cursor:pointer}}
@media(max-width:700px){{main{{padding:16px}} .table-wrap{{overflow:visible;border:0}} table{{min-width:0}} thead{{display:none}} tbody,tr,td,th{{display:block;width:100%}} tr{{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:0 0 12px;padding:8px}} th,td{{border:0;padding:7px 9px}} td[data-label]::before{{content:attr(data-label);display:block;color:var(--muted);font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;margin-bottom:3px}} pre{{min-width:0;overflow-wrap:anywhere}}}}
</style></head><body><main>
<p>Locked candidate evidence report</p><h1>Stream Deck Plugin QA</h1><p>Generated {esc(utc_now())}. Verdicts remain separate from release gates.</p>
<section class="metrics">{cards}</section>
<h2>Candidate identity</h2><div class="table-wrap"><table>{identity_rows}</table></div>
<h2>Release gates</h2><div class="table-wrap"><table><thead><tr><th>Gate</th><th>State</th><th>Evidence</th><th>Owner</th></tr></thead><tbody>{gate_rows}</tbody></table></div>
<h2>Action matrix</h2><div class="toolbar"><button onclick="filterRows('ALL')">All</button><button onclick="filterRows('PASS')">Pass</button><button onclick="filterRows('APP_BLOCKED')">App-blocked</button><button onclick="filterRows('FAIL')">Fail</button><button onclick="filterRows('NOT_RUN')">Not run</button><button onclick="copyJson()">Copy as JSON</button></div>
<div class="table-wrap"><table><thead><tr><th>#</th><th>Action</th><th>Case</th><th>Precondition / settings</th><th>Expected</th><th>Evidence</th><th>Verdict</th></tr></thead><tbody>{matrix_rows}</tbody></table></div>
<h2>Restoration</h2><div class="panel"><p><strong>Restored:</strong> {esc(restore.get('restored'))}</p><p><strong>Before:</strong> <code>{esc(restore.get('before_hash'))}</code><br><strong>After:</strong> <code>{esc(restore.get('after_hash'))}</code></p><p>{esc(restore.get('notes'))}</p></div>
<h2>Run notes</h2><div class="panel"><p>{esc(matrix.get('run_notes', ''))}</p></div>
<script id="matrix-data" type="application/json">{raw_json}</script><script>
function filterRows(v){{document.querySelectorAll('tbody tr[data-verdict]').forEach(r=>r.hidden=v!=='ALL'&&r.dataset.verdict!==v)}}
async function copyJson(){{await navigator.clipboard.writeText(document.getElementById('matrix-data').textContent);}}
</script></main></body></html>"""


def command_init(args: argparse.Namespace) -> int:
    matrix = build_matrix(args)
    output = output_path(args.output)
    write_json(output, matrix, args.force)
    controllers = ", ".join(matrix["candidate"]["controllers"])
    print(f"Created {output} with {len(matrix['rows'])} action rows for {controllers}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    matrix_path = pathlib.Path(args.matrix).expanduser().resolve()
    manifest_path = pathlib.Path(args.manifest).expanduser().resolve()
    errors = validate_matrix(
        load_json(matrix_path),
        manifest_path,
        args.require_complete,
        args.require_release,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Validation failed with {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("Matrix validation passed")
    return 0


def command_render(args: argparse.Namespace) -> int:
    matrix_path = pathlib.Path(args.matrix).expanduser().resolve()
    output = output_path(args.output)
    write_output(output, render_report(load_json(matrix_path)), args.force)
    print(f"Rendered {output}")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a manifest-driven QA matrix")
    init.add_argument("--manifest", required=True)
    init.add_argument("--output", required=True)
    init.add_argument(
        "--controller",
        action="append",
        choices=CONTROLLERS,
        help="controller to inventory; repeat as needed (default: all current controllers)",
    )
    init.add_argument("--include-hidden", action="store_true")
    init.add_argument("--package", default="")
    init.add_argument("--installed-manifest", default="")
    init.add_argument("--controlled-system", default="")
    init.add_argument("--controlled-system-version", "--app-build", default="")
    init.add_argument("--stream-deck-version", default="")
    init.add_argument("--device", default="Virtual Stream Deck")
    init.add_argument("--profile", default="")
    init.add_argument("--target", "--task", default="")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)

    validate = sub.add_parser("validate", help="validate inventory and evidence completeness")
    validate.add_argument("--matrix", required=True)
    validate.add_argument("--manifest", required=True)
    validate.add_argument("--require-complete", action="store_true")
    validate.add_argument("--require-release", action="store_true")
    validate.set_defaults(func=command_validate)

    render = sub.add_parser("render", help="render a self-contained HTML report")
    render.add_argument("--matrix", required=True)
    render.add_argument("--output", required=True)
    render.add_argument("--force", action="store_true")
    render.set_defaults(func=command_render)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

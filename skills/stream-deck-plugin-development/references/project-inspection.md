# Project inspection and completion reports

Use this reference when project facts affect implementation, troubleshooting, compatibility, or release conclusions.

## Inspect current project facts

Run the inspector from the skill directory against the plugin repository:

```bash
python3 scripts/inspect_project.py --project /path/to/plugin
```

Pass `--manifest` when the repository contains more than one `*.sdPlugin/manifest.json`. Pass `--output` only when the user wants a saved report. The command refuses to overwrite an existing report.

The inspector reads the manifest, package metadata, package locks, installed SDK package when present, controller declarations, UUIDs, Property Inspector paths, Encoder layouts, and declared compatibility. It does not install packages, run project commands, call the network, validate a package, or prove host behavior.

Treat these report states literally:

- `DECLARED` records a project claim such as `Software.MinimumVersion`.
- `STATIC` records a file, path, hash, or package fact observed during inspection.
- `CONFLICT` identifies incompatible declared facts, such as a Neo controller below its host minimum.
- `UNVERIFIED` names runtime proof that inspection cannot provide.

Regenerate the report after changes. Do not maintain a second project-context file that can drift from the manifest or package lock.

## Report the result

Use the smallest contract that fits the task. Include concrete file or command evidence. Omit a field only when it does not apply.

### Create

```text
Plan:
Identity:
Declared compatibility:
Changed files:
Verification:
Unverified:
Next:
```

### Troubleshoot

```text
Symptom:
First failing layer:
Observed evidence:
Root cause:
Change or next diagnostic:
Verification:
Unverified:
```

### Compatibility

```text
Decision:
Existing floor:
Feature minimum:
Static evidence:
Minimum-host runtime proof:
Next:
```

### Release

```text
Candidate identity:
Source and unit:
Package:
Installed runtime:
Simulated input:
Physical hardware and platforms:
CI and publication:
Gate:
Blocker:
Next:
```

Never collapse missing evidence into a generic pass. Use `NOT_RUN`, `BLOCKED`, `FAIL`, or `UNVERIFIED` where applicable.

## Worked scenario: Signal Lamp

Signal Lamp is a fictional plugin used only to show the workflow. Its manifest declares:

```json
{
  "UUID": "com.example.signal-lamp",
  "SDKVersion": 3,
  "Software": { "MinimumVersion": "7.1" },
  "Actions": [
    {
      "UUID": "com.example.signal-lamp.toggle",
      "Controllers": ["Keypad", "Encoder"],
      "PropertyInspectorPath": "ui/lamp.html",
      "Encoder": { "layout": "layouts/dial.json" }
    }
  ]
}
```

Suppose a request adds a Neo infobar surface while preserving Stream Deck 7.1. Inspecting the current files can establish the existing floor, controller declarations, UUIDs, and resource paths. The Neo platform contract requires Stream Deck 7.6 or later, so the request contains a compatibility conflict.

A correct compatibility report is concise:

```text
Decision: The Neo surface cannot retain the declared 7.1 host floor.
Existing floor: Stream Deck 7.1, SDKVersion 3.
Feature minimum: Neo requires Stream Deck 7.6 or later.
Static evidence: The existing Keypad and Encoder action keeps com.example.signal-lamp.toggle; no UUID replacement is needed.
Minimum-host runtime proof: UNVERIFIED. Static inspection cannot prove the packaged plugin on Stream Deck 7.6 or the retained 7.1 path.
Next: Choose a 7.1-compatible fallback or approve the floor change before implementation.
```

The example does not prove a real package, installed runtime, device, operating system, CI run, or Marketplace result.

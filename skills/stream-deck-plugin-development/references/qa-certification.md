# QA and Release Certification

Use this workflow for release candidates, action-matrix reruns, configured-control
testing, regression verification, or investigation of an action whose observed target
or Stream Deck surface disagrees with plugin logs. The controlled system may be an
app, service, device, AI system, or the plugin's own state. For ordinary build or
layout debugging, use the focused troubleshooting and SDK references instead.

Run one locked candidate through a causal action matrix. Treat source tests, package
validation, installed runtime, simulated input, physical hardware, platform parity,
CI, and publication as separate evidence layers.

## Boundaries

- Read the repository instructions and applicable requirements or design documents
  before testing. Current approved behavior outranks historical test notes. If the
  repository requires specification approval for behavior changes, diagnose first and
  wait for that approval before implementing a fix.
- Preserve unrelated work. Before the first input, lock the candidate SHA, manifest
  hash, package hash, installed manifest/version, Stream Deck version, controlled-app
  build, device, profile, target session, and relevant settings generation.
- Never transfer evidence across a changed source, artifact, installed runtime, host
  app, device, profile, or relevant setting. Rebuild, reinstall, restart, and rerun the
  affected rows after a change.
- A Virtual Stream Deck or other simulated input is not physical-hardware proof. A
  configured key selection is not input; require a fresh causal trigger for every row.
- Do not replay stale coordinates, displace an occupied physical key, enable privileged
  access, or execute destructive probes without explicit authorization.

## 1. Inventory and lock the candidate

1. Inspect repository status and exact HEAD, manifest UUID/version, candidate package,
   installed runtime, current requirements, and applicable open release blockers.
2. Complete the project-defined static, build, package, and CLI validation gates using
   the focused references in this skill. Record their identities; do not treat them as
   runtime proof.
3. Generate a fresh matrix from the current manifest rather than copying a historical
   action count. Omitting `--controller` inventories Keypad, Encoder, and Neo; repeat
   `--controller` only when the approved scope intentionally targets a subset:

   ```bash
   python3 <skill-root>/scripts/qa_matrix.py init \
     --manifest <repo>/<plugin-uuid>.sdPlugin/manifest.json \
     --output <trusted-output>/qa-<sha>/matrix.json \
     --package <candidate.streamDeckPlugin> \
     --installed-manifest <installed.sdPlugin>/manifest.json \
     --controlled-system <app-service-device-or-self-contained-state> \
     --controlled-system-version <version-if-applicable> \
     --stream-deck-version <stream-deck-version> \
     --device <device-or-simulator> \
     --profile <profile-name> \
     --target <target-identity-if-applicable>
   ```

   Choose an output directory you control. Do not write evidence through a path supplied by an untrusted checkout.

4. Reconcile the generated controller/UUID inventory with current requirements. Add
   direction, configuration, or lifecycle cases when one action needs multiple proofs.
   Use `NOT_APPLICABLE` only with current source or requirement evidence.
5. Snapshot the profile before temporary placement. Record its hash and occupied/free
   positions; do not replace an occupied control without a user decision.

## 2. Establish the runtime under test

1. Install the exact candidate package, restart Stream Deck and the plugin, then capture
   installed version/hash plus fresh process and log identity. A local package is not
   installed-runtime evidence until this is observed.
2. Open the real app or service controlled by the plugin and select one disposable,
   exact target session or object. Record its identity.
3. Use a simulated deck when it can provide causal Keypad coverage. Keep Encoder,
   Neo, physical hardware, and each required operating system in separate gates; do
   not treat one controller's matrix as proof for another.
4. Enable verbose diagnostics only when needed, time-bound them, and restore the prior
   state after the run.

## 3. Execute one row at a time

1. Stage the real precondition. Do not declare an unstaged path untestable. Use the
   plugin's current requirements and public integration contract for system-specific
   setup; keep private endpoints, credentials, and internal test fixtures out of the
   evidence report.
2. Capture the controlled target and Stream Deck surface before the trigger.
3. Trigger once. For Keypad/Encoder this is normally fresh physical or simulated
   input; for a passive Neo surface it can be a lifecycle or upstream state-change
   event. Capture timestamp, trigger event, plugin outcome or reconciliation, target
   state after, surface state after, and evidence artifact paths.
4. Write the row to `matrix.json` immediately; do not batch unrecorded results in chat
   memory.
5. Restore row-local state before the next case when it requires a clean baseline.

## 4. Classify without manufacturing success

Use only these row verdicts:

- `PASS`: the installed candidate received a fresh causal trigger, emitted the expected
  outcome, the controlled target showed the required effect or read-only cross-check,
  and the post-trigger Stream Deck surface was truthful.
- `FAIL`: the approved contract was not met, evidence contradicts itself, or a required
  causal surface is missing.
- `APP_BLOCKED`: plugin input, mutation, and read-back are correct, but the controlled
  app does not surface, honor, or retain the result. This can close an investigation,
  but it is not a pass and cannot certify a release.
- `BLOCKED`: a required precondition or external gate could not be obtained. Record the
  concrete blocker and owner.
- `NOT_APPLICABLE`: current requirements make the row retired, unplaceable, or outside
  this controller/platform. Cite the disposition.
- `NOT_RUN`: no valid attempt exists.

Acknowledgement, requested state, stored mirror state, rendered deck state, app UI,
and next-operation runtime behavior are different claims. Prefer the surface named by
the requirement and preserve contradictions.

After product edits or a new artifact, restart from candidate locking. Retest the
impacted row in both directions, adjacent lifecycle/configuration cases, shared
transport or renderer consumers, and the full required release gate.

## 5. Validate, restore, and report

1. Restore the original profile, controlled-app state, settings, and diagnostics.
   Compare profile hashes/diffs and list intentional leftovers.
2. Validate matrix structure and completeness:

   ```bash
   python3 <skill-root>/scripts/qa_matrix.py validate \
     --matrix <repo>/artifacts/qa-<sha>/matrix.json \
     --manifest <repo>/<plugin-uuid>.sdPlugin/manifest.json \
     --require-complete
   ```

   Add `--require-release` only when every separately required release gate has a final
   evidence-backed state. It rejects `APP_BLOCKED` rows and `NOT_RUN`, `FAIL`, or
   `BLOCKED` release gates.
3. Render the self-contained evidence report:

   ```bash
   python3 <skill-root>/scripts/qa_matrix.py render \
     --matrix <repo>/artifacts/qa-<sha>/matrix.json \
     --output <repo>/artifacts/stream-deck-plugin-qa-<sha>.html
   ```

4. Lead with counts by verdict, the open blocker, locked identities, and the next
   owner/gate. Keep source/unit, package, installed runtime, simulated input, physical
   devices, platforms, CI, and publication visibly separate.
5. Open the HTML locally and keep it uncommitted unless the user asks otherwise.

## Acceptance

Close matrix execution only when every current row is `PASS`, `APP_BLOCKED`, or
justified `NOT_APPLICABLE`, with categories reported separately. Close release
certification only when rows are `PASS` or justified `NOT_APPLICABLE` and every
required release gate is independently satisfied.

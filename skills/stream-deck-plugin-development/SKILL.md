---
name: stream-deck-plugin-development
description: Create, develop, test, troubleshoot, package, and certify Elgato Stream Deck plugins that use the Node.js SDK. Use for Stream Deck repository or runtime work involving manifests, actions, keys, dials, Neo, Property Inspectors, settings, profiles, animation, Marketplace validation, or causal QA. Do not use for general TypeScript or third-party API work unless it changes Stream Deck behavior.
---

# Stream Deck plugin development

Use this skill for end-to-end Stream Deck plugin work with the official `@elgato/streamdeck` Node.js SDK.

Keep third-party APIs, OAuth providers, app-specific IPC, testing frameworks, and general TypeScript in the project's existing architecture. Apply this skill only where those systems meet Stream Deck.

## Use the right source

When sources conflict, use this order and report unresolved conflicts:

1. Approved project requirements and repository instructions define intended behavior.
2. The manifest, package lock, and existing implementation define the compatibility contract.
3. Installed `@elgato/streamdeck` types define the API available to the checkout.
4. Current official schemas, documentation, and changelog define the platform contract and feature minimums.
5. This skill's references provide workflow guidance and maintained summaries.

Use current Node.js SDK APIs. Do not copy legacy SDK examples into a current plugin.

Bundled helpers require Python 3.10 or newer. Use the host's Python 3 launcher
(`python3`, `python`, or `py -3`); if none is available, perform the equivalent read-only
checks manually and report that the helper was not run.

## Choose a workflow

- For a new plugin, read `references/getting-started.md`, `references/manifest.md`, and `references/cli-distribution.md`. Decide the controller surfaces, settings, external integration, compatibility floor, destination, distribution intent, and permanent plugin UUID before scaffolding.
- For implementation work, inspect `package.json`, the manifest, the package lock, and installed SDK types. When a manifest exists, run `scripts/inspect_project.py` to derive a fresh project snapshot. Read only the references routed for the feature, then use the repository's existing build and test commands.
- For troubleshooting, reproduce the failure at the lowest available evidence layer. Run `scripts/inspect_project.py`, then read `references/troubleshooting.md` and the reference for the failing feature before changing source.
- For release or causal QA, read `references/qa-certification.md`. Lock the candidate identity before runtime testing, run the bundled Property Inspector closure verifier when a PI exists, and keep each evidence layer separate.

Treat inspector output as generated evidence, not a context file. Do not copy it into the project unless the user asks for an artifact.

Register every action and global event handler before `streamDeck.connect()`. Treat `connect()` as the final initialization step.

## Route by task

| Task | Read |
|---|---|
| Setup, scaffold, runtime requirements, file structure | `references/getting-started.md` |
| Manifest fields, UUIDs, compatibility, paths | `references/manifest.md` |
| Action registration and shared lifecycle/events | `references/actions-events.md` |
| Key behavior, states, images, temporary feedback | `references/keys.md` |
| Dials, touch strip, layouts, feedback, dial events | `references/dials-layouts.md` |
| Animation, frame scheduling, lifecycle quiescence | `references/animation-runtime.md` |
| Action and global settings, including security | `references/settings.md` |
| Property Inspectors and sdpi-components | `references/property-inspector.md` |
| Device types, device events, profiles | `references/devices-profiles.md` |
| Embedded resources, system, deep links, app monitoring, logging, localization | `references/platform-services.md` |
| CLI, validation, packaging, DRM, distribution | `references/cli-distribution.md` |
| Marketplace UX, images, and Property Inspector requirements | `references/plugin-guidelines.md` |
| Runtime, build, Property Inspector, and layout failures | `references/troubleshooting.md` |
| Causal action-matrix QA, candidate identity, evidence reports, release gates | `references/qa-certification.md` |
| Project inspection, completion-report contracts, synthetic worked scenario | `references/project-inspection.md` |
| Current official documentation links | `references/official-sources.md` |

## Preserve these invariants

- Preserve an existing plugin's declared compatibility unless the task requires a change. Map every new API or manifest field to its official introduction version before raising or relying on a minimum.
- Use documented SDK APIs, event names, manifest fields, layouts, controllers, and device types. Use installed types and official sources instead of guessing.
- Keep plugin and action UUIDs stable after publication. Keep manifest action UUIDs synchronized with `@action({ UUID })` implementations.
- Treat `Keypad`, `Encoder`, and `Neo` as distinct controller surfaces. Match every declared controller to its supported input and feedback contract.
- Store per-instance configuration in action settings and plugin-wide configuration in global settings. Keep developer and service secrets out of distributed plugins.
- Keep programmatic rendering at or below 10 updates per second. For periodic visuals, use one owner per `action.id`, bounded work, deduplication, backpressure, lifecycle cancellation, and idle quiescence. Read `references/animation-runtime.md` before implementing animation.
- Edit source and rebuild generated files under `*.sdPlugin/bin/`. Do not hand-edit compiled output.
- Distributed Property Inspector resources must close inside the plugin bundle. Reject remote executable/UI assets, missing local dependencies, unsafe paths, and symlinks; do not confuse runtime API calls with static dependencies.
- Keep source and unit tests, package validation, installed runtime, simulated input, physical hardware, platform, CI, and publication evidence separate. Identity changes invalidate downstream evidence.

## Prove completion

1. Record the inspected manifest, package, SDK version, and applicable repository instructions.
2. Build or type-check with the repository's one-shot command. Run defined lint and tests when relevant.
3. For a plugin with a Property Inspector, run `python3 <skill-root>/scripts/bundle_self_containment.py <plugin-uuid>.sdPlugin`, then run `streamdeck validate <plugin-uuid>.sdPlugin` when the CLI is available.
4. Confirm manifest and implementation UUIDs, settings paths, declared controllers, and generated output match.
5. For compatibility work, test the packaged plugin on the declared minimum host. An unchanged manifest is not compatibility proof.
6. For runtime behavior, verify in Stream Deck or state the exact remaining runtime and device checks.
7. For release certification or app-controlling actions, run the QA workflow and report every verdict and evidence layer separately.
8. Use the matching completion contract in `references/project-inspection.md`; omit fields that do not apply instead of filling them with assumptions.

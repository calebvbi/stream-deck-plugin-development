# CLI, Validation, Packaging, and Distribution

Official CLI docs: https://docs.elgato.com/streamdeck/cli/intro/
Official distribution guide: https://docs.elgato.com/streamdeck/sdk/introduction/distribution/

## Install CLI

Inspect and record the existing and current published versions first:

```bash
streamdeck -v
npm view @elgato/cli version
```

If the CLI is missing or needs an update, obtain authorization before changing the
global toolchain, install the resolved version explicitly, and verify it afterward.
The official docs use `@latest`; recording the resolved version makes the run
reproducible.

Current CLI development prerequisites are Node.js 24+ and Stream Deck 7.1+.

## Core commands

Create/scaffold:

```bash
streamdeck create
```

Developer mode:

```bash
streamdeck dev
streamdeck dev --disable
```

Developer mode enables Node debugger attachment and PI debugging at `http://localhost:23654/`.
Restore the prior developer-mode state after a temporary debugging session.

Link a plugin directory:

```bash
streamdeck link <plugin-uuid>.sdPlugin
```

The directory name must match the plugin UUID and end in `.sdPlugin`.

List linked plugins:

```bash
streamdeck list
streamdeck list --all
```

Restart:

```bash
streamdeck restart <plugin-uuid>
```

Stop:

```bash
streamdeck stop <plugin-uuid>
```

Unlink:

```bash
streamdeck unlink <plugin-uuid>
```

Do not use `--delete` casually; it can remove a normally installed plugin rather than merely a linked development plugin.

Validate:

```bash
streamdeck validate <plugin-uuid>.sdPlugin
```

In CI, `--no-update-check` is recommended to prevent schema/rule updates during the pipeline:

```bash
streamdeck validate <plugin-uuid>.sdPlugin --no-update-check
```

Package:

```bash
streamdeck pack <plugin-uuid>.sdPlugin --output dist/
```

`pack` validates before creating the `.streamDeckPlugin` installer.

Useful options include:

```bash
streamdeck pack <plugin>.sdPlugin --dry-run
streamdeck pack <plugin>.sdPlugin --output dist/
streamdeck pack <plugin>.sdPlugin --version "1.2.3.0"
```

`--version` writes the supplied version to the manifest before packaging; do not use it casually during local validation.

## .sdignore

Place `.sdignore` in the root of the `.sdPlugin` bundle next to the manifest. Syntax follows `.gitignore` conventions.

By default, pack excludes `.git`, `/.env*`, `*.log`, and `*.js.map`.

Keep development-only files and secrets out of packages.

## Recommended validation sequence

1. Inspect `package.json` scripts.
2. Run the one-shot build (`npm run build` in the standard scaffold).
3. Run repo lint/tests when defined and relevant.
4. Run `streamdeck validate` for the plugin bundle when CLI access is available.
5. Runtime-test in Stream Deck when the behavior cannot be established statically.
6. Run `streamdeck pack` only for release/distribution work.

## DRM

Current DRM compatibility requirements include:

- Node.js plugin uses `@elgato/streamdeck` v2+.
- `SDKVersion` is `3`.
- `Software.MinimumVersion` is `6.9` or higher.

DRM-protected output is produced after upload/processing in Maker Console, not merely by local packaging.

For DRM-compatible plugins, distributed files are treated as immutable and the manifest is protected; do not design runtime behavior that modifies distributed files or depends on reading the manifest at runtime.

## Marketplace publishing

Before publishing:

- review current Plugin Guidelines
- create required Marketplace/app imagery
- validate the plugin
- package a `.streamDeckPlugin`
- submit/manage the version through Maker Console

Do not encode review timelines or Maker Console workflow assumptions in code; those processes can change.

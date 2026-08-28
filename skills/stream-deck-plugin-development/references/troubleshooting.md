# Troubleshooting

Use the installed SDK types, Stream Deck CLI validation, plugin logs, and the local Stream Deck developer tools before guessing at runtime behavior.

## Plugin does not appear or run

1. Run the repository's one-shot build.
2. Run `streamdeck validate <plugin-uuid>.sdPlugin`.
3. Confirm the `.sdPlugin` directory name matches the manifest `UUID`.
4. Confirm the manifest `CodePath` exists after the build.
5. Confirm the manifest action UUIDs match their `@action({ UUID })` implementations.
6. Confirm the plugin is linked/installed in the local Stream Deck development environment.
7. Inspect `*.sdPlugin/logs/` for startup/runtime failures.

After a fresh Stream Deck install/update, the app may temporarily be running elevated on Windows; Elgato's getting-started guide notes that restarting Stream Deck can resolve a generated/linked plugin not appearing.

## Plugin code changes are not reflected

For the standard scaffold, use:

```bash
npm run watch
```

The generated watch command rebuilds source changes and restarts the plugin. If not using the watcher, rebuild and restart explicitly:

```bash
npm run build
streamdeck restart <plugin-uuid>
```

Inspect `package.json` before assuming the project uses the standard scripts.

## Property inspector debugging

Enable developer mode when needed:

```bash
streamdeck dev
```

If this workflow enabled developer mode and it was previously disabled, restore it
after debugging with `streamdeck dev --disable`.

With the PI visible in Stream Deck, inspect it using the local debugger:

```text
http://localhost:23654/
```

If a PI does not appear or load, isolate the first failing boundary in order:

1. HTML load: validate `PropertyInspectorPath`, path precedence, and bundled file existence.
2. Script load: inspect console/network errors and confirm local dependencies resolve.
3. Bridge readiness: verify `sdpi-components` initialization or the repository's
   established custom/legacy bridge without replacing that stack during diagnosis.
4. Action context: ensure the expected action is selected and visible; only active PI
   pages appear in the debugger.
5. Settings round-trip: verify action/global scope and observe the corresponding
   settings event in plugin logs.
6. Custom messaging: trace `sendToPlugin` and `sendToPropertyInspector` separately
   after settings persistence works.

## Dial layout does not render

- Validate the layout JSON against the current touch-strip layout reference.
- Keep every item inside the 200×100px canvas.
- Confirm layout item keys used by `setFeedback` match the layout definition.
- Prefer a built-in layout first when isolating whether the failure is custom layout JSON or action logic.
- Do not use the removed `dialPress` event; use `onDialDown`/`onDialUp`.

## Settings appear stale

- Prefer settings delivered in action event payloads where available.
- Use `onDidReceiveSettings`/global settings events rather than polling.
- Confirm PI components persist to the intended scope (`setting`, and `global` only when intended).
- Remember action settings belong to one action instance; global settings are plugin-wide.

## Runtime debugging

Use `streamDeck.logger` for diagnostics so messages land in supported plugin logs.

If Node debugger attachment is needed, use the manifest's documented `Nodejs.Debug` configuration and developer mode rather than adding ad hoc debug servers.

## CI or agent environments without Stream Deck

If Stream Deck/CLI/hardware is unavailable:

- run build/type-check/lint/tests that exist
- inspect manifest and generated paths statically
- do not claim runtime/device verification occurred
- state the exact remaining Stream Deck/manual checks

Official references:

- https://docs.elgato.com/streamdeck/sdk/introduction/getting-started/
- https://docs.elgato.com/streamdeck/sdk/guides/ui/
- https://docs.elgato.com/streamdeck/sdk/guides/logging/
- https://docs.elgato.com/streamdeck/cli/commands/validate/
- https://docs.elgato.com/streamdeck/cli/commands/restart/

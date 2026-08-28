# Platform Services

This reference covers current Stream Deck-specific platform services that do not need their own large skill.

## Embedded resources

Official guide: https://docs.elgato.com/streamdeck/sdk/guides/resources/

Available from Stream Deck 7.1+.

Resources can be embedded into action instances so exported `.streamDeckAction`/`.streamDeckProfile` files remain portable.

Relevant SDK operations include:

- `action.setResources(...)`
- `action.getResources()`
- `SingletonAction.onDidReceiveResources(...)`

Use resources for files that belong to an action instance, such as audio/config/script files. The payload is a key-to-file-path mapping so Stream Deck can remap paths when importing/exporting.

## System utilities

Official guide: https://docs.elgato.com/streamdeck/sdk/guides/system/

Use `streamDeck.system.openUrl(...)` to open an HTTP/HTTPS URL in the user's default browser.

The SDK's `openUrl` does not support arbitrary custom URL schemes.

Use `streamDeck.system.onSystemDidWakeUp(...)` to restore connections/state after system wake when needed. Visible actions also receive `onWillAppear` during the wake procedure.

## Deep links

Official guide: https://docs.elgato.com/streamdeck/sdk/guides/deep-linking/

Plugins can receive messages at:

```text
streamdeck://plugins/message/<PLUGIN_UUID>
```

Handle them with `streamDeck.system.onDidReceiveDeepLink(...)`.

From Stream Deck 7.0+, `?streamdeck=hidden` enables passive deep links that do not bring Stream Deck to the foreground.

Useful for OAuth callbacks, local IPC setup, and configuration handoff.

## App monitoring

Official guide: https://docs.elgato.com/streamdeck/sdk/guides/app-monitoring/

Declare apps in `ApplicationsToMonitor` in the manifest, then subscribe to:

- `streamDeck.system.onApplicationDidLaunch(...)`
- `streamDeck.system.onApplicationDidTerminate(...)`

Windows entries use executable names. macOS entries use bundle identifiers.

Do not poll the process list when Stream Deck's app-monitoring API already fits the task.

## Logging

Official guide: https://docs.elgato.com/streamdeck/sdk/guides/logging/

Prefer:

```ts
streamDeck.logger.info("message");
streamDeck.logger.error("message");
```

instead of `console` for plugin logs, because the SDK logger writes to the supported log targets, including plugin log files.

Plugin log files live under the plugin's `logs/` directory.

Never log tokens, credentials, private user data, or secrets.

## Localization

Official guide: https://docs.elgato.com/streamdeck/sdk/guides/i18n/

Current Stream Deck language resource files include:

- `zh_CN.json`
- `zh_TW.json`
- `de.json`
- `en.json`
- `fr.json`
- `ja.json`
- `ko.json`
- `es.json`

Use Stream Deck's documented localization resources for plugin/action metadata and SDK-side strings.

For property inspectors built with `sdpi-components`, use the sdpi-components localization mechanism described in `property-inspector.md`.

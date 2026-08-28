# Manifest Reference

Use the live schema as the exact source of truth:

```json
"$schema": "https://schemas.elgato.com/streamdeck/plugins/manifest.json"
```

Official reference: https://docs.elgato.com/streamdeck/sdk/references/manifest/

## Current high-level rules

- `SDKVersion` supports `2` or `3`; Elgato currently recommends `3`.
- `Nodejs.Version` supports `"20"` or `"24"`.
- Current new-development guidance uses Node.js 24+ and Stream Deck 7.1+.
- Action controllers are `"Keypad"`, `"Encoder"`, and/or `"Neo"`.
- `"Neo"` targets the Stream Deck Neo infobar and requires Stream Deck 7.6 or later.
- Action UUIDs must be prefixed by the plugin UUID.
- Published plugin/action UUIDs should never change.
- Action UUID characters are lowercase alphanumeric, hyphen, and period.
- Keep file path extensions exactly as the schema/reference requires. Many image fields omit extensions; `CodePath` and `PropertyInspectorPath` include extensions.

## Minimal current-generation shape

Do not blindly copy this over an existing manifest; preserve project compatibility and fields.

```json
{
  "$schema": "https://schemas.elgato.com/streamdeck/plugins/manifest.json",
  "Actions": [],
  "Author": "Example",
  "CodePath": "bin/plugin.js",
  "Description": "Example Stream Deck plugin.",
  "Icon": "imgs/plugin-icon",
  "Name": "Example",
  "Nodejs": {
    "Version": "24"
  },
  "OS": [
    { "Platform": "mac", "MinimumVersion": "13" },
    { "Platform": "windows", "MinimumVersion": "10" }
  ],
  "SDKVersion": 3,
  "Software": {
    "MinimumVersion": "7.1"
  },
  "UUID": "com.example.plugin",
  "Version": "1.0.0.0"
}
```

The OS values above are illustrative, not universal requirements. Choose OS minimums based on the plugin's actual dependencies and requirements.

## Actions

Typical action metadata includes:

```json
{
  "Name": "Example Action",
  "UUID": "com.example.plugin.example-action",
  "Icon": "imgs/actions/example/action-icon",
  "Tooltip": "Does an example thing.",
  "Controllers": ["Keypad"],
  "States": [
    {
      "Image": "imgs/actions/example/key"
    }
  ]
}
```

For an action supporting dials:

```json
{
  "Controllers": ["Keypad", "Encoder"],
  "Encoder": {
    "layout": "$B1"
  }
}
```

For a Neo infobar action, declare `"Controllers": ["Neo"]` and set
`Software.MinimumVersion` to at least `"7.6"`. Use the action state image and shared
lifecycle contract; do not add invented Neo-specific metadata or input handlers.

Current built-in layout IDs accepted by the manifest are:

- `$X1`
- `$A0`
- `$A1`
- `$B1`
- `$B2`
- `$C1`

## Property inspector paths

A PI can be defined globally at manifest root or per action via `PropertyInspectorPath`.

Action-level PI path overrides the top-level PI path.

Paths are relative to the plugin root, have no leading slash, and include `.html`/`.htm`.

## Support URL

`SupportURL` is available at plugin and action level. Action-level support can override the plugin-level destination.

## Device profile types

Current manifest `Profiles[].DeviceType` values are 0 through 13. See `devices-profiles.md` for the mapping.

## Newer action metadata

Current schema includes fields such as:

- `SupportedInKeyLogicActions`
- `SupportedInMultiActions`
- `VisibleInActionsList`
- action-level `OS`
- action-level `SupportURL`

Use the schema rather than guessing availability/minimum versions.

## DRM note

DRM protection requires:

- `@elgato/streamdeck` v2 or higher for Node.js plugins.
- `SDKVersion: 3`.
- `Software.MinimumVersion: "6.9"` or higher.

For new Node 24-based plugins, the Node runtime requirement may already imply a higher Stream Deck minimum (7.1+).

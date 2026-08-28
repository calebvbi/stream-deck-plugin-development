# Property Inspectors and sdpi-components

Official Stream Deck guide: https://docs.elgato.com/streamdeck/sdk/guides/ui/
Official PI component library: https://sdpi-components.dev/

## Default approach

For a standard Stream Deck property inspector, prefer Elgato's `sdpi-components` UI library unless the repository already uses another established PI stack or the feature genuinely requires custom UI.

Do not use invented packages or old legacy PI libraries.

Do not manually implement the raw Stream Deck property-inspector WebSocket registration protocol unless there is a specific low-level need that `sdpi-components` cannot satisfy.

## Local library is recommended

For a distributable plugin, bundle `sdpi-components.js` locally beside/within the plugin's PI resources:

```html
<!doctype html>
<html>
<head lang="en">
    <meta charset="utf-8" />
    <script src="sdpi-components.js"></script>
</head>
<body>
    <sdpi-item label="Name">
        <sdpi-textfield setting="name"></sdpi-textfield>
    </sdpi-item>
</body>
</html>
```

Do not load executable Property Inspector code from a mutable remote URL, including during prototyping. Bundle the exact reviewed library file locally so development and packaged behavior use the same dependency.

Before packaging, verify that the PI's static resource graph closes inside the bundle:

```bash
python3 <skill-root>/scripts/bundle_self_containment.py \
  <plugin-uuid>.sdPlugin
```

The verifier follows manifest-declared PI HTML, load-bearing HTML resources, CSS imports and URLs, and static JavaScript module imports. It fails on remote executable/UI resources, missing files, unsafe or escaping paths, symlinks, and case mismatches. It intentionally does not reject runtime `fetch`, XHR, WebSocket, OAuth, or `openUrl` destinations. Treat this as static package evidence; it does not prove the PI loaded or behaved correctly in Stream Deck.

## Automatic settings persistence

Most input components support `setting="path"`, which automatically persists their value.

Example:

```html
<sdpi-item label="Brightness">
    <sdpi-range setting="brightness" min="0" max="100" step="1" showlabels></sdpi-range>
</sdpi-item>
```

Nested settings are supported with dotted paths such as `audio.output.volume`.

Add the `global` attribute when a supported component should persist to global settings instead of action settings.

## Common components

Current official components include:

- `<sdpi-item>`
- `<sdpi-button>`
- `<sdpi-calendar>`
- `<sdpi-checkbox>`
- `<sdpi-checkbox-list>`
- `<sdpi-color>`
- `<sdpi-delegate>`
- `<sdpi-file>`
- `<sdpi-i18n>`
- `<sdpi-password>`
- `<sdpi-radio>`
- `<sdpi-range>`
- `<sdpi-select>`
- `<sdpi-textarea>`
- `<sdpi-textfield>`

Check https://sdpi-components.dev/ for exact current attributes and component behavior.

## Dynamic data sources

`sdpi-select`, `sdpi-radio`, and `sdpi-checkbox-list` support `datasource` for options supplied by the plugin.

Example:

```html
<sdpi-select
    setting="deviceId"
    datasource="getDevices"
    loading="Fetching devices..."
    hot-reload
    show-refresh>
</sdpi-select>
```

The PI requests the data using `sendToPlugin`; the plugin responds via `sendToPropertyInspector` using the documented payload structure. Use the official data-source helper docs instead of inventing a custom protocol when this pattern fits.

## Stream Deck client

For PI operations not covered by automatic component persistence, use:

```js
const streamDeckClient = SDPIComponents.streamDeckClient;
```

It provides documented helpers for:

- getting/setting action settings
- getting/setting global settings
- receiving settings changes
- receiving plugin messages
- sending messages to the plugin
- opening URLs
- reading PI connection information

## Localization

`sdpi-components` has its own localization helper. Define locales on `SDPIComponents.i18n.locales` and use `__MSG_key__` placeholders or `<sdpi-i18n>`.

This is separate from the plugin/action manifest localization files used elsewhere by Stream Deck.

## Marketplace PI requirements

Property inspectors should:

- use checkboxes for boolean values
- use select/radio for single-choice values
- show validation feedback
- automatically save action settings on change
- provide setup/help links where needed
- avoid an ordinary Save button for action settings
- avoid cramped, overly complex configuration
- avoid large paragraphs when space should be reserved for controls

If one HTML file serves multiple actions, hide irrelevant UI by default and reveal only the necessary controls to avoid flicker.

## Debugging

Enable developer mode:

```bash
streamdeck dev
```

If you enabled developer mode for the task and it was previously disabled, restore it
with `streamdeck dev --disable` after collecting evidence.

Then PI debugging is available through Stream Deck's local developer tooling at:

```text
http://localhost:23654/
```

Current Stream Deck versions also include in-app developer tools that track the active property inspector.

# Keys

Official guide: https://docs.elgato.com/streamdeck/sdk/guides/keys/

## Input events

Key actions use:

- `onKeyDown`
- `onKeyUp`

Do not use dial handlers for key-only actions.

## Visual methods

Key action instances can update visuals with methods such as:

- `setTitle(...)`
- `setImage(...)`
- `setState(...)` where applicable
- `showOk()`
- `showAlert()`

Consult installed SDK types for exact options/signatures.

## Images

`setImage` accepts a plugin-local path, data URL, or SVG string. When using `ImageOptions`, keys can target hardware/software and a specific state.

User-customized titles/images have higher display precedence than values set by the plugin. Runtime values then take precedence over manifest defaults.

## States

All key actions require at least one state in the manifest. Stream Deck fully supports up to two key states.

Do not create a multi-state architecture that relies on more than two native manifest states. Represent more complex state in plugin data/settings and render it yourself.

## Rendering rate

Keys are not intended for high-frame-rate video. For programmatic animation, use the
ownership, rate, cancellation, and backpressure gates in `animation-runtime.md` and
the Marketplace limit summarized in `plugin-guidelines.md`.

## Key icon assets

Marketplace guidance:

- Static key state images: SVG, PNG, or GIF.
- Raster target size: 72×72px plus 144×144px high-DPI variant.
- SVG is recommended where appropriate for scaling and dynamic visuals.
- For programmatic raster updates, provide the higher-DPI size and let Stream Deck scale down.

Animated GIFs may be specified in the manifest but are not the mechanism for programmatic image updates.

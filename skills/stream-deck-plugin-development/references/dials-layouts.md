# Dials and Touch Strip Layouts

Official guide: https://docs.elgato.com/streamdeck/sdk/guides/dials/
Layout schema/reference: https://docs.elgato.com/streamdeck/sdk/references/touch-strip-layout/

## Encoder model

A dial action consists of a physical dial plus an associated region of the touch display. In the manifest, dial support is declared with the `"Encoder"` controller.

## Current dial/touch events

Use:

- `onDialDown`
- `onDialRotate`
- `onDialUp`
- `onTouchTap`

Do not use `dialPress`. Stream Deck 6.5 removed `dialPress` in favor of dial down/up events.

## Built-in layouts

Current built-in layout IDs:

- `$X1` — Icon
- `$A0` — Canvas
- `$A1` — Value
- `$B1` — Indicator
- `$B2` — Gradient indicator
- `$C1` — Double indicator

Prefer a built-in layout when it fits. Use a custom JSON layout when necessary.

## Custom layout canvas

Touch-strip action layouts use a 200×100px coordinate space.

All layout items must stay within the layout bounds or the layout can fail to load.

Interactive touch targets should be at least 35×35px per Marketplace guidance.

## Setting/updating layouts

A default layout can be declared in the action's manifest `Encoder.layout`.

At runtime:

```ts
await ev.action.setFeedbackLayout("$B1");
await ev.action.setFeedback({
    title: "Volume",
    indicator: { value: 50 }
});
```

`setFeedback` updates layout items by their `key`. Fields not included in the update remain unchanged.

Reserved keys such as `title` and `icon` can be affected by user customization, so do not assume your plugin always has final display precedence.

## Trigger descriptions

Encoder metadata can describe behaviors such as push, rotate, touch, and long touch. Runtime trigger descriptions can also be updated through the SDK where supported.

## Rendering rate

Touch strips are not intended for high-frame-rate rendering. Prefer partial feedback
updates, and use the ownership, rate, cancellation, and backpressure gates in
`animation-runtime.md` plus the Marketplace limit in `plugin-guidelines.md`.

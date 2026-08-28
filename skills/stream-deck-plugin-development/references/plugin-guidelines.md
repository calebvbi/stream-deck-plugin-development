# Stream Deck Plugin Guidelines

Official current guidelines: https://docs.elgato.com/guidelines/stream-deck/plugins/

Use these for Marketplace-facing metadata and UX. When guidelines change, the live page wins.

## UUIDs

- Plugin UUID should identify organization/author and plugin.
- Action UUIDs must be prefixed by the plugin UUID.
- Never change published UUIDs.
- For deprecated actions, prefer keeping the UUID and hiding the old action with `VisibleInActionsList: false` rather than replacing its identity.

## Naming/actions

- Use concise descriptive action names, approximately 30 characters or less.
- Category should match or closely resemble plugin name.
- Prefer configurable actions over many static variants.
- Consolidate actions that share settings when doing so creates a clearer configurable action.
- Marketplace guidance recommends a reasonable action count, roughly 2–30.

## Plugin icon

Plugin icon shown in preferences/Marketplace metadata:

- PNG.
- 256×256px and 512×512px high-DPI.

## Action-list icons

Category/action list icons:

- SVG or PNG.
- SVG recommended.
- Monochromatic with transparent background.
- White foreground/stroke `#FFFFFF`.
- Category raster: 28×28px and 56×56px high-DPI.
- Action raster: 20×20px and 40×40px high-DPI.
- Do not use colored or solid-background action-list icons.

## Key icons

- SVG, PNG, or GIF.
- Raster: 72×72px and 144×144px high-DPI.
- Use states to reflect meaningful state changes.
- Programmatic key rendering: maximum 10 updates per second.

## Dials/touch strip

- Layout canvas: 200×100px.
- Keep items inside bounds.
- Interactive touch targets should be at least 35×35px.
- Prefer built-in layouts when suitable.
- Prefer partial layout updates.
- Programmatic touch-strip rendering: maximum 10 updates per second.

## Temporary feedback

- Use `showAlert` for unsuccessful operations and accompany it with useful logging.
- Use `showOk` for success when there is no other persistent visual confirmation.
- Avoid redundant `showOk` when the action's visual state already confirms success.

## Property inspectors

Requirements/recommendations include:

- checkbox for boolean settings
- select/radio for single-select settings
- validation feedback
- automatically save action settings on change
- support/setup links where needed
- no ordinary Save button for action settings
- avoid donation/sponsor/copyright content in PI; use Marketplace product metadata/additional links instead
- hide irrelevant components initially if a shared PI would otherwise flicker
- avoid overly complex control density and long paragraphs

Use `sdpi-components` as the standard implementation path for these controls unless the project has an established alternative.

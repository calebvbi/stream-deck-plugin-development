# Actions and Shared Events

Official guide: https://docs.elgato.com/streamdeck/sdk/guides/actions/

## Action model

Actions are implemented as classes derived from `SingletonAction` and identified with the `@action` decorator.

```ts
import { action, type KeyDownEvent, SingletonAction } from "@elgato/streamdeck";

@action({ UUID: "com.example.plugin.example" })
export class ExampleAction extends SingletonAction {
    override async onKeyDown(ev: KeyDownEvent): Promise<void> {
        await ev.action.setTitle("Hello");
    }
}
```

Keep the decorator UUID identical to the manifest action UUID.

## Registration order

```ts
import streamDeck from "@elgato/streamdeck";
import { ExampleAction } from "./actions/example";

streamDeck.actions.registerAction(new ExampleAction());
streamDeck.connect();
```

Register all plugin actions before connecting. As a general rule, call `streamDeck.connect()` last in the entry file.

## Controllers

The live manifest exposes three controller surfaces:

- Key: `"Keypad"` in the manifest. Includes standard LCD keys, pedals, G-Keys, etc.
- Dial: `"Encoder"` in the manifest. Includes a dial plus its associated touch-display region.
- Infobar: `"Neo"` in the manifest. Targets the Stream Deck Neo infobar and is available from Stream Deck 7.6.

Do not assume every action instance supports both.

Current official input-event documentation still assigns key events to `Keypad` and
dial/touch events to `Encoder`. Shared lifecycle payloads can report `Neo`. Treat Neo
as a separate visual surface, narrow on the actual controller, and use the installed
SDK types rather than assuming key or dial input methods apply.

## Shared lifecycle/events

Common action lifecycle behavior includes `onWillAppear`, `onWillDisappear`, settings changes, PI visibility/messages, and controller-specific input events.

Use the event/action object's actual TypeScript type to determine available methods. For handlers shared across controller types, narrow with SDK helpers such as `Action.isKey()` before calling key-only methods.

## Settings

Per-action settings can be read from event payloads or via the visible action instance and written with `ev.action.setSettings(...)`.

Use `SingletonAction<Settings>` to type action settings.

## PI messaging

Use SDK PI messaging APIs rather than implementing the raw Stream Deck WebSocket protocol for normal Node.js plugin work.

Use PI messages for data that is not simply a persisted setting, such as requesting a dynamic data source or invoking an operation.

## Global SDK namespaces

The default `streamDeck` object exposes services for actions, devices, settings, profiles, system behavior, logging, and property-inspector communication. Use the installed SDK's types as the authoritative API surface.

## Temporary feedback

For failures, use `showAlert()` where appropriate and log the underlying problem. Use `showOk()` only when a success indicator is useful and not already obvious from the action's persistent visual state.

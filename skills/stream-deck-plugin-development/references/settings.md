# Settings

Official guide: https://docs.elgato.com/streamdeck/sdk/guides/settings/

There are two settings scopes:

- Action settings: belong to one action instance.
- Global settings: plugin-wide.

Both are persisted as JSON-compatible objects.

## Action settings

Use action settings for configuration/state that belongs to an individual action instance.

```ts
await ev.action.setSettings({ count: 1 });
```

Read from event payloads when available or with `getSettings()` while the action is visible.

Use a typed action:

```ts
type Settings = {
    count?: number;
};

class Counter extends SingletonAction<Settings> {
    // ...
}
```

Important security behavior:

- Action settings are plain text.
- Action settings are included when exporting profiles/actions.
- Never store credentials/tokens in action settings.

## Global settings

Use global settings for plugin-wide values and user-specific credentials/tokens when local storage is acceptable.

```ts
await streamDeck.settings.setGlobalSettings({ token });
const settings = await streamDeck.settings.getGlobalSettings<MyGlobalSettings>();
```

Global settings are stored securely on the user's local machine, but the user can still access them. Therefore:

- Good: user-provided API tokens/OAuth tokens.
- Good: plugin-wide preferences.
- Bad: private developer/service secrets that must remain unknown to users.

Do not ship private service credentials inside the plugin package either.

## Change notifications

The plugin and active property inspector are notified when the adjacent side updates settings. Use SDK settings events rather than polling settings.

## Property inspectors

When using `sdpi-components`, the `setting` attribute can automatically persist component values to action settings; `global` changes the persistence target to global settings.

Do not add a Save button for normal action settings. Marketplace PI guidance requires action settings to save automatically on change.

# Devices and Profiles

Official device guide: https://docs.elgato.com/streamdeck/sdk/guides/devices/
Official profile guide: https://docs.elgato.com/streamdeck/sdk/guides/profiles/

## Current device type mapping

As of 2026-08-26:

| Value | Device |
|---:|---|
| 0 | Stream Deck / Stream Deck Scissor Keys |
| 1 | Stream Deck Mini |
| 2 | Stream Deck XL |
| 3 | Stream Deck Mobile |
| 4 | Corsair GKeys |
| 5 | Stream Deck Pedal |
| 6 | Corsair Voyager |
| 7 | Stream Deck + |
| 8 | SCUF Controller |
| 9 | Stream Deck Neo |
| 10 | Stream Deck Studio |
| 11 | Virtual Stream Deck |
| 12 | Galleon 100 SD |
| 13 | Stream Deck + XL |

Do not hard-code an old 0-11 mapping.

## Device events

Use the SDK device manager to observe:

- `onDeviceDidConnect`
- `onDeviceDidChange`
- `onDeviceDidDisconnect`

`onDeviceDidChange` is available from Stream Deck 7.0 and can report metadata/size changes.

Use the device data supplied by the SDK rather than inferring behavior solely from model names.

## Controller capability

Declare actions by controller surface (`Keypad`, `Encoder`, or `Neo`) rather than targeting individual hardware models whenever possible.

When behavior truly depends on hardware capability, inspect the actual action/device/controller context and degrade gracefully.

Do not conflate device and controller availability. Stream Deck 6.6 added device
support for Stream Deck Neo (`DeviceType: 9`), while the manifest's `Neo` infobar
controller is documented as available from Stream Deck 7.6.

## Profiles

Plugins may distribute pre-defined `.streamDeckProfile` files and declare them in the manifest.

Important limitations:

- Plugins can switch only to profiles bundled with the plugin and declared in the manifest.
- Plugins cannot access or switch to arbitrary user-defined profiles.
- Manifest `Profiles[].Name` is the profile path/name without the `.streamDeckProfile` extension.
- `AutoInstall` defaults to `true`; when false, installation is deferred until the plugin first attempts to switch to the bundled profile.

Use `streamDeck.profiles.switchToProfile(...)` according to installed SDK types.

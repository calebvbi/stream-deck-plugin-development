# Contributing

Contributions that improve portable Stream Deck development guidance are welcome.

## Before opening a pull request

1. Keep `SKILL.md` concise and route detailed guidance to the smallest relevant file under `references/`.
2. Base version-sensitive claims on current official Elgato documentation, schemas, changelogs, or installed SDK types.
3. Preserve existing-project compatibility guidance. Do not silently replace it with the newest development floor.
4. Keep examples generic. Remove private paths, credentials, customer data, device identities, unpublished project names, and generated evaluation receipts.
5. Run `python3 scripts/validate_publication.py` and include the exact result in the pull request.

Bundled helpers must remain portable, read-only by default, standard-library-only, and explicit about any output they write. Avoid duplicating long guidance across `SKILL.md` and references.

For platform behavior changes, state which evidence layer was checked. Static or package validation must not be presented as installed-runtime or physical-hardware proof.

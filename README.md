# Stream Deck Plugin Development

[![Validate](https://github.com/calebvbi/stream-deck-plugin-development/actions/workflows/validate.yml/badge.svg)](https://github.com/calebvbi/stream-deck-plugin-development/actions/workflows/validate.yml)

An independent Agent Skill for creating, maintaining, testing, troubleshooting, and packaging Elgato Stream Deck plugins built with the official Node.js SDK.

The skill routes an AI agent to focused guidance for manifests, actions, keys, dials, Neo, Property Inspectors, settings, profiles, animation, troubleshooting, package validation, and evidence-based QA. It preserves an existing plugin's compatibility floor unless a requested change requires otherwise.

## Install

Install the skill from GitHub with the [`skills`](https://skills.sh/) CLI:

```bash
npx --yes skills@1.5.23 add \
  https://github.com/calebvbi/stream-deck-plugin-development/tree/v0.1.0-rc.3 \
  --skill stream-deck-plugin-development
```

Install globally for selected agents:

```bash
npx --yes skills@1.5.23 add \
  https://github.com/calebvbi/stream-deck-plugin-development/tree/v0.1.0-rc.3 \
  --skill stream-deck-plugin-development \
  --agent claude-code cursor codex grok \
  --global
```

You can also copy `skills/stream-deck-plugin-development` into an Agent Skills directory supported by your agent.

## Use

Ask your agent to use `stream-deck-plugin-development`, or make an ordinary Stream Deck request such as:

- Create a Stream Deck plugin with a key action, dial action, and Property Inspector.
- Diagnose why this existing plugin does not load.
- Add bounded animation that stops cleanly when an action disappears.
- Validate and package this plugin for distribution.

The agent should inspect the target project before making compatibility decisions, load only the references relevant to the task, and keep source, package, installed-runtime, simulated-input, and physical-hardware evidence separate.

## Requirements

- An AI agent or IDE that supports the Agent Skills format.
- Python 3.10 or newer to run the three bundled, standard-library-only helpers.
- The Stream Deck CLI, Stream Deck desktop app, and physical hardware only when the requested validation requires them.
- Node.js and Stream Deck versions appropriate to the plugin being created or maintained.

## Portable skill structure

```text
skills/stream-deck-plugin-development/
├── SKILL.md
├── references/
└── scripts/
```

The payload has no vendor-specific frontmatter, private paths, credentials, network-dependent helpers, or hidden local dependencies. The helpers inspect a selected project, create a QA matrix, and verify Property Inspector resource self-containment.

## Validate a checkout

```bash
python3 scripts/validate_publication.py
npx --yes skills@1.5.23 add . --list
```

The publication validator checks the repository allowlist, skill frontmatter, topic routing, relative links, Python syntax, helper entry points, accidental private paths, common secret formats, generated files, and duplicate long-form context.

## Compatibility status

- Clean explicit and organic discovery has been tested in Codex and Claude Code.
- The portable structure is intended for other Agent Skills clients, including Cursor and Grok, but those environments are not yet certified by this project.
- Static and package checks do not prove installed Stream Deck behavior or physical-device behavior. Require causal runtime evidence when the task depends on it.
- Version-sensitive platform guidance should be rechecked against the official sources routed by the skill before a release.

## Support and security

Use [GitHub Issues](https://github.com/calebvbi/stream-deck-plugin-development/issues) for reproducible bugs and documentation problems. Use [private vulnerability reporting](https://github.com/calebvbi/stream-deck-plugin-development/security/advisories/new) for security-sensitive reports. Do not include credentials, private paths, customer data, or unpublished plugin packages in a public issue.

See [SUPPORT.md](SUPPORT.md), [SECURITY.md](SECURITY.md), and [CONTRIBUTING.md](CONTRIBUTING.md) before reporting or proposing a change.

## License and trademarks

The repository is available under the [MIT License](LICENSE).

Stream Deck and Elgato are trademarks of Corsair Memory, Inc. This independent community project is not affiliated with or endorsed by Elgato, Corsair, OpenAI, Anthropic, Cursor, or xAI. Product names identify compatibility targets only.

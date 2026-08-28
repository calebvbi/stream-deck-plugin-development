# Security Policy

## Supported versions

Security fixes are provided for the latest published prerelease or stable version. Older prereleases are not maintained.

## Report a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/calebvbi/stream-deck-plugin-development/security/advisories/new). Do not disclose a suspected vulnerability in a public issue.

Include the affected skill version, relevant file or helper, impact, reproduction steps, and a minimal sanitized example. Remove credentials, tokens, customer data, private paths, unpublished plugin packages, device identifiers, and proprietary source.

## Security boundaries

The bundled helpers use only the Python standard library and make no network requests. They do not install dependencies or execute project build commands. `inspect_project.py` reads project metadata, `qa_matrix.py` can call local Git commands for repository identity, and `bundle_self_containment.py` walks manifest-referenced Property Inspector resources.

The helpers write only to caller-selected output paths and refuse silent overwrites. Their output can still contain repository identities, hashes, manifest data, paths supplied by the caller, and device or action metadata. Review generated output before sharing it.

An Agent Skill guides an AI agent but is not a security sandbox. Review generated commands and code before execution, protect developer and service secrets, and verify the exact packaged artifact before installation or distribution.

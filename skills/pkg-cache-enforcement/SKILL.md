---
name: pkg-cache-enforcement
description: Ensure every network download in Forgejo composite actions uses the inherited PKG_CACHE mirror when available.
vendor_neutral: true
version: 1.0.0
triggers:
  - "create a new action"
  - "add a download"
  - "add an installer"
  - "review pkg-cache usage"
  - "check mirror support"
inputs:
  action_name:
    type: string
    description: Action or action directory being created or reviewed.
    required: false
---

# Package Cache Enforcement Skill

Use this skill for every new action, installer, scanner, downloader, or code
review that can access the network. The repository-wide contract is that
downloads use the inherited `PKG_CACHE` environment value whenever it is set.
`setup-cache` is responsible for detecting and exporting `PKG_CACHE`; consumer
actions must not add their own detection steps or reintroduce a `pkg_cache`
input.

## Required procedure

1. Search the action and its scripts for all network access:
   `curl`, `wget`, `python`/`urllib`/`requests`, Node HTTP clients, package
   managers, release APIs, archive URLs, and shell subprocesses.
2. For each download, identify the upstream host and use the corresponding
   `PKG_CACHE` path when the mirror supports that host.
3. Read `PKG_CACHE` from the environment, normalize it by adding `https://`
   when no scheme is present and removing trailing slashes, and fall back to
   the official upstream URL when it is empty.
4. Pass `PKG_CACHE` through `env:` for inline shell steps. Do not interpolate
   untrusted values directly into shell code.
5. For Python scripts, read `os.environ["PKG_CACHE"]` (or an explicit empty
   default) and centralize URL construction in a helper rather than duplicating
   string replacements.
6. Preserve paths expected by the configured reverse proxy. For example:
   `https://<cache>/github.com/<owner>/<repo>`,
   `https://<cache>/nodejs.org`, and
   `https://<cache>/registry.npmjs.org/`.
7. Keep authentication credentials out of mirror URLs. Use existing token or
   header mechanisms and never commit secrets.
8. Document in the action README which downloads use the mirror and that
   official endpoints are used when `PKG_CACHE` is unset.

## Review checklist

- No new `pkg_cache` action input is added.
- No consumer action independently runs `detect-pkg-cache`.
- Every `curl`/`wget` URL is mirror-aware.
- Every Python/Node HTTP request is mirror-aware or explicitly documented as
  an API that the mirror cannot proxy.
- Package-manager registry or repository configuration uses `PKG_CACHE`.
- Empty `PKG_CACHE` remains a supported official-source fallback.
- `setup-cache` remains the only automatic detection/setup action.
- Tests or syntax checks cover URL construction and the empty-cache path when
  the action has non-trivial download logic.

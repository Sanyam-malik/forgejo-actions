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

Apply this skill whenever an action performs network access. Every `curl`,
`wget`, Python/urllib/requests call, Node HTTP request, package-manager
download, release API, or archive download must use the inherited `PKG_CACHE`
environment value when the configured mirror supports that upstream host.

`setup-cache` is the only action that detects and exports `PKG_CACHE`.
Consumers must read the environment value, must not add a `pkg_cache` input or
their own detection step, and must fall back to the official endpoint when it
is empty. Normalize the value with an `https://` scheme and no trailing slash,
preserve the reverse-proxy path for the upstream host, and keep credentials
out of URLs.

Before completing a change, search all scripts for network access, verify each
URL construction path, pass `PKG_CACHE` through `env:` for shell steps, use
`os.environ` in Python, document mirror behavior in the action README, and
check both configured-mirror and empty-mirror behavior when download logic is
non-trivial.

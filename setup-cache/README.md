# Setup Package Cache

Configure system package repositories and establish the shared `PKG_CACHE`
environment variable for subsequent actions.

## Usage

```yaml
steps:
  - name: Setup Package Cache
    id: setup-cache
    uses: your-org/forgejo-actions/setup-cache@v1
```

To override automatic detection, set `PKG_CACHE` in the job environment before
this action runs:

```yaml
env:
  PKG_CACHE: https://pkg-cache.example.com
```

## Inputs

This action has no inputs. It uses an existing `PKG_CACHE` environment value
when present; otherwise it derives `https://pkg-cache.<root-domain>` from
`github.server_url`.

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Normalizes the cache value with an `https://` scheme and no trailing slash.
- Rewrites supported APT, DNF/YUM, APK, and Zypper repositories through the
  normalized cache URL.
- Exports the normalized value as `PKG_CACHE` through `GITHUB_ENV` so all
  following actions inherit it.
- Consumers fall back to official sources when `PKG_CACHE` is unset.

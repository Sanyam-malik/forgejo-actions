# Setup Package Cache

Rewrite system package repositories to use a package cache

## Usage

```yaml
steps:
  - name: Setup Package Cache
    id: setup-cache
    uses: your-org/forgejo-actions/setup-cache@v1
    with:
      pkg_cache: https://pkg-cache.example.com
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `pkg_cache` | Package cache host or base URL | Yes | — |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- `pkg_cache` is required and identifies the package-cache host or base URL to configure.

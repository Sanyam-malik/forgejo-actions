# Setup Hugo

Install Hugo Extended with inherited PKG_CACHE mirror support

## Usage

```yaml
steps:
  - name: Setup Hugo
    id: setup-hugo
    uses: your-org/forgejo-actions/setup-hugo@v1
    with:
      hugo_version: 0.146.0
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `hugo_version` | Hugo version | Yes | — |

## Behavior and requirements

- Reads the inherited `PKG_CACHE` environment variable for mirror access when it is set; otherwise uses official sources. Run `setup-cache` once to derive and export it, or set `PKG_CACHE` explicitly as a job environment override.

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.

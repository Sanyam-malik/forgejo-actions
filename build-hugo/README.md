# Build Hugo Site

Build Hugo static website

## Usage

```yaml
steps:
  - name: Build Hugo Site
    id: build-hugo
    uses: your-org/forgejo-actions/build-hugo@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `working_dir` | Directory containing Hugo site | No | `.` |
| `base_url` | Hugo base URL | No | `/` |
| `output_dir` | Custom output directory (optional) | No | `""` |

## Outputs

| Name | Description |
| --- | --- |
| `output_dir` | Hugo build output directory |

## Behavior and requirements

- Reads the inherited `PKG_CACHE` environment variable for mirror access when it is set; otherwise uses official sources. Run `setup-cache` once to derive and export it, or set `PKG_CACHE` explicitly as a job environment override.

- Runs as a vendor-neutral composite action on the current CI runner.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

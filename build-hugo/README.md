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
| `pkg_cache` | Package cache host or base URL | No | `""` |

## Outputs

| Name | Description |
| --- | --- |
| `output_dir` | Hugo build output directory |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- `pkg_cache` is optional; leave it empty to use the action's default package or download source, or set it to a compatible mirror.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

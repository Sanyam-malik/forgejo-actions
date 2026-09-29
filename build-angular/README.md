# Build Angular Application

Install dependencies and build Angular project

## Usage

```yaml
steps:
  - name: Build Angular Application
    id: build-angular
    uses: your-org/forgejo-actions/build-angular@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `working_dir` | Directory containing Angular project | No | `.` |
| `base_href` | Angular base href | No | `/` |
| `build_configuration` | Angular build configuration | No | `production` |
| `force_install` | Force npm dependency installation | No | `false` |
| `output_dir` | Custom output directory (optional) | No | `""` |

## Outputs

| Name | Description |
| --- | --- |
| `output_dir` | Angular build output directory |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

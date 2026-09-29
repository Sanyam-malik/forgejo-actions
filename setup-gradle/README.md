# Setup Gradle

Install Gradle optionally using pkg-cache mirror

## Usage

```yaml
steps:
  - name: Setup Gradle
    id: setup-gradle
    uses: your-org/forgejo-actions/setup-gradle@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `pkg_cache` | Package cache host or base URL | No | `""` |
| `gradle_version` | Gradle version (use 'latest' for current release) | No | `latest` |

## Outputs

| Name | Description |
| --- | --- |
| `gradle_version` | Installed Gradle version |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- `pkg_cache` is optional; leave it empty to use the action's default package or download source, or set it to a compatible mirror.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

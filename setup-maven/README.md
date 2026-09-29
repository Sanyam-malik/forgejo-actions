# Setup Maven

Install Maven with optional pkg-cache mirror

## Usage

```yaml
steps:
  - name: Setup Maven
    id: setup-maven
    uses: your-org/forgejo-actions/setup-maven@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `pkg_cache` | Package cache host or base URL (reverse proxy cache) | No | `""` |
| `maven_version` | Maven version (use 'latest' for current stable release) | No | `latest` |

## Outputs

| Name | Description |
| --- | --- |
| `maven_version` | Installed Maven version |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- `pkg_cache` is optional; leave it empty to use the action's default package or download source, or set it to a compatible mirror.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

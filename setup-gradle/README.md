# Setup Gradle

Install Gradle using inherited PKG_CACHE mirror support

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
| `gradle_version` | Gradle version (use 'latest' for current release) | No | `latest` |

## Outputs

| Name | Description |
| --- | --- |
| `gradle_version` | Installed Gradle version |

## Behavior and requirements

- Reads the inherited `PKG_CACHE` environment variable for mirror access when it is set; otherwise uses official sources. Run `setup-cache` once to derive and export it, or set `PKG_CACHE` explicitly as a job environment override.

- Runs as a vendor-neutral composite action on the current CI runner.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

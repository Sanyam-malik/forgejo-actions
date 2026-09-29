# Publish Maven Package

Publish Gradle or Maven artifacts to a Maven registry

## Usage

```yaml
steps:
  - name: Publish Maven Package
    id: publish-maven
    uses: your-org/forgejo-actions/publish-maven@v1
    with:
      registry: registry.example.com
      user: ci-user
      token: ${{ secrets.ACTION_TOKEN }}
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `registry` | Registry hostname | Yes | — |
| `user` | Registry username | Yes | — |
| `token` | Registry token | Yes | — |
| `build_tool` | Build tool (gradle \| maven) | No | `gradle` |

## Outputs

| Name | Description |
| --- | --- |
| `package_url` | Maven repository URL |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

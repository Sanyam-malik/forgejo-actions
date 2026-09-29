# Forgejo Link Package

Link container package to repository

## Usage

```yaml
steps:
  - name: Forgejo Link Package
    id: link-docker-image
    uses: your-org/forgejo-actions/link-docker-image@v1
    with:
      registry_api: https://forgejo.example.com/api/v1
      namespace: team
      image: example-app
      username: ci-user
      token: ${{ secrets.ACTION_TOKEN }}
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `registry_api` | Forgejo registry API endpoint | Yes | — |
| `namespace` | Namespace | Yes | — |
| `image` | Image name | Yes | — |
| `username` | Forgejo username | Yes | — |
| `token` | Forgejo token | Yes | — |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- API operations require a compatible server endpoint and a token with sufficient permissions when authentication is needed.

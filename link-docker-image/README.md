# Forgejo Link Docker Image

Link a Forgejo container package to the current repository.

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
- `registry_api` must be the Forgejo API base URL, normally ending in `/api/v1`.
- The package is linked to the repository identified by `GITHUB_REPOSITORY`.
- When the namespace and image name match the repository owner and name (including nested image names such as `repository/service`), the action skips the legacy link API because Forgejo auto-links those images when the package is first created.
- Package, namespace, and repository names are URL-encoded before the API request, so names containing special characters are handled safely.
- The action uses Forgejo's package-link endpoint and treats HTTP `200`, `201`, and `204` as successful outcomes. For other responses, the API message is checked for an explicit already-linked/already-associated condition so duplicate links remain idempotent across Forgejo versions.
- API errors fail the action and include the server response when one is returned.
- Works with Forgejo versions that return any of the supported successful status codes.

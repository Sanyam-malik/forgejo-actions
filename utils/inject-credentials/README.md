# Inject Artifact Credentials

Replace artifact URL and token placeholders in a file

## Usage

```yaml
steps:
  - name: Inject Artifact Credentials
    id: inject-credentials
    uses: your-org/forgejo-actions/utils/inject-credentials@v1
    with:
      file: path/to/file
      artifact_url_placeholder: __ARTIFACT_URL__
      artifact_token_placeholder: __ARTIFACT_TOKEN__
      artifact_url: https://artifacts.example.com
      artifact_token: ${{ secrets.ARTIFACT_TOKEN }}
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `file` | File to update | Yes | — |
| `artifact_url_placeholder` | Placeholder for artifact URL | Yes | — |
| `artifact_token_placeholder` | Placeholder for artifact token | Yes | — |
| `artifact_url` | Artifact repository URL | Yes | — |
| `artifact_token` | Artifact access token | Yes | — |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.

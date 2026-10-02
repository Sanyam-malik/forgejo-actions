# Docker Push

Load an OCI image tarball and push the image to a registry

## Usage

```yaml
steps:
  - name: Docker Push
    id: docker-push
    uses: your-org/forgejo-actions/docker-push@v1
    with:
      registry: registry.example.com
      namespace: team
      image: example-app
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `registry` | Registry URL | Yes | — |
| `namespace` | Registry namespace | Yes | — |
| `image` | Image name | Yes | — |
| `tags` | Comma-separated image tags | No | `latest` |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- Docker operations require a runner with Docker and the permissions needed to build, load, log in, or push images as applicable.
- Set `tags` to one tag (`latest`) or multiple comma-separated tags (`1.2.3,latest`); each tag is pushed separately.

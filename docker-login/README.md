# Docker Login

Login to Docker / Forgejo container registry

## Usage

```yaml
steps:
  - name: Docker Login
    id: docker-login
    uses: your-org/forgejo-actions/docker-login@v1
    with:
      registry: registry.example.com
      username: ci-user
      token: ${{ secrets.ACTION_TOKEN }}
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `registry` | Container registry URL | Yes | — |
| `username` | Registry username | Yes | — |
| `token` | Registry token/password | Yes | — |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- Docker operations require a runner with Docker and the permissions needed to build, load, log in, or push images as applicable.

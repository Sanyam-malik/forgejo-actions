# Setup Docker

Installs Docker (if missing) and optionally configures a registry mirror

## Usage

```yaml
steps:
  - name: Setup Docker
    id: setup-docker
    uses: your-org/forgejo-actions/setup-docker@v1
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `registry_mirror` | Registry mirror URL (e.g. https://mirror.gcr.io) | No | `""` |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Docker operations require a runner with Docker and the permissions needed to build, load, log in, or push images as applicable.

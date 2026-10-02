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

- When the inherited `PKG_CACHE` environment variable is set, the Docker convenience installer is fetched through the mirror and Docker Hub pulls use `<PKG_CACHE>/registry-1.docker.io` as the registry mirror unless `registry_mirror` is explicitly provided. Run `setup-cache` once to derive and export it, or set `PKG_CACHE` explicitly as a job environment override.
- Runs as a vendor-neutral composite action on the current CI runner.
- Docker operations require a runner with Docker and the permissions needed to build, load, log in, or push images as applicable.

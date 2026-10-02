# Setup Docker

Installs Docker (if missing) and ensures the Docker daemon is running

## Usage

```yaml
steps:
  - name: Setup Docker
    id: setup-docker
    uses: your-org/forgejo-actions/setup-docker@v1
```

## Configuration

This action has no registry-mirror input. Configure BuildKit mirrors on the
`docker-build` or `docker-multi-build` action instead.

## Behavior and requirements

- When the inherited `PKG_CACHE` environment variable is set, the Docker convenience installer is fetched through the mirror. Run `setup-cache` once to derive and export it, or set `PKG_CACHE` explicitly as a job environment override.
- Runs as a vendor-neutral composite action on the current CI runner.
- Docker operations require a runner with Docker and the permissions needed to build, load, log in, or push images as applicable.

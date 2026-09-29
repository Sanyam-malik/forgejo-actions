# Docker Image Sync

Sync linked Docker container images from the current Forgejo repository package registry to external registries (e.g. GCR, Docker Hub, GHCR) with multi-arch support.

## Usage

```yaml
steps:
  - name: Docker Image Sync
    id: docker-sync
    uses: your-org/forgejo-actions/docker-sync@v1
    with:
      docker_registry: <docker_registry>
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `tag` | Source image tag to sync | No | `latest` |
| `token` | Token used to authenticate against the Forgejo source registry. Defaults to the auto-issued job token (github.token), which may lack package-registry scope depending on your instance. Pass a personal access token with package read permission here to bypass that without changing workflow-level permissions. | No | `""` |
| `docker_registry` | Target container registry URL (e.g. docker.io, gcr.io, ghcr.io) | Yes | — |
| `docker_registry_username` | Username for target registry authentication | No | `""` |
| `docker_registry_token` | Password or token for target registry authentication | No | `""` |
| `docker_registry_namespace` | Target registry namespace or organization (defaults to github.repository_owner) | No | `""` |
| `docker_registry_image` | Target image name override (defaults to auto-discovered package name) | No | `""` |
| `docker_registry_tag` | Target image tag or comma-separated list of tags (defaults to source_tag) | No | `""` |

## Outputs

| Name | Description |
| --- | --- |
| `source_image` | Fully resolved source image reference (or comma-separated list if multiple) |
| `synced_images` | Comma-separated list of fully resolved target image references that were synced |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- Docker operations require a runner with Docker and the permissions needed to build, load, log in, or push images as applicable.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

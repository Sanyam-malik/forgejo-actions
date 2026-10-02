# Docker Image Build

Build a single-platform Docker image to an OCI tar archive, without pushing it

## Usage

```yaml
steps:
  - name: Docker Image Build
    id: docker-build
    uses: your-org/forgejo-actions/docker-build@v1
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
| `dockerfile` | Path to the Dockerfile to build | No | `Dockerfile` |
| `platform` | Target platform (e.g. linux/amd64). Defaults to the runner's native architecture, preventing an accidental fall-through to an emulated platform. | No | `""` |
| `disable_process_sandbox` | Create and use a dedicated buildx builder with BuildKit's process sandbox disabled (--oci-worker-no-process-sandbox). Required for tools that write out and directly execute native helper binaries during the build (e.g. GraalVM native-image), which BuildKit's default process sandbox blocks. Only enable this for builds that specifically need it; leave disabled for normal builds so they keep the default hardened sandbox. | No | `false` |
| `build_args` | Additional docker build arguments (e.g. --build-arg FOO=bar) | No | `""` |
| `registry_mirror` | BuildKit mirror for Docker Hub | No | `""` |

## Outputs

| Name | Description |
| --- | --- |
| `image` | Full image reference |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- Docker operations require a runner with Docker and the permissions needed to build, load, log in, or push images as applicable.
- The build writes an OCI archive in the workspace; it does not push the image unless the action description says otherwise.
- Set `tags` to one tag (`latest`) or multiple comma-separated tags (`1.2.3,latest`); all tags are applied to the exported image.
- Set `registry_mirror` to a Docker Hub mirror, or set `PKG_CACHE` to use `<PKG_CACHE>/registry-1.docker.io` automatically. The mirror is scoped to this BuildKit builder and does not restart the Docker daemon.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

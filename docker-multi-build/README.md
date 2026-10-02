# Docker Multi Image Build

Build a multi-architecture Docker image to an OCI tar archive with platform validation and alias support

## Usage

```yaml
steps:
  - name: Docker Multi Image Build
    id: docker-multi-build
    uses: your-org/forgejo-actions/docker-multi-build@v1
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
| `build_args` | Additional docker build arguments | No | `""` |
| `registry_mirror` | BuildKit mirror for Docker Hub | No | `""` |
| `platforms` | Comma-separated list of target platforms to build (supports aliases like armhf, armv7, x86_64, aarch64) | No | `linux/amd64,linux/arm64,linux/arm/v7` |
| `validate_platforms` | Whether to validate platform buildability before building | No | `true` |
| `disable_process_sandbox` | Create the Buildx builder with BuildKit's process sandbox disabled (--oci-worker-no-process-sandbox). Required for tools that write out and directly execute native helper binaries during the build (e.g. GraalVM native-image), which BuildKit's default process sandbox blocks. Only enable this for builds that specifically need it; leave disabled for normal builds so they keep the default hardened sandbox. | No | `false` |

## Outputs

| Name | Description |
| --- | --- |
| `image` | Fully resolved image reference embedded in the archive (registry/namespace/image:tag) |
| `supported_platforms` | Comma-separated list of platforms that were validated and built |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- Docker operations require a runner with Docker and the permissions needed to build, load, log in, or push images as applicable.
- The build writes an OCI archive in the workspace; it does not push the image unless the action description says otherwise.
- Set `registry_mirror` to a Docker Hub mirror, or set `PKG_CACHE` to use `<PKG_CACHE>/registry-1.docker.io` automatically. The mirror is scoped to this BuildKit builder and does not restart the Docker daemon.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

# Set Image Metadata

Compute docker image name and namespace from repository

## Usage

```yaml
steps:
  - name: Set Image Metadata
    id: set-image
    uses: your-org/forgejo-actions/utils/set-image@v1
```

## Inputs

This action has no inputs.

## Outputs

| Name | Description |
| --- | --- |
| `image` | Image name |
| `namespace` | Namespace |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Docker operations require a runner with Docker and the permissions needed to build, load, log in, or push images as applicable.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

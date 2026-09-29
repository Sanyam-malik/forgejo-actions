# Clone Git Repository

Clone a git repository supporting branch, tag, commit, or PR refs with optional shallow clone

## Usage

```yaml
steps:
  - name: Clone Git Repository
    id: git-clone
    uses: your-org/forgejo-actions/git-clone@v1
    with:
      repo: owner/repository
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `repo` | Repository URL | Yes | — |
| `ref` | Branch, tag, commit SHA, or ref | No | `""` |
| `depth` | Clone depth (0 = full clone) | No | `1` |
| `token` | Authentication token (optional) | No | `""` |
| `directory` | Directory to clone into | No | `repo` |

## Outputs

| Name | Description |
| --- | --- |
| `repo_dir` | Path to cloned repository |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

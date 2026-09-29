# Deploy to GitHub Pages

Deploy static site to a branch

## Usage

```yaml
steps:
  - name: Deploy to GitHub Pages
    id: deploy-pages
    uses: your-org/forgejo-actions/deploy-pages@v1
    with:
      site_path: dist
      git_user: CI Bot
      git_email: ci@example.com
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `site_path` | Path to built site directory | Yes | — |
| `git_user` | Git username | Yes | — |
| `git_email` | Git email | Yes | — |
| `target_branch` | Branch to deploy site | No | `gh-pages` |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.

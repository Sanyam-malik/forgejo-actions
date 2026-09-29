# Post PR Comments

Post inline pull-request review comments to a Forgejo (or Gitea) PR, driven by a JSON file of items and a message template. Generic — no assumptions about linters, reviewdog, or any particular tool.

## Usage

```yaml
steps:
  - name: Post PR Comments
    id: post-file-comment
    uses: your-org/forgejo-actions/post-file-comment@v1
    with:
      items-file: review-items.json
      message-template-file: review-comment.md
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `items-file` | Path to a JSON file containing an array of items, one per comment. Each item can be any nested shape (e.g. [{"location": {"file": "src/app.py", "range": {"start": {"line": 42}}}, "message": "..."}]) -- path-field/line-field say where to find the position, and the rest is available to the message template. | Yes | — |
| `message-template-file` | Path to a file containing the template for each comment body. Placeholders use a small dotted/indexed path syntax that reaches into nested JSON, e.g. "{message}", "{location.file}", "{range.start.line}", "{tags[0]}". A placeholder that doesn't resolve for a given item is left as literal text rather than failing the run, so one template can tolerate items of varying shape. | Yes | — |
| `path-field` | Dotted/indexed path into each item for the file path the comment attaches to, e.g. "path" or "location.file". | No | `location.file` |
| `line-field` | Dotted/indexed path into each item for the 1-based line number the comment attaches to, e.g. "line" or "range.start.line". This is the one fixed lookup every item must resolve, however the rest of the item's JSON is shaped. | No | `range.start.line` |
| `review-body` | Template for the top-level review summary comment. Supports a {count} placeholder for the number of comments being posted. Set to '' (empty) to skip the top-level comment entirely and post only the inline per-item comments. | No | `""` |
| `dedupe` | Drop duplicate (path, line, rendered body) comments before posting. | No | `true` |
| `fail-on-comments` | If true, the action exits non-zero when one or more comments are posted. | No | `false` |
| `api-url` | Base URL of the Forgejo/Gitea API, e.g. https://forgejo.example.com/api/v1. Defaults to the runner-provided API URL for the current instance. | No | `${{ github.api_url }}` |
| `owner` | Repository owner/organization. Defaults to the current repository's owner. | No | `${{ github.repository_owner }}` |
| `repo` | Repository name. Defaults to the current repository's name. | No | `${{ github.event.repository.name }}` |
| `pr-number` | Pull request number. Defaults to the number of the pull request that triggered this workflow. | No | `${{ github.event.pull_request.number }}` |
| `head-sha` | Commit SHA the review should be attached to. Defaults to the head commit of the pull request that triggered this workflow. | No | `${{ github.event.pull_request.head.sha }}` |
| `token` | Token used to post pull-request review comments. Defaults to the Forgejo-provided GitHub-compatible workflow token; override with a PAT if the default token lacks permission to create reviews. | No | `${{ github.token }}` |

## Outputs

| Name | Description |
| --- | --- |
| `comments-posted` | Number of inline comments posted. |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Required inputs must be supplied; they have no declared defaults.
- Pull-request operations require the relevant event context and a token with sufficient repository permissions.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

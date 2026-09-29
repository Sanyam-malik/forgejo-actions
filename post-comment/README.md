# Comment on Pull Request

Post (or update) a markdown comment on the pull request associated with the current ref

## Usage

```yaml
steps:
  - name: Comment on Pull Request
    id: post-comment
    uses: your-org/forgejo-actions/post-comment@v1
    with:
      body: "Build completed successfully."
```

## Inputs

| Name | Description | Required | Default |
| --- | --- | :---: | --- |
| `body` | Markdown comment body to post. Ignored if body_path is set. | No | `""` |
| `body_path` | Path to a file containing the markdown comment body. Takes precedence over body if both are set. | No | `""` |
| `marker` | A unique string (e.g. an HTML comment like "<!-- my-tool-summary -->") used to find a previous comment to update in place. It is prepended to the comment body if the body does not already start with it. Leave empty to always post a new comment instead of upserting. | No | `""` |
| `pr_number` | Pull request number to comment on. If empty, it is auto-detected from the triggering event or the current branch's open pull request. | No | `""` |
| `fail_if_no_pr` | Fail the action if no pull request could be found to comment on. | No | `false` |
| `token` | API token used to authenticate with the Forgejo/GitHub API. | No | `${{ github.token }}` |
| `api_url` | Base API URL. Defaults to the current server's API. | No | `${{ github.api_url }}` |
| `server_url` | Base server URL, used to derive api_url when api_url is empty. | No | `${{ github.server_url }}` |
| `repository` | owner/repo to comment on. | No | `${{ github.repository }}` |
| `ref_name` | Current ref name, used for pull request auto-detection when not triggered by a pull_request event. | No | `${{ github.ref_name }}` |
| `head_ref` | Head ref of the pull request, used for auto-detection. | No | `${{ github.head_ref }}` |
| `event_name` | Name of the triggering event. | No | `${{ github.event_name }}` |
| `event_path` | Path to the event payload file, used to read the pull request number when triggered by pull_request. | No | `${{ github.event_path }}` |

## Outputs

| Name | Description |
| --- | --- |
| `comment_id` | ID of the comment that was created or updated. Empty if no comment was posted. |
| `action` | One of "created", "updated", or "skipped". |
| `pr_number` | The pull request number that was commented on, if any. |

## Behavior and requirements

- Runs as a vendor-neutral composite action on the current CI runner.
- Pull-request operations require the relevant event context and a token with sufficient repository permissions.
- To read outputs, assign an `id` to the action step and use `${{ steps.<step-id>.outputs.<output-name> }}`.

# Code Review

Runs MegaLinter through reviewdog and converts pull-request lint findings into
normalized JSON review items. Shared filtering, fingerprinting,
existing-comment handling, auto-resolution, posting, and fail-level enforcement
are delegated to [`code-analyzer`](../code-analyzer/).

## Usage

```yaml
- uses: actions/forgejo/code-review@v1
  with:
    level: error
    filter-mode: changed_files
    skip-existing: true
    fail-level: warning
    token: ${{ github.token }}
```

Run this action in a `pull_request` workflow. The token must be able to read
pull-request files and review comments.

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `token` | `${{ github.token }}` | Token used for pull-request API access and comments. |
| `pkg_cache` | `""` | Optional package cache host or base URL for reviewdog. |
| `languages` | `""` | Comma-separated languages to force MegaLinter to run. |
| `exclude-languages` | `""` | Comma-separated languages to skip. |
| `exclude-tools` | `""` | Comma-separated linters to skip. |
| `level` | `error` | Minimum severity passed to `code-analyzer`: `info`, `warning`, or `error`. |
| `filter-mode` | `changed_files` | Review scope: `changed_files`, `added`, `diff_context`, `file`, or `nofilter`. |
| `fail-level` | `none` | Failure threshold: `none`, `any`, `info`, `warning`, or `error`. |
| `skip-existing` | `true` | Skip open findings already commented on and auto-mark stale comments fixed. |
| `reviewdog-version` | `latest` | Reviewdog version, such as `latest` or `vX.Y.Z`. |
| `workdir` | `.` | Directory in which reviewdog runs. |

## Outputs

| Output | Description |
| --- | --- |
| `item-count` | New findings after filtering and existing-comment suppression. |
| `total-count` | Current findings before existing-comment suppression. |
| `skipped-existing-count` | Findings skipped because their fingerprints are already open. |
| `resolved-count` | Earlier comments auto-marked fixed because their findings disappeared. |
| `should-fail` | `true` when the configured fail threshold was met. |

## Architecture

[`scripts/build-review-items.py`](scripts/build-review-items.py) reads
reviewdog output and writes `review-items.json`. The shared
[`code-analyzer`](../code-analyzer/) action performs the remaining lifecycle
and posts using `post-file-comment`.

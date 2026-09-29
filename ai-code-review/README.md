# AI Code Review

Reviews changed pull-request files with an LLM served by an OpenAI-compatible
endpoint, including Ollama, llama.cpp, vLLM, and OpenAI. The producer writes a
JSON review envelope; [`code-analyzer`](../code-analyzer/) applies shared
filtering, fingerprinting, comment lifecycle, posting, and failure handling.

## Usage

```yaml
- uses: actions/forgejo/ai-code-review@v1
  with:
    ai-base-url: https://api.openai.com/v1
    ai-model: gpt-4o
    ai-api-key: ${{ secrets.OPENAI_API_KEY }}
    level: warning
    skip-existing: true
    fail-level: none
    token: ${{ github.token }}
```

Run this action in a `pull_request` workflow. Local endpoints can leave
`ai-api-key` empty.

## Inputs

### Model endpoint

| Input | Default | Description |
| --- | --- | --- |
| `ai-base-url` | required | OpenAI-compatible API base URL before `/chat/completions`. |
| `ai-model` | required | Model name sent to the endpoint. |
| `ai-api-key` | `""` | Optional API key. |
| `ai-temperature` | `0.1` | Sampling temperature. |
| `ai-max-tokens` | `4096` | Maximum generated tokens per request. |
| `ai-timeout` | `180` | Per-request timeout in seconds. |
| `ai-json-mode` | `true` | Request JSON mode and retry without it if rejected. |

### Review scope and noise control

| Input | Default | Description |
| --- | --- | --- |
| `focus` | correctness, security, reliability, performance, maintainability, testing | Review areas sent to the model. |
| `extra-instructions` | `""` | Additional prompt instructions. |
| `guidelines-file` | `""` | Repository guidelines file, truncated to 6000 characters. |
| `system-prompt-file` | `""` | File replacing the built-in system prompt. |
| `include` | `""` | Comma/newline-separated file globs to include. |
| `exclude` | built-in exclusions | Comma/newline-separated globs to skip; use `none` to disable defaults. |
| `level` | `warning` | Minimum severity to post: `info`, `warning`, or `error`. |
| `min-confidence` | `0.5` | Minimum model confidence from 0 to 1. |
| `max-comments` | `0` | Maximum comments after shared processing; `0` means unlimited. |
| `skip-existing` | `true` | Skip open findings already commented on and auto-mark stale comments fixed. |

### Limits and failure behavior

| Input | Default | Description |
| --- | --- | --- |
| `max-files` | `0` | Maximum changed files to review; `0` means unlimited. |
| `max-chars` | `20000` | Maximum diff characters per model request. |
| `max-requests` | `0` | Maximum model requests; `0` means unlimited. |
| `concurrency` | `4` | Number of parallel model requests. |
| `batch-files` | `true` | Pack small files into a request. |
| `fail-level` | `none` | Failure threshold: `none`, `any`, `info`, `warning`, or `error`. |
| `fail-on-ai-error` | `false` | Fail if one or more model requests fail. |
| `token` | `${{ github.token }}` | Token used for pull-request API access and comments. |

## Outputs

| Output | Description |
| --- | --- |
| `item-count` | New findings after shared processing. |
| `should-fail` | `true` when the configured fail threshold was met. |

## Architecture

[`scripts/ai-review.py`](scripts/ai-review.py) writes an envelope containing
`items` and AI review metadata. The shared
[`code-analyzer`](../code-analyzer/) action owns filtering, fingerprints,
existing-comment lookup, auto-resolution, posting, and fail-level enforcement.

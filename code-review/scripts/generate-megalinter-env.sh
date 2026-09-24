#!/usr/bin/env bash
# Translates this action's languages / exclude-languages / exclude-tools
# inputs into the environment variables MegaLinter understands, and
# appends them to $GITHUB_ENV so the "Run MegaLinter" step picks them up.
#
# MegaLinter does its own language auto-detection, so LANGUAGES is only
# used to force a specific set (same semantics as before). Unknown keys
# are warned about and skipped rather than failing the build.
set -euo pipefail

LANGUAGES="${LANGUAGES:-}"
EXCLUDE_LANGUAGES="${EXCLUDE_LANGUAGES:-}"
EXCLUDE_TOOLS="${EXCLUDE_TOOLS:-}"

# Our language keys -> MegaLinter language/format identifiers.
declare -A LANG_MAP=(
  [go]=GO
  [python]=PYTHON
  [javascript]=JAVASCRIPT
  [shell]=BASH
  [yaml]=YAML
  [ruby]=RUBY
  [rust]=RUST
  [markdown]=MARKDOWN
  [terraform]=TERRAFORM
  [php]=PHP
  [dockerfile]=DOCKERFILE
)

# Our tool keys -> MegaLinter linter keys (for DISABLE_LINTERS).
declare -A TOOL_MAP=(
  [golangci-lint]=GO_GOLANGCI_LINT
  [ruff]=PYTHON_RUFF
  [eslint]=JAVASCRIPT_ES
  [shellcheck]=BASH_SHELLCHECK
  [yamllint]=YAML_YAMLLINT
  [hadolint]=DOCKERFILE_HADOLINT
  [rubocop]=RUBY_RUBOCOP
  [clippy]=RUST_CLIPPY
  [markdownlint]=MARKDOWN_MARKDOWNLINT
  [tflint]=TERRAFORM_TFLINT
  [phpcs]=PHP_PHPCS
)

csv_to_list () { # $1 = comma separated string -> prints trimmed items, one per line
  local raw="$1"
  [ -z "$raw" ] && return 0
  IFS=',' read -ra items <<< "$raw"
  for item in "${items[@]}"; do
    trimmed="$(echo "$item" | xargs)"
    [ -n "$trimmed" ] && echo "$trimmed"
  done
}

enable=""
while IFS= read -r key; do
  mapped="${LANG_MAP[$key]:-}"
  if [ -n "$mapped" ]; then
    enable="${enable}${enable:+,}${mapped}"
  else
    echo "WARN: unknown language '$key', ignoring for MegaLinter ENABLE" >&2
  fi
done < <(csv_to_list "$LANGUAGES")

disable=""
while IFS= read -r key; do
  mapped="${LANG_MAP[$key]:-}"
  [ -n "$mapped" ] && disable="${disable}${disable:+,}${mapped}"
done < <(csv_to_list "$EXCLUDE_LANGUAGES")

# Security/secret scanners are out of scope for this action by design,
# same as before the MegaLinter switch.
disable_linters="REPOSITORY_GITLEAKS,REPOSITORY_TRIVY,REPOSITORY_SECRETLINT,PYTHON_BANDIT"

while IFS= read -r key; do
  mapped="${TOOL_MAP[$key]:-}"
  if [ -n "$mapped" ]; then
    disable_linters="${disable_linters}${disable_linters:+,}${mapped}"
  else
    echo "WARN: unknown tool '$key', ignoring for MegaLinter DISABLE_LINTERS" >&2
  fi
done < <(csv_to_list "$EXCLUDE_TOOLS")

{
  echo "MEGALINTER_ENABLE=$enable"
  echo "MEGALINTER_DISABLE=$disable"
  echo "MEGALINTER_DISABLE_LINTERS=$disable_linters"
} >> "${GITHUB_ENV:?GITHUB_ENV is required}"

echo "MegaLinter ENABLE          : ${enable:-<auto-detect>}"
echo "MegaLinter DISABLE         : ${disable:-<none>}"
echo "MegaLinter DISABLE_LINTERS : ${disable_linters}"
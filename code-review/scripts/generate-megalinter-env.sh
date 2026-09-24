#!/usr/bin/env bash

set -euo pipefail

LANGUAGES="${LANGUAGES:-}"
EXCLUDE_LANGUAGES="${EXCLUDE_LANGUAGES:-}"
EXCLUDE_TOOLS="${EXCLUDE_TOOLS:-}"

declare -A LANG_MAP=(
  [go]=GO
  [golang]=GO
  [python]=PYTHON
  [javascript]=JAVASCRIPT
  [typescript]=TYPESCRIPT
  [jsx]=JSX
  [tsx]=TSX
  [shell]=BASH
  [bash]=BASH
  [yaml]=YAML
  [yml]=YAML
  [json]=JSON
  [ruby]=RUBY
  [rust]=RUST
  [markdown]=MARKDOWN
  [terraform]=TERRAFORM
  [php]=PHP
  [dockerfile]=DOCKERFILE
  [java]=JAVA
  [kotlin]=KOTLIN
  [groovy]=GROOVY
  [scala]=SCALA
  [c]=C
  [cpp]=CPP
  [c++]=CPP
  [csharp]=C
  [cs]=C
  [dotnet]=C
)

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

csv_to_list() {
  local raw="$1"

  [ -z "$raw" ] && return 0

  IFS=',' read -ra items <<< "$raw"

  for item in "${items[@]}"; do
    item="${item#"${item%%[![:space:]]*}"}"
    item="${item%"${item##*[![:space:]]}"}"

    [ -n "$item" ] && printf '%s\n' "$item"
  done
}

enable=""

while IFS= read -r key; do
  key="${key,,}"

  mapped="${LANG_MAP[$key]:-}"

  if [ -n "$mapped" ]; then
    case ",$enable," in
      *,"$mapped",*)
        ;;
      *)
        enable="${enable}${enable:+,}${mapped}"
        ;;
    esac
  else
    echo "WARN: unknown language '$key', ignoring for MegaLinter ENABLE" >&2
  fi
done < <(csv_to_list "$LANGUAGES")

disable=""

while IFS= read -r key; do
  key="${key,,}"

  mapped="${LANG_MAP[$key]:-}"

  if [ -n "$mapped" ]; then
    case ",$disable," in
      *,"$mapped",*)
        ;;
      *)
        disable="${disable}${disable:+,}${mapped}"
        ;;
    esac
  else
    echo "WARN: unknown language '$key', ignoring for MegaLinter DISABLE" >&2
  fi
done < <(csv_to_list "$EXCLUDE_LANGUAGES")

disable_linters="REPOSITORY_GITLEAKS,REPOSITORY_TRIVY,REPOSITORY_SECRETLINT,PYTHON_BANDIT"

while IFS= read -r key; do
  key="${key,,}"

  mapped="${TOOL_MAP[$key]:-}"

  if [ -n "$mapped" ]; then
    case ",$disable_linters," in
      *,"$mapped",*)
        ;;
      *)
        disable_linters="${disable_linters},${mapped}"
        ;;
    esac
  else
    echo "WARN: unknown tool '$key', ignoring for MegaLinter DISABLE_LINTERS" >&2
  fi
done < <(csv_to_list "$EXCLUDE_TOOLS")

{
  printf 'MEGALINTER_ENABLE=%s\n' "$enable"
  printf 'MEGALINTER_DISABLE=%s\n' "$disable"
  printf 'MEGALINTER_DISABLE_LINTERS=%s\n' "$disable_linters"
} >> "${GITHUB_ENV:?GITHUB_ENV is required}"

echo "MegaLinter ENABLE          : ${enable:-<auto-detect>}"
echo "MegaLinter DISABLE         : ${disable:-<none>}"
echo "MegaLinter DISABLE_LINTERS : ${disable_linters}"
#!/usr/bin/env bash

set -euo pipefail


# ============================================================
# Inputs
# ============================================================

LANGUAGES="${LANGUAGES:-}"
EXCLUDE_LANGUAGES="${EXCLUDE_LANGUAGES:-}"
EXCLUDE_TOOLS="${EXCLUDE_TOOLS:-}"
REVIEW_WORKDIR="${REVIEW_WORKDIR:-.}"


# ============================================================
# Validate required GitHub/Forgejo Action variables
# ============================================================

: "${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}"
: "${GITHUB_ENV:?GITHUB_ENV is required}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"


# ============================================================
# Resolve the MegaLinter workspace
#
# This must match DEFAULT_WORKSPACE in action.yml.
# ============================================================

if [ "$REVIEW_WORKDIR" = "." ] || [ -z "$REVIEW_WORKDIR" ]; then
  WORKSPACE="$GITHUB_WORKSPACE"
else
  WORKSPACE="$GITHUB_WORKSPACE/$REVIEW_WORKDIR"
fi

WORKSPACE="${WORKSPACE%/}"


# ============================================================
# Detect repository MegaLinter configuration
#
# If auto-review.yml exists, it becomes authoritative.
#
# We deliberately do NOT generate:
#
#   MEGALINTER_ENABLE
#   MEGALINTER_DISABLE
#   MEGALINTER_DISABLE_LINTERS
#
# in this mode.
# ============================================================

MEGALINTER_CONFIG_FILE="$WORKSPACE/auto-review.yml"


if [ -f "$MEGALINTER_CONFIG_FILE" ]; then

  echo ""
  echo "============================================================"
  echo "MegaLinter configuration"
  echo "============================================================"
  echo ""
  echo "Found:"
  echo "  $MEGALINTER_CONFIG_FILE"
  echo ""
  echo "Using:"
  echo "  MEGALINTER_CONFIG=auto-review.yml"
  echo ""
  echo "Repository MegaLinter configuration is authoritative."
  echo "Action language/tool overrides will NOT be generated."
  echo ""

  # Tell action.yml which MegaLinter step to execute.
  printf 'config_found=true\n' >> "$GITHUB_OUTPUT"

  # MegaLinter will resolve this relative to DEFAULT_WORKSPACE.
  printf 'MEGALINTER_CONFIG=auto-review.yml\n' >> "$GITHUB_ENV"

  # Clear any fallback values.
  #
  # The configured MegaLinter step does not consume these values,
  # but clearing them prevents stale environment state.
  printf 'MEGALINTER_ENABLE=\n' >> "$GITHUB_ENV"
  printf 'MEGALINTER_DISABLE=\n' >> "$GITHUB_ENV"
  printf 'MEGALINTER_DISABLE_LINTERS=\n' >> "$GITHUB_ENV"

  exit 0
fi


# ============================================================
# No auto-review.yml
#
# Preserve the existing action behaviour.
# ============================================================

echo ""
echo "============================================================"
echo "MegaLinter automatic configuration"
echo "============================================================"
echo ""
echo "No auto-review.yml found in:"
echo "  $WORKSPACE"
echo ""
echo "Using action language/tool inputs."
echo ""


# Tell action.yml to use the normal MegaLinter step.
printf 'config_found=false\n' >> "$GITHUB_OUTPUT"

# Explicitly clear custom config.
printf 'MEGALINTER_CONFIG=\n' >> "$GITHUB_ENV"


# ============================================================
# Language map
# ============================================================

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


# ============================================================
# Tool map
# ============================================================

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


# ============================================================
# CSV helper
#
# Converts:
#
#   java, python, yaml
#
# into:
#
#   java
#   python
#   yaml
#
# No xargs dependency.
# ============================================================

csv_to_list() {
  local raw="$1"

  [ -z "$raw" ] && return 0

  IFS=',' read -ra items <<< "$raw"

  for item in "${items[@]}"; do

    # Trim leading whitespace.
    item="${item#"${item%%[![:space:]]*}"}"

    # Trim trailing whitespace.
    item="${item%"${item##*[![:space:]]}"}"

    [ -n "$item" ] && printf '%s\n' "$item"

  done
}


# ============================================================
# Build ENABLE
# ============================================================

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

    echo \
      "WARN: unknown language '$key', ignoring for MegaLinter ENABLE" \
      >&2

  fi

done < <(csv_to_list "$LANGUAGES")


# ============================================================
# Build DISABLE
# ============================================================

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

    echo \
      "WARN: unknown language '$key', ignoring for MegaLinter DISABLE" \
      >&2

  fi

done < <(csv_to_list "$EXCLUDE_LANGUAGES")


# ============================================================
# Default disabled linters
# ============================================================

disable_linters="REPOSITORY_GITLEAKS,REPOSITORY_TRIVY,REPOSITORY_SECRETLINT,PYTHON_BANDIT"


# ============================================================
# Build DISABLE_LINTERS
# ============================================================

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

    echo \
      "WARN: unknown tool '$key', ignoring for MegaLinter DISABLE_LINTERS" \
      >&2

  fi

done < <(csv_to_list "$EXCLUDE_TOOLS")


# ============================================================
# Export generated configuration
# ============================================================

{
  printf 'MEGALINTER_ENABLE=%s\n' "$enable"
  printf 'MEGALINTER_DISABLE=%s\n' "$disable"
  printf 'MEGALINTER_DISABLE_LINTERS=%s\n' "$disable_linters"
} >> "$GITHUB_ENV"


# ============================================================
# Display effective configuration
# ============================================================

echo "MegaLinter ENABLE          : ${enable:-<auto-detect>}"
echo "MegaLinter DISABLE         : ${disable:-<none>}"
echo "MegaLinter DISABLE_LINTERS : ${disable_linters}"
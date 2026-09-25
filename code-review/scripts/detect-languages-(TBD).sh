#!/usr/bin/env bash
# Detects which programming languages a repo uses by counting tracked files
# per extension. Writes a comma separated list to $GITHUB_OUTPUT as
# "languages". Honors LANGUAGES_OVERRIDE / EXCLUDE_LANGUAGES / MIN_FILES env
# vars.
set -euo pipefail

MIN_FILES="${MIN_FILES:-1}"

if [ -n "${LANGUAGES_OVERRIDE:-}" ]; then
  detected="$LANGUAGES_OVERRIDE"
  echo "Language auto-detection skipped, using override: $detected"
else
  # Tracked files only (respects .gitignore); drop common vendor/build dirs.
  files="$(git ls-files \
    | grep -Ev '(^|/)(vendor|node_modules|dist|build|\.git|third_party|target)/' || true)"

  declare -A counts=()
  count_ext () { # $1=key $2=count
    counts["$1"]=$(( ${counts["$1"]:-0} + $2 ))
  }

  while IFS= read -r f; do
    [ -z "$f" ] && continue
    base="$(basename "$f")"
    case "$base" in
      Dockerfile|Dockerfile.*|*.dockerfile) count_ext dockerfile 1; continue ;;
    esac
    case "$f" in
      *.go)                              count_ext go 1 ;;
      *.py)                              count_ext python 1 ;;
      *.js|*.jsx|*.mjs|*.cjs|*.ts|*.tsx) count_ext javascript 1 ;;
      *.sh|*.bash)                       count_ext shell 1 ;;
      *.yml|*.yaml)                      count_ext yaml 1 ;;
      *.rb)                              count_ext ruby 1 ;;
      *.rs)                              count_ext rust 1 ;;
      *.md|*.markdown)                   count_ext markdown 1 ;;
      *.tf|*.tfvars)                     count_ext terraform 1 ;;
      *.php)                             count_ext php 1 ;;
    esac
  done <<< "$files"

  detected=""
  for lang in "${!counts[@]}"; do
    if [ "${counts[$lang]}" -ge "$MIN_FILES" ]; then
      detected="${detected}${detected:+,}${lang}"
    fi
  done
fi

# Apply exclusions
if [ -n "${EXCLUDE_LANGUAGES:-}" ]; then
  IFS=',' read -ra excl <<< "$EXCLUDE_LANGUAGES"
  IFS=',' read -ra langs <<< "$detected"
  kept=()
  for l in "${langs[@]}"; do
    l_trim="$(echo "$l" | xargs)"
    skip=false
    for e in "${excl[@]}"; do
      [ "$l_trim" = "$(echo "$e" | xargs)" ] && skip=true
    done
    [ -n "$l_trim" ] && [ "$skip" = false ] && kept+=("$l_trim")
  done
  detected="$(IFS=','; echo "${kept[*]}")"
fi

echo "Detected languages: ${detected:-none}"
{
  echo "languages=$detected"
} >> "${GITHUB_OUTPUT:-/dev/stdout}"
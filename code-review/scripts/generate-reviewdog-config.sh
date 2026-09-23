#!/usr/bin/env bash
# Builds .reviewdog.generated.yml containing one `runner` entry per linter
# that is (a) for a detected language, (b) not in EXCLUDE_TOOLS, and
# (c) actually installed. Security/secret scanners are never added here —
# they are out of scope for this action by design.
set -uo pipefail

LANGUAGES="${LANGUAGES:-}"
EXCLUDE_TOOLS="${EXCLUDE_TOOLS:-}"
CONF=".reviewdog.generated.yml"

excluded () {
  [ -z "$EXCLUDE_TOOLS" ] && return 1
  IFS=',' read -ra excl <<< "$EXCLUDE_TOOLS"
  for e in "${excl[@]}"; do
    [ "$(echo "$e" | xargs)" = "$1" ] && return 0
  done
  return 1
}

has_lang () {
  IFS=',' read -ra langs <<< "$LANGUAGES"
  for l in "${langs[@]}"; do
    [ "$(echo "$l" | xargs)" = "$1" ] && return 0
  done
  return 1
}

echo "runner:" > "$CONF"
count=0

add_runner () { # $1=name $2=cmd $3=errorformat $4=level
  cat >> "$CONF" <<EOF
  $1:
    cmd: $2
    errorformat:
      - '$3'
    level: $4
EOF
  count=$((count + 1))
}

if has_lang go && ! excluded golangci-lint && command -v golangci-lint >/dev/null 2>&1; then
  add_runner golangci-lint \
    "golangci-lint run --timeout=5m --out-format=line-number --disable=gosec ./..." \
    '%f:%l:%c: %m' warning
fi

if has_lang python && ! excluded ruff && command -v ruff >/dev/null 2>&1; then
  # -S (flake8-bandit) rules are security checks: excluded on purpose.
  add_runner ruff \
    "ruff check --output-format=concise --ignore=S ." \
    '%f:%l:%c: %m' warning
fi

if has_lang javascript && ! excluded eslint; then
  eslint_bin="npx eslint"
  add_runner eslint \
    "$eslint_bin . -f unix --no-error-on-unmatched-pattern" \
    '%f:%l:%c: %m' warning
fi

if has_lang shell && ! excluded shellcheck && command -v shellcheck >/dev/null 2>&1; then
  add_runner shellcheck \
    "bash -c \"git ls-files '*.sh' '*.bash' | xargs -r shellcheck -f gcc\"" \
    '%f:%l:%c: %m' warning
fi

if has_lang yaml && ! excluded yamllint && command -v yamllint >/dev/null 2>&1; then
  add_runner yamllint \
    "yamllint -f parsable ." \
    '%f:%l:%c: %m' info
fi

if has_lang dockerfile && ! excluded hadolint && command -v hadolint >/dev/null 2>&1; then
  add_runner hadolint \
    "bash -c \"git ls-files 'Dockerfile*' '*.dockerfile' | xargs -r -I{} hadolint -f gnu {}\"" \
    '%f:%l %c %m' warning
fi

if has_lang ruby && ! excluded rubocop && command -v rubocop >/dev/null 2>&1; then
  add_runner rubocop \
    "rubocop --format emacs --except Security ." \
    '%f:%l:%c: %m' warning
fi

if has_lang rust && ! excluded clippy && command -v cargo >/dev/null 2>&1; then
  add_runner clippy \
    "cargo clippy --message-format=short --all-targets 2>&1" \
    '%f:%l:%c: %m' warning
fi

if has_lang markdown && ! excluded markdownlint; then
  add_runner markdownlint \
    "npx markdownlint '**/*.md' --ignore node_modules" \
    '%f:%l %m' info
fi

if has_lang terraform && ! excluded tflint && command -v tflint >/dev/null 2>&1; then
  add_runner tflint \
    "tflint --format=compact" \
    '%f:%l:%c: %m' warning
fi

if has_lang php && ! excluded phpcs && command -v phpcs >/dev/null 2>&1; then
  add_runner phpcs \
    "phpcs --report=emacs ." \
    '%f:%l:%c: %m' warning
fi

echo "Generated $CONF with $count runner(s):"
cat "$CONF"

{
  echo "runner-count=$count"
} >> "${GITHUB_OUTPUT:-/dev/stdout}"
#!/usr/bin/env bash
# Installs one open-source, non-security linter per detected language.
# Assumes the relevant language toolchain (go/node/python/ruby/rust/php) was
# already set up by a prior step (actions/setup-go, setup-node, setup-python,
# ...) when that toolchain isn't preinstalled on the runner image.
set -uo pipefail

export PATH="$HOME/.local/bin:$PATH"

LANGUAGES="${LANGUAGES:-}"
EXCLUDE_TOOLS="${EXCLUDE_TOOLS:-}"

excluded () { # $1 = tool name
  [ -z "$EXCLUDE_TOOLS" ] && return 1
  IFS=',' read -ra excl <<< "$EXCLUDE_TOOLS"
  for e in "${excl[@]}"; do
    [ "$(echo "$e" | xargs)" = "$1" ] && return 0
  done
  return 1
}

has_lang () { # $1 = language key
  IFS=',' read -ra langs <<< "$LANGUAGES"
  for l in "${langs[@]}"; do
    [ "$(echo "$l" | xargs)" = "$1" ] && return 0
  done
  return 1
}

echo "Installing linters for: ${LANGUAGES:-<none>}"

if has_lang go && ! excluded golangci-lint; then
  echo "-> golangci-lint"
  go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest || echo "  WARN: golangci-lint install failed (is Go set up?)"
fi

if has_lang python && ! excluded ruff; then
  echo "-> ruff"
  python3 -m pip install --user --quiet ruff || echo "  WARN: ruff install failed (is Python set up?)"
fi

if has_lang javascript && ! excluded eslint; then
  echo "-> eslint (using repo's own config if present)"
  # We rely on the repo already having eslint as a devDependency where
  # possible; otherwise fall back to a bare eslint for basic syntax checks.
  if [ ! -f package.json ] || ! grep -q '"eslint"' package.json 2>/dev/null; then
    npm install --no-save --silent eslint@latest || echo "  WARN: eslint install failed (is Node set up?)"
  fi
fi

if has_lang shell && ! excluded shellcheck; then
  echo "-> shellcheck"
  if ! command -v shellcheck >/dev/null 2>&1; then
    sudo apt-get update -qq && sudo apt-get install -y -qq shellcheck || echo "  WARN: shellcheck install failed"
  fi
fi

if has_lang yaml && ! excluded yamllint; then
  echo "-> yamllint"
  python3 -m pip install --user --quiet yamllint || echo "  WARN: yamllint install failed (is Python set up?)"
fi

if has_lang dockerfile && ! excluded hadolint; then
  echo "-> hadolint"
  if ! command -v hadolint >/dev/null 2>&1; then
    curl -sSfL -o /usr/local/bin/hadolint \
      https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64 \
      && sudo chmod +x /usr/local/bin/hadolint \
      || echo "  WARN: hadolint install failed"
  fi
fi

if has_lang ruby && ! excluded rubocop; then
  echo "-> rubocop"
  gem install --user-install --no-document rubocop || echo "  WARN: rubocop install failed (is Ruby set up?)"
fi

if has_lang rust && ! excluded clippy; then
  echo "-> clippy"
  rustup component add clippy 2>/dev/null || echo "  WARN: clippy install failed (is Rust/rustup set up?)"
fi

if has_lang markdown && ! excluded markdownlint; then
  echo "-> markdownlint-cli"
  npm install --no-save --silent markdownlint-cli || echo "  WARN: markdownlint-cli install failed (is Node set up?)"
fi

if has_lang terraform && ! excluded tflint; then
  echo "-> tflint"
  if ! command -v tflint >/dev/null 2>&1; then
    curl -sSfL https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash \
      || echo "  WARN: tflint install failed"
  fi
fi

if has_lang php && ! excluded phpcs; then
  echo "-> phpcs"
  if ! command -v phpcs >/dev/null 2>&1; then
    sudo apt-get update -qq && sudo apt-get install -y -qq php-codesniffer || echo "  WARN: phpcs install failed"
  fi
fi

exit 0
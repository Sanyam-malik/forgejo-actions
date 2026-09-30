#!/usr/bin/env bash
set -euo pipefail

# Shared repository/provider helpers for the tag and release actions.

normalize_provider() {
  local provider
  provider="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$provider" in
    gh|github) printf '%s\n' github ;;
    gl|gitlab) printf '%s\n' gitlab ;;
    gitea) printf '%s\n' gitea ;;
    forgejo) printf '%s\n' forgejo ;;
    onedev) printf '%s\n' onedev ;;
    *) printf '%s\n' "$provider" ;;
  esac
}

url_encode() {
  printf '%s' "$1" | jq -sRr @uri
}

repository_parts() {
  local input="${1:?repository URL is required}"
  local explicit_provider="${2:-}"
  local without_scheme path host

  input="${input%%\#*}"
  input="${input%%\?*}"
  if [[ "$input" =~ ^[^/:]+/[^/]+$ ]]; then
    # Keep compatibility with the original GitHub helper, which accepted
    # owner/repository in addition to a clone URL.
    case "$(normalize_provider "$explicit_provider")" in
      gitlab) host=gitlab.com ;;
      *) host=github.com ;;
    esac
    path="$input"
    REPO_URL="https://${host}/${path}.git"
  elif [[ "$input" =~ ^[^/@:]+@([^:]+):(.+)$ ]]; then
    host="${BASH_REMATCH[1]}"
    path="${BASH_REMATCH[2]}"
    REPO_URL="https://${host}/${path}"
  else
    without_scheme="${input#*://}"
    host="${without_scheme%%/*}"
    path="${without_scheme#*/}"
    if [[ "$without_scheme" == "$host" ]]; then
      path=""
    fi
    REPO_URL="$input"
  fi
  host="${host#*@}"
  path="${path#/}"
  path="${path%/}"
  path="${path%.git}"

  REPO_HOST="$(printf '%s' "$host" | tr '[:upper:]' '[:lower:]')"
  REPO_PATH="$path"
  REPO_PROVIDER="$(normalize_provider "$explicit_provider")"
  if [[ -z "$explicit_provider" ]]; then
    case "$REPO_HOST" in
      github.com) REPO_PROVIDER=github ;;
      gitlab.com) REPO_PROVIDER=gitlab ;;
      *onedev*) REPO_PROVIDER=onedev ;;
      *) REPO_PROVIDER=generic ;;
    esac
  fi

  # GitLab keeps the complete (possibly nested) namespace as the project ID.
  # Other supported providers use the first two path components for API calls.
  if [[ "$REPO_PROVIDER" == gitlab ]]; then
    REPO_PROJECT="$REPO_PATH"
    REPO_OWNER="${REPO_PATH%/*}"
    REPO_NAME="${REPO_PATH##*/}"
  else
    REPO_OWNER="${REPO_PATH%%/*}"
    REPO_NAME="${REPO_PATH#*/}"
    [[ "$REPO_OWNER" == "$REPO_NAME" ]] && REPO_NAME=""
    REPO_PROJECT="${REPO_OWNER}/${REPO_NAME}"
  fi
}

api_base_for() {
  local requested="${1:-}" provider="$2" host="$3" input_url="$4"
  if [[ -n "$requested" ]]; then
    printf '%s\n' "${requested%/}"
    return
  fi
  case "$provider" in
    github) printf '%s\n' "https://api.github.com" ;;
    gitlab)
      local scheme=https
      [[ "$input_url" == http://* ]] && scheme=http
      printf '%s\n' "${scheme}://${host}/api/v4"
      ;;
    gitea|forgejo)
      local scheme=https
      [[ "$input_url" == http://* ]] && scheme=http
      printf '%s\n' "${scheme}://${host}/api/v1"
      ;;
    *)
      local scheme=https
      [[ "$input_url" == http://* ]] && scheme=http
      # Self-hosted Gitea/Forgejo instances commonly use this API path even
      # when their hostname does not identify the product.
      printf '%s\n' "${scheme}://${host}/api/v1"
      ;;
  esac
}

pkg_cache_base() {
  local cache="${PKG_CACHE:-}"
  [[ -z "$cache" ]] && return 0
  case "$cache" in
    http://*|https://*) ;;
    *) cache="https://${cache}" ;;
  esac
  printf '%s\n' "${cache%/}"
}

github_api_base_with_cache() {
  local base="$1" cache
  cache="$(pkg_cache_base)"
  if [[ -n "$cache" && "$base" == "https://api.github.com" ]]; then
    printf '%s/api.github.com\n' "$cache"
  else
    printf '%s\n' "$base"
  fi
}

github_asset_url_with_cache() {
  local url="$1" cache
  cache="$(pkg_cache_base)"
  if [[ -n "$cache" && "$url" =~ ^https?://github\.com/ ]]; then
    printf '%s/github.com/%s\n' "$cache" "${url#*://github.com/}"
  else
    printf '%s\n' "$url"
  fi
}

api_auth_header() {
  local provider="$1" token="$2"
  case "$provider" in
    gitlab) printf 'PRIVATE-TOKEN: %s\n' "$token" ;;
    gitea|forgejo|generic) printf 'Authorization: token %s\n' "$token" ;;
    github|onedev|*) printf 'Authorization: Bearer %s\n' "$token" ;;
  esac
}

git_ls_remote() {
  local url="$1" token="${2:-}"
  if [[ -n "$token" && "$url" == http://* || -n "$token" && "$url" == https://* ]]; then
    local auth_scheme="Bearer"
    local auth_header="Authorization: ${auth_scheme} ${token}"
    GIT_TERMINAL_PROMPT=0 \
      GIT_CONFIG_COUNT=1 \
      GIT_CONFIG_KEY_0=http.extraHeader \
      GIT_CONFIG_VALUE_0="$auth_header" \
      git ls-remote --tags "$url"
  else
    GIT_TERMINAL_PROMPT=0 git ls-remote --tags "$url"
  fi
}

latest_tag_from_remote() {
  local url="$1" token="${2:-}"
  local tags
  tags="$(git_ls_remote "$url" "$token" |
    awk '$2 ~ /^refs\/tags\// {
      ref=$2
      sub(/^refs\/tags\//, "", ref)
      sub(/\^\{\}$/, "", ref)
      print ref
    }' | sort -u)"
  [[ -z "$tags" ]] && return 0
  if printf '1\n2\n' | sort -V >/dev/null 2>&1; then
    printf '%s\n' "$tags" | sort -Vu | tail -n 1
  else
    printf '%s\n' "$tags" | tail -n 1
  fi
}

tag_exists_remote() {
  local url="$1" tag="$2" token="${3:-}"
  git_ls_remote "$url" "$token" |
    awk -v wanted="$tag" '$2 == "refs/tags/" wanted || $2 == "refs/tags/" wanted "^{}" { found=1 } END { exit !found }'
}

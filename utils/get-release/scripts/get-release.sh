#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../_lib/repository.sh
source "$SCRIPT_DIR/../../_lib/repository.sh"

repository_parts "${REPO_INPUT}" "${PROVIDER_INPUT:-}"
version="${VERSION_INPUT:-latest}"
if [[ "$version" == "latest" ]]; then
  # Keep latest resolution in one place so this action and the legacy helper
  # have identical provider, mirror, and fallback behavior.
  exec "$SCRIPT_DIR/../../get-latest-release/scripts/get-release.sh"
fi

base="$(api_base_for "${API_URL_INPUT:-}" "$REPO_PROVIDER" "$REPO_HOST" "$REPO_URL_INPUT")"
base="$(github_api_base_with_cache "$base")"
cache="$(pkg_cache_base)"
encoded_version="$(url_encode "$version")"
endpoint=""
case "$REPO_PROVIDER" in
  github|gitea|forgejo) endpoint="${base}/repos/${REPO_PROJECT}/releases/tags/${encoded_version}" ;;
  gitlab) endpoint="${base}/projects/$(url_encode "$REPO_PROJECT")/releases/${encoded_version}" ;;
  onedev) endpoint="" ;;
  *) endpoint="${base}/repos/${REPO_PROJECT}/releases/tags/${encoded_version}" ;;
esac

response=""
if [[ -n "$endpoint" ]]; then
  if [[ -n "${TOKEN_INPUT:-}" ]]; then
    auth_header="$(api_auth_header "$REPO_PROVIDER" "$TOKEN_INPUT")"
    response="$(curl -fsSL --retry 5 --retry-delay 2 -H "$auth_header" "$endpoint" 2>/dev/null || true)"
  else
    response="$(curl -fsSL --retry 5 --retry-delay 2 "$endpoint" 2>/dev/null || true)"
  fi
fi

tag=""
assets="[]"
if [[ -n "$response" ]]; then
  tag="$(jq -r '.tag_name // empty' <<<"$response")"
  case "$REPO_PROVIDER" in
    gitlab)
      assets="$(jq -c '[.assets.links[]? | {name: (.name // ""), size: (.size // null), url: (.direct_asset_url // .url // "")}]' <<<"$response")"
      ;;
    *)
      assets="$(jq -c --arg mirror "$cache" '
        [.assets[]? | {
          name: (.name // ""),
          size: (.size // null),
          url: (.browser_download_url // .download_url // .url // "")
        } | .url = (if $mirror != "" and (.url | test("^https?://github[.]com/"))
                    then ($mirror + "/github.com/" + (.url | sub("^https?://github[.]com/"; "")))
                    else .url end)
      ]' <<<"$response")"
      ;;
  esac
fi

# REST release APIs are optional. A tag is still a useful release result on
# OneDev and other installations that only expose tags through git.
if [[ -z "$tag" ]]; then
  tag="$version"
  tag_exists_remote "$REPO_URL" "$tag" "${TOKEN_INPUT:-}" ||
    { echo "Release/tag '$version' was not found in ${REPO_INPUT}" >&2; exit 1; }
fi

printf 'tag=%s\n' "$tag" >> "$GITHUB_OUTPUT"
printf 'assets=%s\n' "$assets" >> "$GITHUB_OUTPUT"
printf 'Release tag: %s\n' "$tag"
printf 'Assets: %s\n' "$assets"

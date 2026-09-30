#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../_lib/repository.sh
source "$SCRIPT_DIR/../../_lib/repository.sh"

repository_parts "${REPO_URL_INPUT}" "${PROVIDER_INPUT:-}"
base="$(api_base_for "${API_URL_INPUT:-}" "$REPO_PROVIDER" "$REPO_HOST" "$REPO_URL_INPUT")"
base="$(github_api_base_with_cache "$base")"
cache="$(pkg_cache_base)"

endpoint=""
case "$REPO_PROVIDER" in
  github|gitea|forgejo)
    endpoint="${base}/repos/${REPO_PROJECT}/releases/latest"
    ;;
  gitlab)
    endpoint="${base}/projects/$(url_encode "$REPO_PROJECT")/releases/permalink/latest"
    ;;
  onedev)
    endpoint=""
    ;;
  *)
    # Generic self-hosted servers may expose a Gitea-compatible API.
    endpoint="${base}/repos/${REPO_PROJECT}/releases/latest"
    ;;
esac

response=""
if [[ -n "$endpoint" ]]; then
  if [[ -n "${TOKEN_INPUT:-}" ]]; then
    auth_header="$(api_auth_header "$REPO_PROVIDER" "$TOKEN_INPUT")"
    if response="$(curl -fsSL --retry 5 --retry-delay 2 -H "$auth_header" "$endpoint" 2>/dev/null)"; then
      :
    else
      response=""
    fi
  elif response="$(curl -fsSL --retry 5 --retry-delay 2 "$endpoint" 2>/dev/null)"; then
    :
  else
    response=""
  fi
fi

tag=""
assets="[]"
if [[ -n "$response" ]]; then
  tag="$(jq -r '.tag_name // .tag_name // empty' <<<"$response")"
  case "$REPO_PROVIDER" in
    gitlab)
      assets="$(jq -c '[.assets.links[]? | {name: (.name // ""), size: (.size // null), url: (.direct_asset_url // .url // "")}]' <<<"$response")"
      ;;
    *)
      assets="$(jq -c --arg mirror "$cache" '
        [.assets[]? | {
          name: (.name // ""),
          size: (.size // null),
          url: (
            .browser_download_url // .download_url // .url // ""
          )
        } | .url = (if $mirror != "" and (.url | test("^https?://github[.]com/"))
                    then ($mirror + "/github.com/" + (.url | sub("^https?://github[.]com/"; "")))
                    else .url end)
      ]' <<<"$response")"
      ;;
  esac
fi

# OneDev has no stable release API across versions. Git tags are the portable
# fallback and intentionally produce an empty asset list.
if [[ -z "$tag" ]]; then
  tag="$(latest_tag_from_remote "$REPO_URL" "${TOKEN_INPUT:-}" || true)"
fi
[[ -n "$tag" ]] || { echo "Unable to determine a release tag for ${REPO_URL_INPUT}" >&2; exit 1; }

printf 'tag=%s\n' "$tag" >> "$GITHUB_OUTPUT"
printf 'assets=%s\n' "$assets" >> "$GITHUB_OUTPUT"
printf 'Latest release tag: %s\n' "$tag"
printf 'Assets: %s\n' "$assets"

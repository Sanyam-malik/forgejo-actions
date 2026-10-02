#!/usr/bin/env bash
set -euo pipefail

repository="${REPOSITORY_INPUT:?repository is required}"
tag="${TAG_INPUT:?tag is required}"
token="${TOKEN_INPUT:?token is required}"
target="${TARGET_INPUT:-}"
name="${NAME_INPUT:-$tag}"
body_file="${BODY_FILE_INPUT:-RELEASE.md}"
placeholders="${PLACEHOLDERS_INPUT:-\{\}}"
api_base="${API_URL_INPUT:-}"

if [[ -z "$target" ]]; then
  target="$(git rev-parse HEAD)"
fi

if [[ "$repository" == */* && "$repository" != *://* ]]; then
  project="${repository%.git}"
  if [[ -z "$api_base" ]]; then
    server="${SERVER_URL:-https://github.com}"
    api_base="${server%/}/api/v1"
    [[ "$server" == "https://github.com" ]] && api_base="https://api.github.com"
  fi
else
  repository="${repository%.git}"
  without_scheme="${repository#*://}"
  host="${without_scheme%%/*}"
  project="${without_scheme#*/}"
  if [[ -z "$api_base" ]]; then
    if [[ "$host" == "github.com" ]]; then
      api_base="https://api.github.com"
    else
      scheme=https
      [[ "$repository" == http://* ]] && scheme=http
      api_base="${scheme}://${host}/api/v1"
    fi
  fi
fi

api_base="${api_base%/}"
project="${project#/}"
project="${project%/}"
project="${project%.git}"
[[ "$project" == */* ]] || { echo "::error::Repository must be owner/name: ${repository}" >&2; exit 1; }

auth_header="Authorization: Bearer ${token}"
case "$api_base" in
  */api/v1) auth_header="Authorization: token ${token}" ;;
esac

api() {
  local method="$1" endpoint="$2" payload="${3:-}"
  local args=(-fsSL --retry 5 --retry-delay 2 -X "$method" -H "$auth_header" -H "Accept: application/json")
  [[ -n "$payload" ]] && args+=( -H "Content-Type: application/json" --data "$payload" )
  curl "${args[@]}" "${api_base}${endpoint}"
}

if [[ -z "${body_file}" || ! -f "${body_file}" ]]; then
  echo "::error::Release body file not found: ${body_file}" >&2
  exit 1
fi

body="$(<"${body_file}")"

if ! jq -e 'type == "object"' >/dev/null 2>&1 <<<"${placeholders}"; then
  echo "::error::placeholders must be a JSON object." >&2
  exit 1
fi

if [[ "${placeholders}" != "{}" ]]; then
  body="$(printf '%s' "${body}" | jq -R -s --argjson values "${placeholders}" '
    reduce ($values | keys_unsorted[]) as $key
      (.;
       split("{{" + $key + "}}") |
       join(($values[$key] | tostring)))
  ')"
fi

if [[ ! "$target" =~ ^[0-9a-fA-F]{40}$ ]]; then
  encoded_target="$(jq -rn --arg value "$target" '$value|@uri')"
  target_response="$(api GET "/repos/${project}/git/ref/heads/${encoded_target}")"
  target="$(jq -r '.object.sha // empty' <<<"$target_response")"
  [[ -n "$target" ]] || { echo "::error::Unable to resolve target commit: ${TARGET_INPUT}" >&2; exit 1; }
fi

encoded_tag="$(jq -rn --arg value "$tag" '$value|@uri')"
ref_endpoint="/repos/${project}/git/ref/tags/${encoded_tag}"
ref_response=""
if ref_response="$(api GET "$ref_endpoint" 2>/dev/null)"; then
  existing_sha="$(jq -r '.object.sha // empty' <<<"$ref_response")"
  if [[ "$FORCE_TAG_INPUT" != "true" ]]; then
    if [[ "$existing_sha" != "$target" ]]; then
      echo "::error::Tag '$tag' already exists at ${existing_sha}; set force_tag=true to move it." >&2
      exit 1
    fi
  else
    api PATCH "$ref_endpoint" "$(jq -cn --arg sha "$target" '{sha:$sha,force:true}')" >/dev/null
  fi
else
  api POST "/repos/${project}/git/refs" \
    "$(jq -cn --arg ref "refs/tags/${tag}" --arg sha "$target" '{ref:$ref,sha:$sha}')" >/dev/null
fi

release_endpoint="/repos/${project}/releases/tags/${encoded_tag}"
release_payload="$(jq -cn \
  --arg tag "$tag" \
  --arg name "$name" \
  --arg body "$body" \
  --arg target "$target" \
  --argjson draft "${DRAFT_INPUT}" \
  --argjson prerelease "${PRERELEASE_INPUT}" \
  '{tag_name:$tag,name:$name,body:$body,target_commitish:$target,draft:$draft,prerelease:$prerelease}')"

release_response=""
if release_response="$(api GET "$release_endpoint" 2>/dev/null)"; then
  release_id="$(jq -r '.id // empty' <<<"$release_response")"
  release_response="$(api PATCH "/repos/${project}/releases/${release_id}" "$release_payload")"
else
  release_response="$(api POST "/repos/${project}/releases" "$release_payload")"
  release_id="$(jq -r '.id // empty' <<<"$release_response")"
fi

release_url="$(jq -r '.html_url // .url // empty' <<<"$release_response")"
[[ -n "$release_id" ]] || { echo "::error::Release API returned no release id." >&2; exit 1; }

printf 'tag=%s\n' "$tag" >> "$GITHUB_OUTPUT"
printf 'release_id=%s\n' "$release_id" >> "$GITHUB_OUTPUT"
printf 'release_url=%s\n' "$release_url" >> "$GITHUB_OUTPUT"
printf 'Created release %s (%s)\n' "$tag" "$release_url"

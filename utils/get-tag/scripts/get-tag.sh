#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../_lib/repository.sh
source "$SCRIPT_DIR/../../_lib/repository.sh"

repository_parts "${REPO_URL_INPUT}" "${PROVIDER_INPUT:-}"
version="${VERSION_INPUT:-latest}"
if [[ "$version" == "latest" ]]; then
  exec bash "$SCRIPT_DIR/../../get-latest-tag/scripts/get-latest-tag.sh"
else
  if ! tag_exists_remote "$REPO_URL" "$version" "${TOKEN_INPUT:-}"; then
    echo "Tag '$version' was not found in ${REPO_URL_INPUT}" >&2
    exit 1
  fi
  tag="$version"
fi

[[ -n "$tag" ]] || { echo "No tag found for ${REPO_URL_INPUT}" >&2; exit 1; }
printf 'tag=%s\n' "$tag" >> "$GITHUB_OUTPUT"
printf 'Tag: %s\n' "$tag"

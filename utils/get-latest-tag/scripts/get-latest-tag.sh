#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../_lib/repository.sh
source "$SCRIPT_DIR/../../_lib/repository.sh"

repository_parts "${REPO_URL_INPUT}" "${PROVIDER_INPUT:-}"
tag="$(latest_tag_from_remote "$REPO_URL" "${TOKEN_INPUT:-}")"
if [[ -z "$tag" ]]; then
  echo "No tags found for ${REPO_URL_INPUT}" >&2
  exit 1
fi

printf 'tag=%s\n' "$tag" >> "$GITHUB_OUTPUT"
printf 'Latest tag: %s\n' "$tag"

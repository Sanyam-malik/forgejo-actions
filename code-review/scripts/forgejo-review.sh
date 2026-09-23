#!/usr/bin/env bash

set -euo pipefail

RESULT_FILE="${1:?Usage: forgejo-review.sh <reviewdog-results-file>}"

: "${FORGEJO_TOKEN:?FORGEJO_TOKEN is required}"
: "${FORGEJO_API_URL:?FORGEJO_API_URL is required}"

API_URL="${FORGEJO_API_URL%/}"

REPOSITORY="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
EVENT_FILE="${GITHUB_EVENT_PATH:?GITHUB_EVENT_PATH is required}"

FILTER_MODE="${REVIEW_FILTER_MODE:-changed_files}"

OWNER="${REPOSITORY%%/*}"
REPO="${REPOSITORY#*/}"

echo "========================================"
echo "Forgejo Code Review"
echo "========================================"
echo "Repository : ${OWNER}/${REPO}"
echo "API URL    : ${API_URL}"
echo "Filter     : ${FILTER_MODE}"
echo

# ------------------------------------------------------------
# Validate filter
# ------------------------------------------------------------

case "$FILTER_MODE" in
    changed_files|added|diff_context|file|nofilter)
        ;;
    *)
        echo "Unsupported filter mode: $FILTER_MODE"
        exit 1
        ;;
esac

# ------------------------------------------------------------
# Ensure curl is installed
# ------------------------------------------------------------

if ! command -v curl >/dev/null 2>&1; then

    echo "curl not found. Installing curl..."

    if command -v apt-get >/dev/null 2>&1; then

        sudo apt-get update
        sudo apt-get install -y curl

    elif command -v dnf >/dev/null 2>&1; then

        sudo dnf install -y curl

    elif command -v yum >/dev/null 2>&1; then

        sudo yum install -y curl

    elif command -v apk >/dev/null 2>&1; then

        sudo apk add --no-cache curl

    elif command -v zypper >/dev/null 2>&1; then

        sudo zypper install -y curl

    else
        echo "ERROR: Could not install curl."
        echo "Supported package managers: apt-get, dnf, yum, apk, zypper."
        exit 1
    fi
fi

CURL="$(command -v curl)"

echo "curl       : ${CURL}"

# ------------------------------------------------------------
# Determine PR number
# ------------------------------------------------------------

PR_NUMBER="$(
    python3 - "$EVENT_FILE" <<'PY'
import json
import sys

event_file = sys.argv[1]

with open(event_file, "r", encoding="utf-8") as f:
    event = json.load(f)

number = None

pull_request = event.get("pull_request")

if isinstance(pull_request, dict):
    number = pull_request.get("number")

if not number:
    number = event.get("number")

if number:
    print(number)
PY
)"

if [ -z "$PR_NUMBER" ]; then
    echo "ERROR: Could not determine pull request number."
    exit 1
fi

echo "Pull request: #${PR_NUMBER}"

# ------------------------------------------------------------
# API helper
# ------------------------------------------------------------

forgejo_api() {

    local METHOD="$1"
    local PATH="$2"

    shift 2

    "$CURL" \
        --fail \
        --silent \
        --show-error \
        --location \
        --request "$METHOD" \
        --header "Authorization: token ${FORGEJO_TOKEN}" \
        --header "Accept: application/json" \
        --header "Content-Type: application/json" \
        "$@" \
        "${API_URL}${PATH}"
}

# ------------------------------------------------------------
# Read PR
# ------------------------------------------------------------

PR_JSON="$(
    forgejo_api \
        GET \
        "/repos/${OWNER}/${REPO}/pulls/${PR_NUMBER}"
)"

printf '%s\n' "$PR_JSON" > .forgejo-pr.json

BASE_SHA="$(
    python3 - .forgejo-pr.json <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    data = json.load(f)

print(data.get("base", {}).get("sha", ""))
PY
)"

HEAD_SHA="$(
    python3 - .forgejo-pr.json <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    data = json.load(f)

print(data.get("head", {}).get("sha", ""))
PY
)"

if [ -z "$HEAD_SHA" ]; then
    echo "ERROR: Could not determine pull request head SHA."
    exit 1
fi

echo "Base SHA: ${BASE_SHA}"
echo "Head SHA: ${HEAD_SHA}"

# ------------------------------------------------------------
# Get changed files
# ------------------------------------------------------------

forgejo_api \
    GET \
    "/repos/${OWNER}/${REPO}/pulls/${PR_NUMBER}/files" \
    > .forgejo-pr-files.json

echo
echo "Changed files:"

python3 - .forgejo-pr-files.json <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    files = json.load(f)

for item in files:
    filename = item.get("filename", "")
    status = item.get("status", "")

    if status:
        print(f"  {filename} ({status})")
    else:
        print(f"  {filename}")
PY

# ------------------------------------------------------------
# Parse reviewdog output and post Forgejo review
# ------------------------------------------------------------

python3 \
    "${GITHUB_ACTION_PATH}/scripts/forgejo-review.py" \
    "$RESULT_FILE" \
    .forgejo-pr-files.json \
    "$FILTER_MODE" \
    "$API_URL" \
    "$OWNER" \
    "$REPO" \
    "$PR_NUMBER" \
    "$HEAD_SHA" \
    "$FORGEJO_TOKEN"
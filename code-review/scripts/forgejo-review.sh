#!/usr/bin/env bash

set -euo pipefail

RESULT_FILE="${1:?Usage: forgejo-review.sh <reviewdog-output>}"

: "${FORGEJO_TOKEN:?FORGEJO_TOKEN is required}"
: "${FORGEJO_API_URL:?FORGEJO_API_URL is required}"

API_URL="${FORGEJO_API_URL%/}"

REPOSITORY="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"

OWNER="${REPOSITORY%%/*}"
REPO="${REPOSITORY#*/}"

EVENT_FILE="${GITHUB_EVENT_PATH:?GITHUB_EVENT_PATH is required}"

echo "Forgejo repository: ${OWNER}/${REPO}"
echo "Forgejo API: ${API_URL}"

# ------------------------------------------------------------
# Determine pull request number
# ------------------------------------------------------------

PR_NUMBER="$(
    python3 - "$EVENT_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    event = json.load(f)

pr = event.get("pull_request", {})

number = (
    pr.get("number")
    or event.get("number")
)

if number:
    print(number)
PY
)"

if [ -z "$PR_NUMBER" ]; then
    echo "ERROR: Could not determine pull request number."
    echo "Event payload:"
    cat "$EVENT_FILE"
    exit 1
fi

echo "Pull request: #$PR_NUMBER"

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

forgejo_api() {
    local method="$1"
    local url="$2"

    shift 2

    curl \
        --fail \
        --silent \
        --show-error \
        --request "$method" \
        --header "Authorization: token ${FORGEJO_TOKEN}" \
        --header "Content-Type: application/json" \
        "$@" \
        "${API_URL}${url}"
}

# ------------------------------------------------------------
# Read reviewdog output
# ------------------------------------------------------------

if [ ! -f "$RESULT_FILE" ]; then
    echo "No reviewdog result file found."
    exit 0
fi

if [ ! -s "$RESULT_FILE" ]; then
    echo "Reviewdog produced no findings."
    exit 0
fi

echo
echo "Reviewdog findings:"
cat "$RESULT_FILE"

# ------------------------------------------------------------
# Convert reviewdog output to JSON
# ------------------------------------------------------------

python3 - "$RESULT_FILE" "$API_URL" "$OWNER" "$REPO" "$PR_NUMBER" "$FORGEJO_TOKEN" <<'PY'
import json
import os
import re
import sys
import urllib.request
import urllib.error

result_file = sys.argv[1]
api_url = sys.argv[2]
owner = sys.argv[3]
repo = sys.argv[4]
pr_number = sys.argv[5]
token = sys.argv[6]

# ------------------------------------------------------------
# Parse reviewdog local output
#
# Expected common format:
#
# file:line:column: message
# file:line: message
#
# The parser intentionally accepts several common forms.
# ------------------------------------------------------------

findings = []

patterns = [
    re.compile(
        r"^(?P<file>.+?):(?P<line>\d+):(?P<column>\d+):\s*(?P<message>.+)$"
    ),
    re.compile(
        r"^(?P<file>.+?):(?P<line>\d+):\s*(?P<message>.+)$"
    ),
    re.compile(
        r"^(?P<file>.+?)\((?P<line>\d+),(?P<column>\d+)\):\s*(?P<message>.+)$"
    ),
]

with open(result_file, "r", encoding="utf-8", errors="replace") as f:
    for raw in f:
        line = raw.strip()

        if not line:
            continue

        matched = None

        for pattern in patterns:
            match = pattern.match(line)

            if match:
                matched = match
                break

        if not matched:
            continue

        data = matched.groupdict()

        findings.append({
            "file": data["file"],
            "line": int(data["line"]),
            "column": int(data.get("column") or 1),
            "message": data["message"],
        })

print(f"Parsed {len(findings)} finding(s).")

if not findings:
    print("No machine-readable findings found.")
    sys.exit(0)

# ------------------------------------------------------------
# Forgejo API helper
# ------------------------------------------------------------

def request(method, path, payload=None):
    url = f"{api_url}{path}"

    body = None

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            raw = response.read()

            if not raw:
                return {}

            return json.loads(raw)

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")

        print(
            f"Forgejo API error {e.code}: {body}",
            file=sys.stderr,
        )

        raise


# ------------------------------------------------------------
# Get PR information
# ------------------------------------------------------------

pr = request(
    "GET",
    f"/repos/{owner}/{repo}/pulls/{pr_number}",
)

print(
    f"PR head: {pr.get('head', {}).get('sha', '')}"
)

print(
    f"PR base: {pr.get('base', {}).get('sha', '')}"
)

# ------------------------------------------------------------
# Get changed files
# ------------------------------------------------------------

files = request(
    "GET",
    f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
)

changed_files = {}

for item in files:
    filename = item.get("filename")

    if not filename:
        continue

    changed_files[filename] = item

print(f"Changed files: {len(changed_files)}")

# ------------------------------------------------------------
# Only report findings that belong to changed files.
#
# This provides a second layer of protection even when reviewdog
# filtering is configured as "file" or "nofilter".
# ------------------------------------------------------------

for finding in findings:
    filename = finding["file"]

    if filename not in changed_files:
        continue

    message = (
        f"**{finding['message']}**\n\n"
        f"_reviewdog_"
    )

    payload = {
        "body": message,
        "path": filename,
        "line": finding["line"],
        "side": "right",
    }

    try:
        request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            {
                "body": message,
                "event": "COMMENT",
                "comments": [
                    {
                        "path": filename,
                        "line": finding["line"],
                        "side": "RIGHT",
                        "body": message,
                    }
                ],
            },
        )

        print(
            f"Posted comment: {filename}:{finding['line']}"
        )

    except Exception as exc:
        print(
            f"Failed to post comment for "
            f"{filename}:{finding['line']}: {exc}",
            file=sys.stderr,
        )

PY
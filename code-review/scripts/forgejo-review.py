#!/usr/bin/env python3

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


# ============================================================
# Arguments
# ============================================================

if len(sys.argv) != 9:
    print(
        "Usage: forgejo-review.py "
        "<results-file> "
        "<pr-files-json> "
        "<filter-mode> "
        "<api-url> "
        "<owner> "
        "<repo> "
        "<pr-number> "
        "<token>",
        file=sys.stderr,
    )
    sys.exit(1)


RESULT_FILE = Path(sys.argv[1])
PR_FILES_FILE = Path(sys.argv[2])
FILTER_MODE = sys.argv[3]
API_URL = sys.argv[4].rstrip("/")
OWNER = sys.argv[5]
REPO = sys.argv[6]
PR_NUMBER = sys.argv[7]
TOKEN = sys.argv[8]


# ============================================================
# Validation
# ============================================================

VALID_FILTERS = {
    "changed_files",
    "added",
    "diff_context",
    "file",
    "nofilter",
}

if FILTER_MODE not in VALID_FILTERS:
    print(
        f"Unsupported filter mode: {FILTER_MODE}",
        file=sys.stderr,
    )
    sys.exit(1)


# ============================================================
# Load files
# ============================================================

if not RESULT_FILE.exists():
    print(
        f"ERROR: Reviewdog result file does not exist: {RESULT_FILE}",
        file=sys.stderr,
    )
    sys.exit(1)

if not PR_FILES_FILE.exists():
    print(
        f"ERROR: PR files file does not exist: {PR_FILES_FILE}",
        file=sys.stderr,
    )
    sys.exit(1)


with RESULT_FILE.open("r", encoding="utf-8", errors="replace") as f:
    reviewdog_output = f.read()


with PR_FILES_FILE.open("r", encoding="utf-8") as f:
    changed_files = json.load(f)


if not isinstance(changed_files, list):
    print(
        "ERROR: PR files response is not a JSON array.",
        file=sys.stderr,
    )
    sys.exit(1)


# ============================================================
# Helpers
# ============================================================

def normalize_path(path):
    """Normalize a repository path."""

    if not path:
        return ""

    path = path.strip()

    if path.startswith("./"):
        path = path[2:]

    path = path.replace("\\", "/")

    return path


def normalize_status(status):
    """Normalize Forgejo file status."""

    if not status:
        return ""

    return str(status).strip().lower()


def is_deleted_file(item):
    return normalize_status(item.get("status")) == "deleted"


def is_reviewable_changed_file(item):
    """
    Files that belong to the PR's changed-file scope.

    We intentionally include deleted files because their changes
    are still part of the PR review.
    """

    return normalize_status(item.get("status")) in {
        "added",
        "modified",
        "renamed",
        "deleted",
    }


def get_file_path(item):
    """
    Get the current repository path.

    Forgejo normally exposes `filename`. For renamed files,
    `previous_filename` contains the old path.
    """

    filename = normalize_path(item.get("filename"))

    if filename:
        return filename

    return normalize_path(item.get("previous_filename"))


# ============================================================
# Parse reviewdog findings
# ============================================================

def parse_finding(line):
    """
    Parse common reviewdog local reporter formats.

    Supported examples:

        file:line:column: message
        file:line: message
        file(line,column): message
        file(line): message

    The parser intentionally keeps the message intact.
    """

    line = line.rstrip("\n")

    if not line.strip():
        return None

    # --------------------------------------------------------
    # file:line:column: message
    # --------------------------------------------------------

    match = re.match(
        r"^(.*?):(\d+):(\d+):\s*(.*)$",
        line,
    )

    if match:
        path = normalize_path(match.group(1))
        line_number = int(match.group(2))
        column = int(match.group(3))
        message = match.group(4).strip()

        return {
            "file": path,
            "line": line_number,
            "column": column,
            "message": message,
        }

    # --------------------------------------------------------
    # file:line: message
    # --------------------------------------------------------

    match = re.match(
        r"^(.*?):(\d+):\s*(.*)$",
        line,
    )

    if match:
        path = normalize_path(match.group(1))
        line_number = int(match.group(2))
        message = match.group(3).strip()

        return {
            "file": path,
            "line": line_number,
            "column": None,
            "message": message,
        }

    # --------------------------------------------------------
    # file(line,column): message
    # --------------------------------------------------------

    match = re.match(
        r"^(.*?)\((\d+),(\d+)\):\s*(.*)$",
        line,
    )

    if match:
        path = normalize_path(match.group(1))
        line_number = int(match.group(2))
        column = int(match.group(3))
        message = match.group(4).strip()

        return {
            "file": path,
            "line": line_number,
            "column": column,
            "message": message,
        }

    # --------------------------------------------------------
    # file(line): message
    # --------------------------------------------------------

    match = re.match(
        r"^(.*?)\((\d+)\):\s*(.*)$",
        line,
    )

    if match:
        path = normalize_path(match.group(1))
        line_number = int(match.group(2))
        message = match.group(3).strip()

        return {
            "file": path,
            "line": line_number,
            "column": None,
            "message": message,
        }

    return None


findings = []

for line in reviewdog_output.splitlines():
    finding = parse_finding(line)

    if finding is not None:
        findings.append(finding)


print(f"Parsed findings: {len(findings)}")
print(f"Changed files: {len(changed_files)}")


# ============================================================
# Build changed-file indexes
# ============================================================

changed_file_map = {}

for item in changed_files:
    path = get_file_path(item)

    if not path:
        continue

    changed_file_map[path] = item


changed_paths = set(changed_file_map.keys())


# ============================================================
# Parse patches
# ============================================================

def parse_patch(patch):
    """
    Parse a unified diff and return:

      added_lines
      changed_context_lines

    `added_lines` contains current/right-side line numbers.

    `changed_context_lines` contains lines that are part of
    a changed hunk, including context around additions.
    """

    added_lines = set()
    context_lines = set()

    if not patch:
        return added_lines, context_lines

    current_line = None

    for raw_line in patch.splitlines():

        # ----------------------------------------------------
        # Hunk header
        #
        # @@ -old,count +new,count @@
        # ----------------------------------------------------

        match = re.match(
            r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@",
            raw_line,
        )

        if match:
            current_line = int(match.group(1))
            continue

        if current_line is None:
            continue

        # ----------------------------------------------------
        # Added line
        # ----------------------------------------------------

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            added_lines.add(current_line)
            context_lines.add(current_line)
            current_line += 1
            continue

        # ----------------------------------------------------
        # Deleted line
        #
        # Deleted lines do not exist on the right side.
        # ----------------------------------------------------

        if raw_line.startswith("-") and not raw_line.startswith("---"):
            continue

        # ----------------------------------------------------
        # Context line
        # ----------------------------------------------------

        if raw_line.startswith(" "):
            context_lines.add(current_line)
            current_line += 1
            continue

        # Unknown diff metadata.
        if raw_line.startswith("\\"):
            continue

    return added_lines, context_lines


file_diff_info = {}

for item in changed_files:

    path = get_file_path(item)

    if not path:
        continue

    patch = item.get("patch") or ""

    added_lines, context_lines = parse_patch(patch)

    file_diff_info[path] = {
        "status": normalize_status(item.get("status")),
        "added_lines": added_lines,
        "context_lines": context_lines,
        "patch": patch,
    }


# ============================================================
# Filtering
# ============================================================

def filter_changed_files(items):
    """
    Keep every finding belonging to a file changed by the PR.

    This intentionally does NOT require the finding's line to be
    an added line.

    Therefore:

        modified file + old line      -> included
        modified file + new line      -> included
        added file                    -> included
        renamed file                  -> included
        deleted file                 -> included
    """

    result = []

    for finding in items:
        path = normalize_path(finding["file"])

        if path in changed_paths:
            result.append(finding)

    return result


def filter_added_lines(items):
    """
    Keep findings whose reported line is an added line.

    This preserves the old `added` behavior.
    """

    result = []

    for finding in items:

        path = normalize_path(finding["file"])
        line_number = finding["line"]

        info = file_diff_info.get(path)

        if not info:
            continue

        if line_number in info["added_lines"]:
            result.append(finding)

    return result


def filter_diff_context(items):
    """
    Keep findings that fall anywhere inside a changed diff hunk.
    """

    result = []

    for finding in items:

        path = normalize_path(finding["file"])
        line_number = finding["line"]

        info = file_diff_info.get(path)

        if not info:
            continue

        if line_number in info["context_lines"]:
            result.append(finding)

    return result


def filter_file(items):
    """
    Keep findings for PR files regardless of line location.

    This is effectively the same file-level scope as
    changed_files, but is retained as a separate mode for
    compatibility.
    """

    return filter_changed_files(items)


if FILTER_MODE == "changed_files":
    filtered_findings = filter_changed_files(findings)

elif FILTER_MODE == "added":
    filtered_findings = filter_added_lines(findings)

elif FILTER_MODE == "diff_context":
    filtered_findings = filter_diff_context(findings)

elif FILTER_MODE == "file":
    filtered_findings = filter_file(findings)

elif FILTER_MODE == "nofilter":
    filtered_findings = findings

else:
    filtered_findings = []


# ============================================================
# Deduplicate findings
# ============================================================

deduplicated = []
seen = set()

for finding in filtered_findings:

    key = (
        finding["file"],
        finding["line"],
        finding.get("column"),
        finding["message"],
    )

    if key in seen:
        continue

    seen.add(key)
    deduplicated.append(finding)


filtered_findings = deduplicated


print(
    f"Findings after '{FILTER_MODE}' filtering: "
    f"{len(filtered_findings)}"
)


# ============================================================
# No findings
# ============================================================

if not filtered_findings:
    print(
        f"No findings matched the configured Forgejo filter mode."
    )
    sys.exit(0)


# ============================================================
# Build Forgejo review comments
# ============================================================

comments = []
general_comments = []

for finding in filtered_findings:

    path = normalize_path(finding["file"])
    line_number = finding["line"]

    info = file_diff_info.get(path, {})

    status = info.get("status", "")

    message = finding["message"]

    body = (
        f"{message}\n\n"
        "_Automated review by reviewdog._"
    )

    # --------------------------------------------------------
    # Deleted file
    #
    # A deleted file has no current RIGHT-side line.
    # Keep the finding, but don't create an invalid inline
    # comment against the current file.
    # --------------------------------------------------------

    if status == "deleted":

        general_comments.append(
            f"**{path}:{line_number}** — {message}"
        )

        continue

    # --------------------------------------------------------
    # Normal current-side finding
    # --------------------------------------------------------

    if not line_number or line_number < 1:

        general_comments.append(
            f"**{path}** — {message}"
        )

        continue

    comment = {
        "path": path,
        "line": line_number,
        "side": "RIGHT",
        "body": body,
    }

    comments.append(comment)


# ============================================================
# Review body
# ============================================================

review_body = (
    "Automated multi-language code review by reviewdog."
)

if general_comments:

    review_body += "\n\n"

    review_body += (
        "### Findings requiring general review\n\n"
    )

    for item in general_comments:
        review_body += f"- {item}\n"


# ============================================================
# Nothing can be posted inline
# ============================================================

if not comments and not general_comments:

    print("No comments to post.")
    sys.exit(0)


# ============================================================
# Forgejo API
# ============================================================

review_url = (
    f"{API_URL}"
    f"/repos/{OWNER}/{REPO}"
    f"/pulls/{PR_NUMBER}/reviews"
)


payload = {
    "body": review_body,
    "event": "COMMENT",
}


if comments:
    payload["comments"] = comments


request_body = json.dumps(payload).encode("utf-8")


request = urllib.request.Request(
    review_url,
    data=request_body,
    method="POST",
)

request.add_header(
    "Authorization",
    f"token {TOKEN}",
)

request.add_header(
    "Accept",
    "application/json",
)

request.add_header(
    "Content-Type",
    "application/json",
)


# ============================================================
# Post review
# ============================================================

try:

    with urllib.request.urlopen(
        request,
        timeout=60,
    ) as response:

        response_body = response.read().decode(
            "utf-8",
            errors="replace",
        )

        status_code = response.status

        print(
            f"Forgejo review posted successfully "
            f"(HTTP {status_code})."
        )

        if response_body:
            try:
                response_json = json.loads(response_body)

                review_id = response_json.get("id")

                if review_id:
                    print(
                        f"Review ID: {review_id}"
                    )

            except json.JSONDecodeError:
                pass

except urllib.error.HTTPError as exc:

    response_body = exc.read().decode(
        "utf-8",
        errors="replace",
    )

    print(
        f"ERROR: Forgejo API returned HTTP "
        f"{exc.code}.",
        file=sys.stderr,
    )

    if response_body:
        print(
            response_body,
            file=sys.stderr,
        )

    sys.exit(1)

except urllib.error.URLError as exc:

    print(
        f"ERROR: Could not connect to Forgejo: {exc}",
        file=sys.stderr,
    )

    sys.exit(1)
#!/usr/bin/env python3

import json
import re
import sys
import urllib.request
import urllib.error


RESULT_FILE = sys.argv[1]
FILES_FILE = sys.argv[2]
FILTER_MODE = sys.argv[3]
API_URL = sys.argv[4].rstrip("/")
OWNER = sys.argv[5]
REPO = sys.argv[6]
PR_NUMBER = sys.argv[7]
TOKEN = sys.argv[8]


# ============================================================
# Helpers
# ============================================================

def api_request(method, path, payload=None):

    url = f"{API_URL}{path}"

    data = None

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request) as response:
            body = response.read()

            if not body:
                return {}

            return json.loads(body)

    except urllib.error.HTTPError as exc:

        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        print(
            f"Forgejo API error {exc.code}: {body}",
            file=sys.stderr,
        )

        raise


# ============================================================
# Parse reviewdog output
# ============================================================

def parse_findings():

    findings = []

    patterns = [

        # file:line:column: message
        re.compile(
            r"^(?P<file>.+?):"
            r"(?P<line>\d+):"
            r"(?P<column>\d+):\s*"
            r"(?P<message>.+)$"
        ),

        # file:line: message
        re.compile(
            r"^(?P<file>.+?):"
            r"(?P<line>\d+):\s*"
            r"(?P<message>.+)$"
        ),

        # file(line,column): message
        re.compile(
            r"^(?P<file>.+?)"
            r"\((?P<line>\d+),"
            r"(?P<column>\d+)\):\s*"
            r"(?P<message>.+)$"
        ),
    ]

    with open(
        RESULT_FILE,
        "r",
        encoding="utf-8",
        errors="replace",
    ) as file:

        for raw_line in file:

            line = raw_line.strip()

            if not line:
                continue

            for pattern in patterns:

                match = pattern.match(line)

                if not match:
                    continue

                data = match.groupdict()

                findings.append({
                    "file": data["file"],
                    "line": int(data["line"]),
                    "column": int(
                        data.get("column") or 1
                    ),
                    "message": data["message"],
                })

                break

    return findings


# ============================================================
# Parse changed files
# ============================================================

def load_changed_files():

    with open(
        FILES_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    result = {}

    for item in data:

        filename = item.get("filename")

        if not filename:
            continue

        result[filename] = item

    return result


# ============================================================
# Parse unified diff
# ============================================================

def parse_added_lines(patch):

    added = set()

    if not patch:
        return added

    current_line = None

    for raw in patch.splitlines():

        line = raw

        # Example:
        #
        # @@ -10,5 +10,8 @@
        #

        match = re.match(
            r"^@@ -\d+(?:,\d+)? "
            r"\+(\d+)(?:,\d+)? @@",
            line,
        )

        if match:

            current_line = int(
                match.group(1)
            )

            continue

        if current_line is None:
            continue

        if line.startswith("+++"):
            continue

        if line.startswith("+"):

            added.add(current_line)

            current_line += 1

        elif line.startswith("-"):

            pass

        else:

            current_line += 1

    return added


def parse_context_lines(patch):

    lines = set()

    if not patch:
        return lines

    added_lines = parse_added_lines(patch)

    for line in added_lines:

        for offset in range(-3, 4):

            if line + offset > 0:
                lines.add(line + offset)

    return lines


# ============================================================
# Filter findings
# ============================================================

def filter_findings(findings, changed_files):

    filtered = []

    for finding in findings:

        filename = finding["file"]

        if filename.startswith("./"):
            filename = filename[2:]

        finding["file"] = filename

        file_info = changed_files.get(filename)

        # ----------------------------------------------------
        # nofilter
        # ----------------------------------------------------

        if FILTER_MODE == "nofilter":

            filtered.append(finding)
            continue

        # ----------------------------------------------------
        # File not changed
        # ----------------------------------------------------

        if file_info is None:
            continue

        patch = file_info.get("patch") or ""

        # ----------------------------------------------------
        # file
        # ----------------------------------------------------

        if FILTER_MODE == "file":

            filtered.append(finding)
            continue

        # ----------------------------------------------------
        # added
        # ----------------------------------------------------

        if FILTER_MODE == "added":

            added_lines = parse_added_lines(
                patch
            )

            if finding["line"] in added_lines:
                filtered.append(finding)

            continue

        # ----------------------------------------------------
        # diff_context
        # ----------------------------------------------------

        if FILTER_MODE == "diff_context":

            context_lines = parse_context_lines(
                patch
            )

            if finding["line"] in context_lines:
                filtered.append(finding)

            continue

    return filtered


# ============================================================
# Main
# ============================================================

print(
    "Reading reviewdog findings..."
)

findings = parse_findings()

print(
    f"Parsed findings: {len(findings)}"
)

if not findings:
    print(
        "No findings to report."
    )

    sys.exit(0)


changed_files = load_changed_files()

print(
    f"Changed files: {len(changed_files)}"
)

findings = filter_findings(
    findings,
    changed_files,
)

print(
    f"Findings after '{FILTER_MODE}' filtering: "
    f"{len(findings)}"
)

if not findings:

    print(
        "No findings matched the configured "
        "Forgejo filter mode."
    )

    sys.exit(0)


# ============================================================
# Build Forgejo review comments
# ============================================================

comments = []

seen = set()

for finding in findings:

    key = (
        finding["file"],
        finding["line"],
        finding["message"],
    )

    if key in seen:
        continue

    seen.add(key)

    comments.append({
        "path": finding["file"],
        "line": finding["line"],
        "side": "RIGHT",
        "body": (
            f"{finding['message']}\n\n"
            f"_Automated review by reviewdog_"
        ),
    })


if not comments:

    print(
        "No comments to submit."
    )

    sys.exit(0)


print(
    f"Submitting {len(comments)} inline comment(s)..."
)


# ============================================================
# Submit one Forgejo review
# ============================================================

payload = {
    "body": (
        "Automated multi-language code review "
        "by reviewdog."
    ),
    "event": "COMMENT",
    "comments": comments,
}


api_request(
    "POST",
    f"/repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/reviews",
    payload,
)

print(
    "Forgejo review submitted successfully."
)
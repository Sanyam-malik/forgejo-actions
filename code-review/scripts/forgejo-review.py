#!/usr/bin/env python3

import json
import re
import sys
import urllib.error
import urllib.request


VALID_FILTERS = {
    "changed_files",
    "added",
    "diff_context",
    "file",
    "nofilter",
}

CHANGED_FILE_STATUSES = {
    "added",
    "modified",
    "renamed",
    "deleted",
}


def die(message):
    print(f"ERROR: {message}")
    sys.exit(1)


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        die(f"Failed to read JSON file: {exc}")


# ------------------------------------------------------------
# Path handling
# ------------------------------------------------------------

def normalize_path(path):
    path = path.strip().strip("\"'")

    path = path.replace("\\", "/")

    while path.startswith("./"):
        path = path[2:]

    while path.startswith("/"):
        path = path[1:]

    return path


# ------------------------------------------------------------
# Reviewdog parsing
# ------------------------------------------------------------

def parse_reviewdog_line(line):
    """
    Supports reviewdog/local output such as:

        AGENTS.md:5:81 error MD013/line-length ...
        README.md:17:5 error MD060/table-column-style ...
        file.java:42:10: message
        file.java:42: message
        file.java:42 message

    Returns:

        {
            "path": str,
            "line": int,
            "column": int | None,
            "message": str
        }

    or None.
    """

    line = line.rstrip("\n")

    if not line.strip():
        return None

    # --------------------------------------------------------
    # file:line:column message
    #
    # Current reviewdog format:
    #
    # AGENTS.md:5:81 error MD013/line-length ...
    # --------------------------------------------------------

    match = re.match(
        r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+)"
        r"\s+(?P<message>.+)$",
        line,
    )

    if match:
        return {
            "path": normalize_path(match.group("path")),
            "line": int(match.group("line")),
            "column": int(match.group("column")),
            "message": match.group("message").strip(),
        }

    # --------------------------------------------------------
    # file:line:column: message
    # --------------------------------------------------------

    match = re.match(
        r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+):"
        r"\s*(?P<message>.+)$",
        line,
    )

    if match:
        return {
            "path": normalize_path(match.group("path")),
            "line": int(match.group("line")),
            "column": int(match.group("column")),
            "message": match.group("message").strip(),
        }

    # --------------------------------------------------------
    # file:line: message
    # --------------------------------------------------------

    match = re.match(
        r"^(?P<path>.+?):(?P<line>\d+):"
        r"\s*(?P<message>.+)$",
        line,
    )

    if match:
        return {
            "path": normalize_path(match.group("path")),
            "line": int(match.group("line")),
            "column": None,
            "message": match.group("message").strip(),
        }

    # --------------------------------------------------------
    # file:line message
    # --------------------------------------------------------

    match = re.match(
        r"^(?P<path>.+?):(?P<line>\d+)"
        r"\s+(?P<message>.+)$",
        line,
    )

    if match:
        return {
            "path": normalize_path(match.group("path")),
            "line": int(match.group("line")),
            "column": None,
            "message": match.group("message").strip(),
        }

    return None


def parse_findings(result_file):
    findings = []

    with open(
        result_file,
        "r",
        encoding="utf-8",
        errors="replace",
    ) as f:
        for raw_line in f:
            finding = parse_reviewdog_line(raw_line)

            if finding is not None:
                findings.append(finding)

    return findings


# ------------------------------------------------------------
# Forgejo changed files
# ------------------------------------------------------------

def normalize_status(item):
    """
    Normalize Forgejo file status.

    Forgejo may report:

        added
        modified
        changed
        renamed
        deleted

    Internally we treat "changed" as "modified".
    """

    status = str(
        item.get("status", "")
    ).lower().strip()

    # Forgejo can report "changed".
    if status == "changed":
        return "modified"

    if status in {
        "added",
        "modified",
        "renamed",
        "deleted",
    }:
        return status

    # --------------------------------------------------------
    # Fallback based on additions/deletions
    # --------------------------------------------------------

    additions = item.get(
        "additions",
        0,
    ) or 0

    deletions = item.get(
        "deletions",
        0,
    ) or 0

    if additions > 0 and deletions == 0:
        return "added"

    if deletions > 0 and additions == 0:
        return "deleted"

    if additions > 0 or deletions > 0:
        return "modified"

    # Unknown status:
    # treat the file as modified so changed-file review
    # does not accidentally exclude it.
    return "modified"


def build_changed_files(pr_files):
    changed = {}

    for item in pr_files:
        filename = item.get("filename")

        if not filename:
            continue

        filename = normalize_path(filename)

        changed[filename] = {
            "status": normalize_status(item),
            "previous_filename": (
                normalize_path(
                    item["previous_filename"]
                )
                if item.get("previous_filename")
                else None
            ),
        }

    return changed


def finding_matches_file(
    finding,
    changed_files,
):
    finding_path = normalize_path(
        finding.get("path", "")
    )

    if finding_path in changed_files:
        return finding_path

    # --------------------------------------------------------
    # Handle path representation differences.
    # --------------------------------------------------------

    for changed_path in changed_files:

        normalized_changed = normalize_path(
            changed_path
        )

        if finding_path == normalized_changed:
            return changed_path

        if finding_path.endswith(
            "/" + normalized_changed
        ):
            return changed_path

        if normalized_changed.endswith(
            "/" + finding_path
        ):
            return changed_path

    return None


# ------------------------------------------------------------
# Filtering
# ------------------------------------------------------------

def filter_findings(
    findings,
    changed_files,
    filter_mode,
):
    if filter_mode == "nofilter":
        return findings

    filtered = []

    for finding in findings:

        matched_path = finding_matches_file(
            finding,
            changed_files,
        )

        if matched_path is None:
            continue

        file_info = changed_files[
            matched_path
        ]

        status = file_info["status"]

        # ----------------------------------------------------
        # changed_files / file
        #
        # Include:
        #   added
        #   modified
        #   renamed
        #   deleted
        # ----------------------------------------------------

        if filter_mode in {
            "changed_files",
            "file",
        }:

            if status not in CHANGED_FILE_STATUSES:
                continue

            finding["path"] = matched_path
            finding["_status"] = status

            filtered.append(finding)

            continue

        # ----------------------------------------------------
        # added
        #
        # Only newly-added files.
        # ----------------------------------------------------

        if filter_mode == "added":

            if status != "added":
                continue

            finding["path"] = matched_path
            finding["_status"] = status

            filtered.append(finding)

            continue

        # ----------------------------------------------------
        # diff_context
        #
        # The custom reporter currently receives reviewdog's
        # complete local output, not structured diff context.
        #
        # Therefore changed files are used as the available
        # scope here.
        # ----------------------------------------------------

        if filter_mode == "diff_context":

            finding["path"] = matched_path
            finding["_status"] = status

            filtered.append(finding)

            continue

    return filtered


# ------------------------------------------------------------
# Deduplication
# ------------------------------------------------------------

def deduplicate_findings(findings):
    seen = set()
    result = []

    for finding in findings:

        key = (
            normalize_path(
                finding.get("path", "")
            ),
            finding.get("line"),
            finding.get("column"),
            finding.get("message"),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(finding)

    return result


# ------------------------------------------------------------
# Forgejo review comments
# ------------------------------------------------------------

def build_review_comment(finding):
    path = normalize_path(
        finding.get("path", "")
    )

    line = finding.get("line")

    message = finding.get(
        "message",
        "",
    ).strip()

    if not path:
        return None

    if not message:
        return None

    if not isinstance(line, int):
        return None

    if line < 1:
        return None

    status = finding.get(
        "_status"
    )

    # --------------------------------------------------------
    # Deleted files
    #
    # The finding points to the old revision, so it cannot be
    # represented as a normal new-position inline comment.
    # --------------------------------------------------------

    if status == "deleted":
        return None

    return {
        "path": path,
        "body": (
            f"{message}\n\n"
            "_Automated review by reviewdog._"
        ),
        "new_position": line,
        "old_position": 0,
    }


def build_review_comments(findings):
    comments = []

    for finding in findings:

        comment = build_review_comment(
            finding
        )

        if comment is None:
            continue

        comments.append(comment)

    return comments


# ------------------------------------------------------------
# Forgejo API
# ------------------------------------------------------------

def post_review(
    api_url,
    owner,
    repo,
    pr_number,
    head_sha,
    token,
    comments,
):
    url = (
        f"{api_url.rstrip('/')}"
        f"/repos/{owner}/{repo}"
        f"/pulls/{pr_number}/reviews"
    )

    payload = {
        "event": "COMMENT",
        "body": (
            "Automated code review by reviewdog."
        ),
        "commit_id": head_sha,
        "comments": comments,
    }

    data = json.dumps(
        payload
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": (
                f"token {token}"
            ),
            "Accept": "application/json",
            "Content-Type": (
                "application/json"
            ),
        },
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=60,
        ) as response:

            if 200 <= response.status < 300:
                return True

            print(
                f"ERROR: Forgejo API returned "
                f"HTTP {response.status}."
            )

            return False

    except urllib.error.HTTPError as exc:

        print(
            f"ERROR: Forgejo API returned "
            f"HTTP {exc.code}."
        )

        return False

    except urllib.error.URLError:

        print(
            "ERROR: Could not connect to "
            "Forgejo API."
        )

        return False

    except TimeoutError:

        print(
            "ERROR: Forgejo API request timed out."
        )

        return False


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

def print_summary(
    total_findings,
    changed_file_count,
    filtered_count,
    inline_count,
    skipped_count,
):
    print(
        f"Parsed findings: "
        f"{total_findings}"
    )

    print(
        f"Changed files: "
        f"{changed_file_count}"
    )

    print(
        f"Findings after "
        f"'changed_files' filtering: "
        f"{filtered_count}"
    )

    print(
        f"Inline comments: "
        f"{inline_count}"
    )

    print(
        f"Skipped findings: "
        f"{skipped_count}"
    )


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    if len(sys.argv) != 10:
        die(
            "Usage: forgejo-review.py "
            "<reviewdog-results> "
            "<pr-files.json> "
            "<filter> "
            "<api-url> "
            "<owner> "
            "<repo> "
            "<pr-number> "
            "<head-sha> "
            "<token>"
        )

    result_file = sys.argv[1]
    pr_files_file = sys.argv[2]
    filter_mode = sys.argv[3]
    api_url = sys.argv[4]
    owner = sys.argv[5]
    repo = sys.argv[6]
    pr_number = sys.argv[7]
    head_sha = sys.argv[8]
    token = sys.argv[9]

    if filter_mode not in VALID_FILTERS:
        die(
            f"Unsupported filter mode: "
            f"{filter_mode}"
        )

    if not head_sha:
        die(
            "Pull request head SHA is required."
        )

    if not token:
        die(
            "Forgejo token is required."
        )

    pr_files = load_json(
        pr_files_file
    )

    if not isinstance(
        pr_files,
        list,
    ):
        die(
            "Pull request files response "
            "is not an array."
        )

    changed_files = build_changed_files(
        pr_files
    )

    print(
        "Reading reviewdog findings..."
    )

    findings = parse_findings(
        result_file
    )

    print()

    filtered = filter_findings(
        findings,
        changed_files,
        filter_mode,
    )

    filtered = deduplicate_findings(
        filtered
    )

    comments = build_review_comments(
        filtered
    )

    skipped_count = (
        len(filtered)
        - len(comments)
    )

    print_summary(
        total_findings=len(findings),
        changed_file_count=len(
            changed_files
        ),
        filtered_count=len(filtered),
        inline_count=len(comments),
        skipped_count=skipped_count,
    )

    print()

    if not filtered:
        print(
            "No findings matched the "
            "configured Forgejo filter mode."
        )

        return 0

    if not comments:
        print(
            "No findings can be placed as "
            "inline Forgejo comments."
        )

        return 0

    print(
        "Posting Forgejo review..."
    )

    success = post_review(
        api_url=api_url,
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        head_sha=head_sha,
        token=token,
        comments=comments,
    )

    if not success:
        return 1

    print(
        f"Posted {len(comments)} "
        f"review comments."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
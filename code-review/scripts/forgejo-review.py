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


def normalize_status(item):
    status = str(item.get("status", "")).lower().strip()

    if status:
        return status

    # Forgejo/Gitea responses can expose the change through fields
    # such as additions/deletions/changes without an explicit status.
    additions = item.get("additions", 0) or 0
    deletions = item.get("deletions", 0) or 0

    if additions > 0 and deletions == 0:
        return "added"

    if deletions > 0 and additions == 0:
        return "deleted"

    if additions > 0 or deletions > 0:
        return "modified"

    return "modified"


def build_changed_files(pr_files):
    changed = {}

    for item in pr_files:
        filename = item.get("filename")

        if not filename:
            continue

        changed[filename] = {
            "status": normalize_status(item),
            "previous_filename": item.get("previous_filename"),
        }

    return changed


def parse_reviewdog_line(line):
    """
    Parse common reviewdog local reporter formats.

    Supported examples:

        file.go:10:5: message
        file.go:10: message
        file.go:10 message

    Returns:
        {
            "path": str,
            "line": int,
            "column": int|None,
            "message": str
        }

    or None.
    """

    line = line.rstrip("\n")

    if not line.strip():
        return None

    # file:line:column: message
    match = re.match(
        r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+):\s*(?P<message>.+)$",
        line,
    )

    if match:
        return {
            "path": match.group("path"),
            "line": int(match.group("line")),
            "column": int(match.group("column")),
            "message": match.group("message").strip(),
        }

    # file:line: message
    match = re.match(
        r"^(?P<path>.+?):(?P<line>\d+):\s*(?P<message>.+)$",
        line,
    )

    if match:
        return {
            "path": match.group("path"),
            "line": int(match.group("line")),
            "column": None,
            "message": match.group("message").strip(),
        }

    # file:line message
    match = re.match(
        r"^(?P<path>.+?):(?P<line>\d+)\s+(?P<message>.+)$",
        line,
    )

    if match:
        return {
            "path": match.group("path"),
            "line": int(match.group("line")),
            "column": None,
            "message": match.group("message").strip(),
        }

    return None


def parse_findings(result_file):
    findings = []

    with open(result_file, "r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            finding = parse_reviewdog_line(raw_line)

            if finding is not None:
                findings.append(finding)

    return findings


def normalize_path(path):
    path = path.strip()

    if path.startswith("./"):
        path = path[2:]

    return path


def finding_matches_file(finding, changed_files):
    path = normalize_path(finding["path"])

    if path in changed_files:
        return path

    # Some linters output ./path while Forgejo returns path.
    for changed_path in changed_files:
        if normalize_path(changed_path) == path:
            return changed_path

    return None


def filter_findings(findings, changed_files, filter_mode):
    if filter_mode == "nofilter":
        return findings

    filtered = []

    for finding in findings:
        matched_path = finding_matches_file(finding, changed_files)

        if matched_path is None:
            continue

        file_info = changed_files[matched_path]
        status = file_info["status"]

        if filter_mode in {"changed_files", "file"}:
            if status not in CHANGED_FILE_STATUSES:
                continue

            finding["path"] = matched_path
            finding["_status"] = status
            filtered.append(finding)
            continue

        if filter_mode == "added":
            # Preserve the old behaviour: only findings belonging to
            # newly-added files are considered.
            if status != "added":
                continue

            finding["path"] = matched_path
            finding["_status"] = status
            filtered.append(finding)
            continue

        if filter_mode == "diff_context":
            # The custom reporter does not have reviewdog's parsed diff
            # information here. Treat the changed-file set as the
            # available scope.
            finding["path"] = matched_path
            finding["_status"] = status
            filtered.append(finding)
            continue

    return filtered


def deduplicate_findings(findings):
    seen = set()
    result = []

    for finding in findings:
        key = (
            normalize_path(finding["path"]),
            finding.get("line"),
            finding.get("column"),
            finding.get("message"),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(finding)

    return result


def build_review_comment(finding):
    path = normalize_path(finding["path"])
    line = finding.get("line")
    message = finding.get("message", "").strip()

    if not path or not message:
        return None

    if not isinstance(line, int) or line < 1:
        return None

    status = finding.get("_status")

    # A deleted file cannot receive a normal RIGHT-side/new-position
    # comment because the line no longer exists in the new revision.
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
        comment = build_review_comment(finding)

        if comment is not None:
            comments.append(comment)

    return comments


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

    body = {
        "event": "COMMENT",
        "body": "Automated code review by reviewdog.",
        "commit_id": head_sha,
    }

    if comments:
        body["comments"] = comments

    payload = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request) as response:
            status = response.status

            if status < 200 or status >= 300:
                print(f"ERROR: Forgejo API returned HTTP {status}.")
                return False

            return True

    except urllib.error.HTTPError as exc:
        print(f"ERROR: Forgejo API returned HTTP {exc.code}.")
        return False

    except urllib.error.URLError:
        print("ERROR: Could not connect to Forgejo API.")
        return False


def print_summary(
    total_findings,
    changed_file_count,
    filtered_count,
    inline_count,
    skipped_count,
):
    print(f"Parsed findings: {total_findings}")
    print(f"Changed files: {changed_file_count}")
    print(
        f"Findings after 'changed_files' filtering: "
        f"{filtered_count}"
    )
    print(f"Inline comments: {inline_count}")
    print(f"Skipped findings: {skipped_count}")


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
        die(f"Unsupported filter mode: {filter_mode}")

    if not head_sha:
        die("Pull request head SHA is required.")

    if not token:
        die("Forgejo token is required.")

    pr_files = load_json(pr_files_file)

    if not isinstance(pr_files, list):
        die("Pull request files response is not an array.")

    changed_files = build_changed_files(pr_files)

    findings = parse_findings(result_file)

    print("Reading reviewdog findings...")

    filtered = filter_findings(
        findings,
        changed_files,
        filter_mode,
    )

    filtered = deduplicate_findings(filtered)

    comments = build_review_comments(filtered)

    skipped_count = len(filtered) - len(comments)

    print_summary(
        total_findings=len(findings),
        changed_file_count=len(changed_files),
        filtered_count=len(filtered),
        inline_count=len(comments),
        skipped_count=skipped_count,
    )

    if not filtered:
        print("No findings matched the configured Forgejo filter mode.")
        return 0

    if not comments:
        print("No findings can be placed as inline Forgejo comments.")
        return 0

    print("Posting Forgejo review...")

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

    print(f"Posted {len(comments)} review comments.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
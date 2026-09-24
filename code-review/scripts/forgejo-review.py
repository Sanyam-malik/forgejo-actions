#!/usr/bin/env python3

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib import error
from urllib import request


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


def normalize_path(path):
    path = path.strip().strip("\"'")
    path = path.replace("\\", "/")

    while path.startswith("./"):
        path = path[2:]

    while path.startswith("/"):
        path = path[1:]

    return path


# ------------------------------------------------------------
# reviewdog parsing
# ------------------------------------------------------------

def parse_reviewdog_line(line):
    line = line.rstrip("\n")

    if not line.strip():
        return None

    # file:line:column message
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

    # file:line:column: message
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

    # file:line: message
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

    # file:line message
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
    status = str(
        item.get("status", "")
    ).lower().strip()

    # Forgejo commonly reports "changed".
    if status == "changed":
        return "modified"

    if status in {
        "added",
        "modified",
        "renamed",
        "deleted",
    }:
        return status

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

        status = changed_files[
            matched_path
        ]["status"]

        if filter_mode in {
            "changed_files",
            "file",
        }:
            if status not in CHANGED_FILE_STATUSES:
                continue

        elif filter_mode == "added":
            if status != "added":
                continue

        elif filter_mode == "diff_context":
            # The reporter currently operates at file scope.
            # Keep findings from changed files.
            pass

        finding["path"] = matched_path
        finding["_status"] = status

        filtered.append(finding)

    return filtered


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
# Source context
# ------------------------------------------------------------

def get_source_context(
    path,
    line,
    context_lines,
):
    if not path:
        return None

    if not isinstance(line, int):
        return None

    if line < 1:
        return None

    source_path = Path(path)

    if not source_path.is_file():
        return None

    try:
        lines = source_path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return None

    if not lines:
        return None

    target_index = line - 1

    if target_index >= len(lines):
        target_index = len(lines) - 1

    start = max(
        0,
        target_index - context_lines,
    )

    end = min(
        len(lines),
        target_index + context_lines + 1,
    )

    output = []

    for index in range(start, end):
        marker = ">" if index == target_index else " "

        output.append(
            f"{marker} {index + 1:6}: "
            f"{lines[index]}"
        )

    return "\n".join(output)


# ------------------------------------------------------------
# AI suggestions
# ------------------------------------------------------------

def ai_enabled():
    return (
        os.environ.get(
            "AI_SUGGESTIONS",
            "false",
        ).strip().lower()
        == "true"
    )


def ai_context_lines():
    raw = os.environ.get(
        "AI_CONTEXT_LINES",
        "10",
    ).strip()

    try:
        value = int(raw)
    except ValueError:
        return 10

    return max(
        0,
        min(value, 100),
    )


def run_ai_suggestion(
    finding,
    source_context,
):
    if not ai_enabled():
        return None

    action_path = os.environ.get(
        "GITHUB_ACTION_PATH",
        "",
    ).strip()

    if not action_path:
        print(
            "AI: GITHUB_ACTION_PATH is not set; "
            "skipping AI suggestion."
        )
        return None

    ai_script = (
        Path(action_path)
        / "scripts"
        / "ai-suggestions.py"
    )

    if not ai_script.is_file():
        print(
            "AI: ai-suggestions.py not found; "
            "skipping AI suggestion."
        )
        return None

    base_url = os.environ.get(
        "AI_BASE_URL",
        "",
    ).strip()

    model = os.environ.get(
        "AI_MODEL",
        "",
    ).strip()

    if not base_url:
        print(
            "AI: AI_BASE_URL is not configured; "
            "skipping AI suggestions."
        )
        return None

    if not model:
        print(
            "AI: AI_MODEL is not configured; "
            "skipping AI suggestions."
        )
        return None

    if not source_context:
        print(
            f"AI: no source context for "
            f"{finding.get('path')}:{finding.get('line')}; "
            "skipping."
        )
        return None

    try:
        with tempfile.TemporaryDirectory(
            prefix="forgejo-ai-"
        ) as temp_dir:

            temp_path = Path(temp_dir)

            finding_file = (
                temp_path / "finding.json"
            )

            context_file = (
                temp_path / "source.txt"
            )

            finding_payload = {
                "path": finding.get("path"),
                "line": finding.get("line"),
                "column": finding.get("column"),
                "message": finding.get("message"),
            }

            finding_file.write_text(
                json.dumps(
                    finding_payload,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            context_file.write_text(
                source_context,
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ai_script),
                    str(finding_file),
                    str(context_file),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=150,
                check=False,
                env=os.environ.copy(),
            )

            if result.returncode != 0:
                print(
                    "AI: suggestion generation failed; "
                    "keeping original linter finding."
                )

                return None

            output = result.stdout.strip()

            if not output:
                print(
                    "AI: empty response; "
                    "keeping original linter finding."
                )

                return None

            try:
                suggestion = json.loads(
                    output
                )
            except json.JSONDecodeError:
                print(
                    "AI: invalid suggestion response; "
                    "keeping original linter finding."
                )
                return None

            if not isinstance(
                suggestion,
                dict,
            ):
                return None

            description = suggestion.get(
                "description",
                "",
            )

            suggestion_text = suggestion.get(
                "suggestion",
                "",
            )

            if not isinstance(
                description,
                str,
            ):
                description = ""

            if not isinstance(
                suggestion_text,
                str,
            ):
                suggestion_text = ""

            description = description.strip()
            suggestion_text = suggestion_text.strip()

            if not description and not suggestion_text:
                return None

            return {
                "description": description,
                "suggestion": suggestion_text,
            }

    except subprocess.TimeoutExpired:
        print(
            "AI: suggestion generation timed out; "
            "keeping original linter finding."
        )
        return None

    except OSError:
        print(
            "AI: could not execute suggestion generator; "
            "keeping original linter finding."
        )
        return None


# ------------------------------------------------------------
# Local (non-AI) description/suggestion generation
# ------------------------------------------------------------
#
# These are heuristic and rule-based only: no network calls, no
# LLM. They fill in a "Description" / "Suggestion" section using
# the linter's own message plus, where we recognize the tool and
# rule code, a link to that rule's public documentation.

RULE_CODE_PATTERNS = (
    # Leading code: "MD013/line-length ...", "E501 ...",
    # "SC2086: ...", "DL3008 warning: ..."
    re.compile(
        r"^(?P<code>[A-Z]{1,5}\d{2,5}(?:/[\w-]+)?)\b"
    ),
    # Trailing code in brackets/parens:
    # "... [Error/no-unused-vars]", "... [SC2086]",
    # "... (Style/StringLiterals)"
    re.compile(
        r"[\[(](?:[A-Za-z]+/)?(?P<code>[A-Za-z0-9_.-]+)[\])]\s*$"
    ),
)


def extract_rule_code(text):
    if not text:
        return None

    for pattern in RULE_CODE_PATTERNS:
        match = pattern.search(text)

        if match:
            code = match.group("code").strip()

            if code:
                return code

    return None


def rule_doc_url(tool, code):
    if not tool or not code:
        return None

    tool = tool.lower()

    if tool == "markdownlint":
        rule_id = code.split("/")[0].lower()
        return (
            "https://github.com/DavidAnson/markdownlint/"
            f"blob/main/doc/{rule_id}.md"
        )

    if tool == "shellcheck":
        match = re.search(r"\d+", code)
        if match:
            return f"https://www.shellcheck.net/wiki/SC{match.group(0)}"

    if tool == "ruff":
        return f"https://docs.astral.sh/ruff/rules/{code}/"

    if tool == "eslint":
        rule = code.split("/")[-1]
        return f"https://eslint.org/docs/latest/rules/{rule}"

    if tool == "hadolint":
        return f"https://github.com/hadolint/hadolint/wiki/{code}"

    if tool == "clippy":
        rule = code.replace("clippy::", "")
        return (
            "https://rust-lang.github.io/rust-clippy/"
            f"master/#{rule}"
        )

    if tool == "tflint":
        return (
            "https://github.com/terraform-linters/"
            f"tflint-ruleset-terraform/blob/main/docs/rules/{code}.md"
        )

    return None


def local_description(tool, code, text):
    label = TOOL_LABELS.get(tool, tool) if tool else "This linter"

    if code:
        return f"{label} flagged this via rule `{code}`."

    return f"{label} flagged this."


def local_suggestion(tool, code):
    label = TOOL_LABELS.get(tool, tool) if tool else "the linter"

    doc_url = rule_doc_url(tool, code)

    if doc_url:
        return f"See the rule's documentation for how to fix it: {doc_url}"

    if code:
        return (
            f"Look up rule `{code}` in {label}'s documentation "
            "for guidance on fixing this."
        )

    return f"Check {label}'s documentation for how to resolve this."


def enrich_findings_locally(findings):
    filled = 0

    for finding in findings:
        # Don't overwrite an AI-generated description/suggestion.
        if finding.get("description") and finding.get("suggestion"):
            continue

        message = finding.get("message", "").strip()

        if not message:
            continue

        parsed = parse_message(message)
        code = extract_rule_code(parsed["text"])

        if not finding.get("description"):
            finding["description"] = local_description(
                parsed["tool"],
                code,
                parsed["text"],
            )
            finding["description_source"] = "local"

        if not finding.get("suggestion"):
            finding["suggestion"] = local_suggestion(
                parsed["tool"],
                code,
            )
            finding["suggestion_source"] = "local"

        filled += 1

    print(
        f"Local (non-AI) descriptions/suggestions added: {filled}"
    )
    print()

    return findings


def enrich_findings_with_ai(findings):
    if not ai_enabled():
        return findings

    print()
    print("AI suggestions: enabled")
    print(
        f"AI context: ±{ai_context_lines()} lines"
    )
    print(
        f"AI findings: {len(findings)}"
    )
    print()

    context_lines = ai_context_lines()

    enriched = 0
    skipped = 0

    for index, finding in enumerate(
        findings,
        start=1,
    ):
        path = finding.get(
            "path",
            "",
        )

        line = finding.get(
            "line"
        )

        print(
            f"AI [{index}/{len(findings)}] "
            f"{path}:{line}"
        )

        # Deleted files generally aren't present in the
        # working tree, so don't attempt AI enrichment.
        if finding.get("_status") == "deleted":
            print(
                "  skipped: deleted file"
            )
            skipped += 1
            continue

        source_context = get_source_context(
            path,
            line,
            context_lines,
        )

        if not source_context:
            print(
                "  skipped: source context unavailable"
            )
            skipped += 1
            continue

        result = run_ai_suggestion(
            finding,
            source_context,
        )

        if not result:
            skipped += 1
            continue

        description = result.get(
            "description",
            "",
        )

        suggestion = result.get(
            "suggestion",
            "",
        )

        if description:
            finding["description"] = (
                description
            )
            finding["description_source"] = "ai"

        if suggestion:
            finding["suggestion"] = (
                suggestion
            )
            finding["suggestion_source"] = "ai"

        if description or suggestion:
            enriched += 1
            print("  enriched")

        else:
            skipped += 1

    print()
    print(
        f"AI enriched findings: {enriched}"
    )
    print(
        f"AI skipped findings: {skipped}"
    )
    print()

    return findings


# ------------------------------------------------------------
# Forgejo comment generation
# ------------------------------------------------------------

LEVEL_EMOJI = {
    "error": "🛑",
    "warning": "⚠️",
    "info": "ℹ️",
    "note": "ℹ️",
}

TOOL_LABELS = {
    "golangci-lint": "Go · golangci-lint",
    "ruff": "Python · ruff",
    "eslint": "JavaScript · eslint",
    "shellcheck": "Shell · shellcheck",
    "yamllint": "YAML · yamllint",
    "hadolint": "Dockerfile · hadolint",
    "rubocop": "Ruby · rubocop",
    "clippy": "Rust · clippy",
    "markdownlint": "Markdown · markdownlint",
    "tflint": "Terraform · tflint",
    "phpcs": "PHP · phpcs",
}

# reviewdog's local reporter prefixes each message with
# "[tool] level ..." (e.g. "[markdownlint] error MD013 ...").
# Pull that apart so we can render a friendly header instead of
# dumping the raw prefix into the comment body.
MESSAGE_PREFIX_RE = re.compile(
    r"^\[(?P<tool>[^\]]+)\]\s*"
    r"(?:(?P<level>error|warning|info|note)\b\s*)?"
    r"(?P<rest>.+)$",
    re.IGNORECASE,
)


def parse_message(message):
    match = MESSAGE_PREFIX_RE.match(message)

    if not match:
        return {
            "tool": None,
            "level": None,
            "text": message,
        }

    rest = match.group("rest").strip()

    if not rest:
        return {
            "tool": None,
            "level": None,
            "text": message,
        }

    return {
        "tool": match.group("tool").strip(),
        "level": (
            (match.group("level") or "").lower()
            or None
        ),
        "text": rest,
    }


def friendly_header(tool, level):
    emoji = LEVEL_EMOJI.get(level, "🔍")

    label = TOOL_LABELS.get(tool, tool) if tool else None

    if label:
        return f"{emoji} **{label}**"

    return f"{emoji} **Lint finding**"


def build_review_comment(finding):
    path = normalize_path(
        finding.get("path", "")
    )

    line = finding.get("line")

    message = finding.get(
        "message",
        "",
    ).strip()

    if not path or not message:
        return None

    if not isinstance(line, int) or line < 1:
        return None

    # Deleted files cannot receive a new-position inline
    # comment against the current PR head.
    if finding.get("_status") == "deleted":
        return None

    parsed = parse_message(message)

    body = (
        friendly_header(
            parsed["tool"],
            parsed["level"],
        )
        + "\n\n"
        + parsed["text"]
    )

    description = finding.get(
        "description"
    )

    suggestion = finding.get(
        "suggestion"
    )

    if description:
        body += (
            "\n\n"
            "**Description**"
            "\n\n"
            + description
        )

    if suggestion:
        body += (
            "\n\n"
            "**Suggestion**"
            "\n\n"
            + suggestion
        )

    body += (
        "\n\n"
        "<sub>🤖 Automated review by reviewdog</sub>"
    )

    return {
        "path": path,
        "body": body,
        "new_position": line,
        "old_position": 0,
    }


def build_review_comments(findings):
    comments = []

    for finding in findings:
        comment = build_review_comment(
            finding
        )

        if comment is not None:
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

    comment_word = (
        "comment" if len(comments) == 1 else "comments"
    )

    payload = {
        "event": "COMMENT",
        "body": (
            "🤖 **Automated code review**\n\n"
            f"Found {len(comments)} {comment_word} worth a look "
            "below. These come from open-source linters, not a "
            "human reviewer — feel free to push back."
        ),
        "commit_id": head_sha,
        "comments": comments,
    }

    data = json.dumps(
        payload
    ).encode("utf-8")

    req = request.Request(
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
        with request.urlopen(
            req,
            timeout=60,
        ) as response:

            if 200 <= response.status < 300:
                return True

            print(
                f"ERROR: Forgejo API returned "
                f"HTTP {response.status}."
            )

            return False

    except error.HTTPError as exc:
        # Deliberately do not print:
        # - request payload
        # - response body
        print(
            f"ERROR: Forgejo API returned "
            f"HTTP {exc.code}."
        )
        return False

    except error.URLError:
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
        f"Findings after filtering: "
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

    print(
        f"Parsed {len(findings)} findings."
    )

    filtered = filter_findings(
        findings,
        changed_files,
        filter_mode,
    )

    filtered = deduplicate_findings(
        filtered
    )

    # --------------------------------------------------------
    # Optional AI enrichment
    # --------------------------------------------------------

    filtered = enrich_findings_with_ai(
        filtered
    )

    filtered = enrich_findings_locally(
        filtered
    )

    # --------------------------------------------------------
    # Build Forgejo comments
    # --------------------------------------------------------

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
#!/usr/bin/env python3
"""
Turns reviewdog RDJSON output into the flat JSON-items format consumed by
the shared code-analyzer action, applying code-review-specific changed-files
and diff-line filtering while leaving common filtering and posting to the
analyzer.

Each output item is a flat dict with (at least) "path" and "line" plus
everything a message template might want to reference: severity, tool,
rule_code, rule_url, message, and a few pre-rendered convenience fields
(header, description, suggestion, doc_link, footer) so the default
template doesn't need conditional logic for optional pieces.
"""

import json
import os
import re
import sys
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

MESSAGE_PREFIX_RE = re.compile(
    r"^\[(?P<tool>[^\]]+)\]\s*"
    r"(?:(?P<level>error|warning|info|note)\b\s*)?"
    r"(?P<rest>.+)$",
    re.IGNORECASE,
)

RULE_CODE_PATTERNS = (
    re.compile(r"^(?P<code>[A-Z]{1,5}\d{2,5}(?:/[\w-]+)?)\b"),
    re.compile(r"[\[(](?:[A-Za-z]+/)?(?P<code>[A-Za-z0-9_.-]+)[\])]\s*$"),
)


def die(message):
    print(f"ERROR: {message}")
    sys.exit(1)


def env(name, required=True, default=""):
    value = os.environ.get(name, default)
    if required and not value.strip():
        die(f"Required input/env var {name} is empty.")
    return value


def normalize_path(path):
    path = str(path).strip().strip("\"'").replace("\\", "/")
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

    patterns = (
        re.compile(r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+)\s+(?P<message>.+)$"),
        re.compile(r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+):\s*(?P<message>.+)$"),
        re.compile(r"^(?P<path>.+?):(?P<line>\d+):\s*(?P<message>.+)$"),
        re.compile(r"^(?P<path>.+?):(?P<line>\d+)\s+(?P<message>.+)$"),
    )

    for pattern in patterns:
        match = pattern.match(line)
        if match:
            return {
                "path": normalize_path(match.group("path")),
                "line": int(match.group("line")),
                "column": (
                    int(match.group("column")) if match.groupdict().get("column") else None
                ),
                "message": match.group("message").strip(),
            }

    return None


def parse_rdjson_diagnostic(diagnostic, source=None):
    if not isinstance(diagnostic, dict):
        return None

    location = diagnostic.get("location") or {}
    path = location.get("path")
    range_data = location.get("range") or {}
    start = range_data.get("start") or {}

    if not path:
        return None

    try:
        line = int(start.get("line"))
    except (TypeError, ValueError):
        return None

    if line < 1:
        return None

    column = start.get("column")
    try:
        column = int(column) if column is not None else None
    except (TypeError, ValueError):
        column = None

    message = diagnostic.get("message")
    if not isinstance(message, str) or not message.strip():
        return None

    severity = str(diagnostic.get("severity", "")).upper()
    level = {"ERROR": "error", "WARNING": "warning", "INFO": "info"}.get(severity)

    source_data = diagnostic.get("source")
    if not isinstance(source_data, dict):
        source_data = source if isinstance(source, dict) else {}

    tool = source_data.get("name")
    if not isinstance(tool, str):
        tool = None

    code_data = diagnostic.get("code")
    code = None
    code_url = None
    if isinstance(code_data, dict):
        value = code_data.get("value")
        if isinstance(value, str) and value.strip():
            code = value.strip()
        url = code_data.get("url")
        if isinstance(url, str) and url.strip():
            code_url = url.strip()

    text = message.strip()
    if code and code not in text:
        text = f"{code}: {text}"

    if tool:
        prefix = f"[{tool}]"
        if level:
            prefix += f" {level}"
        text = f"{prefix} {text}"

    return {
        "path": normalize_path(path),
        "line": line,
        "column": column,
        "message": text,
        "_severity": level,
        "_rule_code": code,
        "_rule_url": code_url,
    }


def parse_findings(result_file):
    try:
        with open(result_file, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError as exc:
        die(f"Failed to read reviewdog results: {exc}")

    if not raw.strip():
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        findings = []
        for raw_line in raw.splitlines():
            finding = parse_reviewdog_line(raw_line)
            if finding is not None:
                findings.append(finding)
        return findings

    if not isinstance(data, dict) or "diagnostics" not in data:
        return []

    diagnostics = data.get("diagnostics")
    if not isinstance(diagnostics, list):
        return []

    source = data.get("source")
    findings = []
    for diagnostic in diagnostics:
        finding = parse_rdjson_diagnostic(diagnostic, source=source)
        if finding is not None:
            findings.append(finding)

    return findings


# ------------------------------------------------------------
# Forgejo PR files / diff
# ------------------------------------------------------------

def fetch_pr_files(api_url, owner, repo, pr_number, token):
    files = []
    page = 1

    while True:
        url = (
            f"{api_url.rstrip('/')}/repos/{owner}/{repo}"
            f"/pulls/{pr_number}/files?page={page}&limit=50"
        )
        req = request.Request(
            url,
            method="GET",
            headers={"Authorization": f"token {token}", "Accept": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
        except error.HTTPError as exc:
            die(f"Could not fetch PR files (HTTP {exc.code}).")
        except (error.URLError, TimeoutError):
            die("Could not fetch PR files.")

        if not isinstance(data, list) or not data:
            break

        files.extend(data)

        if len(data) < 50 or page > 20:
            break

        page += 1

    return files


def fetch_pull_diff(api_url, owner, repo, pr_number, token):
    url = f"{api_url.rstrip('/')}/repos/{owner}/{repo}/pulls/{pr_number}.diff"

    req = request.Request(
        url,
        method="GET",
        headers={"Authorization": f"token {token}", "Accept": "text/plain"},
    )

    try:
        with request.urlopen(req, timeout=60) as response:
            return response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        print(f"WARNING: Could not fetch pull-request diff (HTTP {exc.code}).")
    except (error.URLError, TimeoutError):
        print("WARNING: Could not fetch pull-request diff.")

    return ""


def normalize_status(item):
    status = str(item.get("status", "")).lower().strip()

    if status == "changed":
        return "modified"

    if status in {"added", "modified", "renamed", "deleted"}:
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
                normalize_path(item["previous_filename"])
                if item.get("previous_filename")
                else None
            ),
        }
    return changed


def parse_unified_diff_changed_lines(diff_text, context_lines=3):
    added_lines = {}
    context_candidates = {}
    current_path = None
    new_line = None
    context_budget = max(0, int(context_lines))

    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            path = raw[4:].strip()
            if path == "/dev/null":
                current_path = None
            else:
                if path.startswith("b/"):
                    path = path[2:]
                current_path = normalize_path(path)
            continue

        if raw.startswith("@@ "):
            match = re.match(r"^@@ -\d+(?:,\d+)? \+(?P<new>\d+)(?:,(?P<count>\d+))? @@", raw)
            if not match:
                current_path = None
                new_line = None
                continue
            new_line = int(match.group("new"))
            continue

        if current_path is None or new_line is None:
            continue

        if raw.startswith("+") and not raw.startswith("+++"):
            added_lines.setdefault(current_path, set()).add(new_line)
            new_line += 1
            continue

        if raw.startswith("-") and not raw.startswith("---"):
            continue

        if raw.startswith(" ") or raw == "":
            context_candidates.setdefault(current_path, set()).add(new_line)
            new_line += 1

    if context_budget == 0:
        return added_lines, added_lines

    context_lines_by_file = {}
    for path, changed in added_lines.items():
        selected = set(changed)
        for line in context_candidates.get(path, set()):
            if any(abs(line - changed_line) <= context_budget for changed_line in changed):
                selected.add(line)
        context_lines_by_file[path] = selected

    return added_lines, context_lines_by_file


def filter_findings_by_diff_lines(findings, diff_lines, mode):
    if mode not in {"added", "diff_context"}:
        return findings

    selected = diff_lines[0 if mode == "added" else 1]
    result = []
    for finding in findings:
        path = normalize_path(finding.get("path", ""))
        line = finding.get("line")
        if path in selected and isinstance(line, int) and line in selected[path]:
            result.append(finding)
    return result


def finding_matches_file(finding, changed_files):
    finding_path = normalize_path(finding.get("path", ""))

    if finding_path in changed_files:
        return finding_path

    for changed_path in changed_files:
        normalized_changed = normalize_path(changed_path)
        if finding_path == normalized_changed:
            return changed_path
        if finding_path.endswith("/" + normalized_changed):
            return changed_path
        if normalized_changed.endswith("/" + finding_path):
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

        status = changed_files[matched_path]["status"]

        if filter_mode in {"changed_files", "file", "added", "diff_context"}:
            if status not in CHANGED_FILE_STATUSES:
                continue

        finding["path"] = matched_path
        finding["_status"] = status
        filtered.append(finding)

    return filtered


# ------------------------------------------------------------
# Message parsing + non-AI (rule-doc-based) enrichment
# ------------------------------------------------------------

def parse_message(message):
    match = MESSAGE_PREFIX_RE.match(message)
    if not match:
        return {"tool": None, "level": None, "text": message}

    rest = match.group("rest").strip()
    if not rest:
        return {"tool": None, "level": None, "text": message}

    return {
        "tool": match.group("tool").strip(),
        "level": (match.group("level") or "").lower() or None,
        "text": rest,
    }


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
        return f"https://github.com/DavidAnson/markdownlint/blob/main/doc/{rule_id}.md"
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
        return f"https://rust-lang.github.io/rust-clippy/master/#{rule}"
    if tool == "tflint":
        return (
            "https://github.com/terraform-linters/"
            f"tflint-ruleset-terraform/blob/main/docs/rules/{code}.md"
        )

    return None


def description_text(tool, code):
    label = TOOL_LABELS.get(tool, tool) if tool else "This linter"
    if code:
        return f"{label} flagged this via rule `{code}`."
    return f"{label} flagged this."


def suggestion_text(tool, code):
    label = TOOL_LABELS.get(tool, tool) if tool else "the linter"
    doc_url = rule_doc_url(tool, code)
    if doc_url:
        return f"See the rule's documentation for how to fix it: {doc_url}"
    if code:
        return f"Look up rule `{code}` in {label}'s documentation for guidance on fixing this."
    return f"Check {label}'s documentation for how to resolve this."


def build_display_item(finding):
    path = normalize_path(finding.get("path", ""))
    line = finding.get("line")
    message = finding.get("message", "").strip()

    parsed = parse_message(message)
    severity = (finding.get("_severity") or parsed.get("level") or "info").lower()
    tool = parsed.get("tool")
    tool_label = TOOL_LABELS.get(tool, tool) if tool else "Lint finding"

    rule_code = finding.get("_rule_code") or extract_rule_code(parsed["text"])
    rule_url = finding.get("_rule_url") or rule_doc_url(tool, rule_code)

    finding_text = parsed["text"]
    if rule_code and finding_text.startswith(f"{rule_code}: "):
        finding_text = finding_text[len(rule_code) + 2 :].strip()

    emoji = LEVEL_EMOJI.get(severity, "🔍")
    header = f"{emoji} **{tool_label}" + (f" · `{rule_code}`**" if rule_code else "**")

    doc_link = ""
    if rule_url:
        doc_link = f"📖 **Documentation:** [{rule_code or 'Rule documentation'}]({rule_url})"

    footer = f"<sub>{tool_label} · {severity.upper()}</sub>"

    return {
        "path": path,
        "line": line,
        "column": finding.get("column") if finding.get("column") is not None else "",
        "severity": severity,
        "tool": tool or "",
        "tool_label": tool_label,
        "rule_code": rule_code or "",
        "rule_url": rule_url or "",
        "message": finding_text,
        "header": header,
        "description": description_text(tool, rule_code),
        "suggestion": suggestion_text(tool, rule_code),
        "doc_link": doc_link,
        "footer": footer,
    }


def main():
    result_file = env("RESULT_FILE")
    filter_mode = env("FILTER_MODE", required=False, default="changed_files")
    items_output = env("ITEMS_OUTPUT", required=False, default="review-items.json")

    api_url = env("API_URL")
    owner = env("OWNER")
    repo = env("REPO")
    pr_number = env("PR_NUMBER")
    token = env("TOKEN")

    if filter_mode not in VALID_FILTERS:
        die(f"Unsupported filter mode: {filter_mode}")

    print("Reading reviewdog findings...")
    findings = parse_findings(result_file)
    print(f"Parsed {len(findings)} findings.")

    print("Fetching PR file list...")
    pr_files = fetch_pr_files(api_url, owner, repo, pr_number, token)
    changed_files = build_changed_files(pr_files)
    print(f"Changed files: {len(changed_files)}")

    filtered = filter_findings(findings, changed_files, filter_mode)

    if filter_mode in {"added", "diff_context"} and filtered:
        print("Fetching pull-request diff for line-level filtering...")
        diff_text = fetch_pull_diff(api_url, owner, repo, pr_number, token)
        if not diff_text:
            die(f"Could not fetch pull-request diff required for filter mode '{filter_mode}'.")
        diff_lines = parse_unified_diff_changed_lines(diff_text, context_lines=3)
        filtered = filter_findings_by_diff_lines(filtered, diff_lines, filter_mode)

    print(f"Findings after filtering: {len(filtered)}")

    items = [build_display_item(f) for f in filtered]

    with open(items_output, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(items)} finding(s) to {items_output}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
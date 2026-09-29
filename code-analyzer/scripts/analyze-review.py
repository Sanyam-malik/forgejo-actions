#!/usr/bin/env python3
"""Apply the shared review-item lifecycle before posting comments.

Review producers write either a JSON array or an object with an ``items``
array.  This script owns the operations that must behave consistently for
every producer: severity filtering, fingerprint deduplication, existing
comment lookup, auto-resolution, output values, and fail-level enforcement.
"""

import hashlib
import json
import os
import re
import secrets
import sys
from pathlib import Path
from urllib import request


SEVERITY_RANK = {"info": 1, "warning": 2, "error": 3}
VALID_FAIL_LEVELS = {"none", "any", "info", "warning", "error"}
FINGERPRINT_RE_TEMPLATE = r"<!--\s*{prefix}:([0-9a-f]{{8,40}})\s*-->"
RESOLVED_RE_TEMPLATE = r"<!--\s*{prefix}-resolved:([0-9a-f]{{8,40}})\s*-->"


def die(message):
    print(f"ERROR: {message}")
    sys.exit(1)


def env(name, default=""):
    return os.environ.get(name, default).strip()


def env_bool(name, default=False):
    value = env(name).lower()
    if value in {"true", "1", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    return default


def env_num(name, default, cast=int):
    raw = env(name)
    if not raw:
        return default
    try:
        return cast(raw)
    except (TypeError, ValueError):
        die(f"Input {name} must be a number, got '{raw}'.")


def env_limit(name):
    value = env_num(name, 0)
    return value if value > 0 else None


def write_output(name, value):
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        return
    value = str(value)
    try:
        with open(output_file, "a", encoding="utf-8") as output:
            if "\n" in value:
                delimiter = f"REVIEW_OUTPUT_{secrets.token_hex(8)}"
                output.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
            else:
                output.write(f"{name}={value}\n")
    except OSError as exc:
        print(f"WARNING: could not write output '{name}': {exc}")


def normalize_path(path):
    path = str(path or "").strip().strip("\"'").replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


def collapse_whitespace(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def read_source_line(path, line):
    if not path or not isinstance(line, int) or line < 1:
        return None

    bases = [Path(".")]
    workspace = env("GITHUB_WORKSPACE")
    if workspace:
        bases.append(Path(workspace))

    for base in bases:
        candidate = base / path
        if not candidate.is_file():
            continue
        try:
            lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return None
        return lines[line - 1] if line <= len(lines) else None
    return None


def forgejo_get_paged(ctx, suffix, limit=50, max_pages=20):
    results = []
    previous = None
    joiner = "&" if "?" in suffix else "?"

    for page in range(1, max_pages + 1):
        url = (
            f"{ctx['api_url'].rstrip('/')}/repos/{ctx['owner']}/{ctx['repo']}"
            f"{suffix}{joiner}page={page}&limit={limit}"
        )
        req = request.Request(
            url,
            method="GET",
            headers={"Authorization": f"token {ctx['token']}", "Accept": "application/json"},
        )
        with request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))

        if not isinstance(data, list) or not data or data == previous:
            break
        results.extend(data)
        if len(data) < limit:
            break
        previous = data
    return results


def fetch_existing_comments(ctx, prefix):
    marker_re = re.compile(FINGERPRINT_RE_TEMPLATE.format(prefix=re.escape(prefix)))
    resolved_re = re.compile(RESOLVED_RE_TEMPLATE.format(prefix=re.escape(prefix)))
    found = []
    try:
        reviews = forgejo_get_paged(ctx, f"/pulls/{ctx['pr_number']}/reviews")
        for review in reviews:
            review_id = review.get("id")
            if review_id is None:
                continue
            comments = forgejo_get_paged(
                ctx, f"/pulls/{ctx['pr_number']}/reviews/{review_id}/comments"
            )
            for comment in comments:
                comment_id = comment.get("id")
                body = str(comment.get("body") or "")
                fingerprints = marker_re.findall(body)
                if comment_id is None or not fingerprints:
                    continue
                found.append(
                    {
                        "id": comment_id,
                        "body": body,
                        "fingerprint": fingerprints[0],
                        "already_resolved": bool(resolved_re.search(body)),
                    }
                )
    except Exception as exc:
        print(f"WARNING: could not load existing review comments ({exc}); not de-duplicating.")
    return found


def edit_pull_comment(ctx, comment_id, body):
    url = (
        f"{ctx['api_url'].rstrip('/')}/repos/{ctx['owner']}/{ctx['repo']}"
        f"/issues/comments/{comment_id}"
    )
    req = request.Request(
        url,
        data=json.dumps({"body": body}).encode("utf-8"),
        method="PATCH",
        headers={
            "Authorization": f"token {ctx['token']}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with request.urlopen(req, timeout=60) as response:
        return 200 <= response.status < 300


def mark_fixed_comments(ctx, comments, prefix):
    head_sha = env("HEAD_SHA")
    fixed_note = (
        f"✅ **Fixed** by `{head_sha[:12]}` (no longer detected on the latest commit)."
        if head_sha
        else "✅ **Fixed** (no longer detected on the latest commit)."
    )
    resolved = 0
    for comment in comments:
        body = (
            f"{comment['body'].rstrip()}\n\n---\n{fixed_note}"
            f"\n<!-- {prefix}-resolved:{comment['fingerprint']} -->"
        )
        try:
            if edit_pull_comment(ctx, comment["id"], body):
                resolved += 1
            else:
                print(f"WARNING: could not mark comment {comment['id']} as fixed.")
        except Exception as exc:
            print(f"WARNING: could not mark comment {comment['id']} as fixed ({exc}).")
    return resolved


def source_text(item):
    if "_fingerprint_line" in item:
        return collapse_whitespace(item["_fingerprint_line"])
    source = read_source_line(normalize_path(item.get("path")), item.get("line"))
    return collapse_whitespace(source) if source is not None else f"line:{item.get('line')}"


def fingerprint_base(item, mode):
    path = normalize_path(item.get("path"))
    if mode == "ai":
        title = re.sub(r"\W+", " ", str(item.get("title") or "").lower()).strip()
        line = source_text(item)
        return "|".join((path, str(item.get("category") or ""), title, line))
    if mode == "lint":
        return "|".join(
            (
                path,
                str(item.get("tool") or ""),
                str(item.get("rule_code") or ""),
                collapse_whitespace(item.get("message")),
                source_text(item),
            )
        )
    return "|".join(
        (
            path,
            str(item.get("tool") or item.get("category") or ""),
            str(item.get("rule_code") or item.get("title") or ""),
            collapse_whitespace(item.get("message")),
            source_text(item),
        )
    )


def assign_fingerprints(items, mode, prefix):
    unique = []
    seen_items = set()
    for item in items:
        key = (
            normalize_path(item.get("path")),
            item.get("line"),
            item.get("column"),
            item.get("message"),
        )
        if key in seen_items:
            continue
        seen_items.add(key)
        unique.append(item)

    indexed = list(enumerate(unique))
    indexed.sort(key=lambda pair: (normalize_path(pair[1].get("path")), pair[1].get("line", 0)))
    occurrences = {}
    fingerprints = {}
    for index, item in indexed:
        base = fingerprint_base(item, mode)
        occurrence = occurrences.get(base, 0)
        occurrences[base] = occurrence + 1
        suffix = f"|{occurrence}" if mode == "lint" else ""
        fingerprints[index] = hashlib.sha1(f"{base}{suffix}".encode("utf-8")).hexdigest()[:12]

    result = []
    seen = set()
    for index, item in enumerate(unique):
        fingerprint = fingerprints[index]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        item["fingerprint"] = fingerprint
        item["fingerprint_marker"] = f"\n<!-- {prefix}:{fingerprint} -->"
        result.append(item)
    return result


def filter_by_level(items, level):
    level = level.lower()
    if level not in SEVERITY_RANK:
        return items
    threshold = SEVERITY_RANK[level]
    return [
        item
        for item in items
        if SEVERITY_RANK.get(str(item.get("severity") or "info").lower(), 1) >= threshold
    ]


def should_fail(items, fail_level):
    if fail_level == "none" or not items:
        return False
    if fail_level == "any":
        return True
    threshold = SEVERITY_RANK[fail_level]
    return any(
        SEVERITY_RANK.get(str(item.get("severity") or "info").lower(), 1) >= threshold
        for item in items
    )


def build_summary(metadata, items):
    summary = metadata.get("summary")
    if not isinstance(summary, dict):
        return str(summary or "")
    counts = {
        severity: sum(1 for item in items if item.get("severity") == severity)
        for severity in SEVERITY_RANK
    }
    emojis = {"error": "🛑", "warning": "⚠️", "info": "💡"}
    parts = [
        f"{emojis[severity]} {counts[severity]} {severity}"
        for severity in ("error", "warning", "info")
        if counts[severity]
    ]
    model = str(summary.get("model") or "")
    files_reviewed = summary.get("files_reviewed", 0)
    lines = [
        f"🤖 **AI code review** · `{model}`",
        "",
        f"Reviewed {files_reviewed} changed file(s) and found {len(items)} issue(s)"
        f"{': ' + ' · '.join(parts) if parts else ''}.",
    ]
    lines.extend(f"- {note}" for note in summary.get("notes", []))
    lines += ["", "_AI-generated review; it can be wrong or miss context. Please verify before acting._"]
    return "\n".join(lines)


def load_items(path):
    try:
        with open(path, encoding="utf-8") as items_file:
            data = json.load(items_file)
    except (OSError, json.JSONDecodeError) as exc:
        die(f"Could not read review items: {exc}")
    if isinstance(data, list):
        return data, {}
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data["items"], data
    die("Review items file must contain a JSON array or an object with an 'items' array.")


def main():
    items_path = env("ITEMS_FILE")
    if not items_path:
        die("Required input/env var ITEMS_FILE is empty.")

    items, metadata = load_items(items_path)
    if not all(isinstance(item, dict) for item in items):
        die("Every review item must be a JSON object.")

    level = env("LEVEL", "none").lower()
    if level not in {"none", *SEVERITY_RANK}:
        die(f"Unsupported level: {level} (use none, info, warning, or error)")
    fail_level = env("FAIL_LEVEL", "none").lower()
    if fail_level not in VALID_FAIL_LEVELS:
        die(f"Unsupported fail level: {fail_level}")

    mode = env("FINGERPRINT_MODE", "generic").lower()
    if mode not in {"generic", "lint", "ai"}:
        die(f"Unsupported fingerprint mode: {mode}")
    prefix = env("FINGERPRINT_PREFIX", "review")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", prefix):
        die("FINGERPRINT_PREFIX may contain only letters, numbers, '-' and '_'.")

    items = filter_by_level(items, level)
    items = assign_fingerprints(items, mode, prefix)
    total_count = len(items)
    fail = should_fail(items, fail_level)

    skipped_existing = 0
    resolved_count = 0
    ctx = {
        "api_url": env("API_URL"),
        "owner": env("OWNER"),
        "repo": env("REPO"),
        "pr_number": env("PR_NUMBER"),
        "token": env("TOKEN"),
    }
    if env_bool("SKIP_EXISTING", True):
        missing = [key for key, value in ctx.items() if not value]
        if missing:
            die(
                "Missing context: " + ", ".join(missing)
                + ". This action must run on a pull_request-triggered job."
            )
        existing = fetch_existing_comments(ctx, prefix)
        current = {item["fingerprint"] for item in items}
        stale = [
            comment
            for comment in existing
            if not comment["already_resolved"] and comment["fingerprint"] not in current
        ]
        if stale:
            print(f"{len(stale)} earlier finding(s) look fixed; marking their comments...")
            resolved_count = mark_fixed_comments(ctx, stale, prefix)
        open_fingerprints = {
            comment["fingerprint"]
            for comment in existing
            if not comment["already_resolved"] and comment["fingerprint"] in current
        }
        before = len(items)
        items = [item for item in items if item["fingerprint"] not in open_fingerprints]
        skipped_existing = before - len(items)

    max_comments = env_limit("MAX_COMMENTS")
    if max_comments:
        items.sort(
            key=lambda item: (
                -SEVERITY_RANK.get(str(item.get("severity") or "info").lower(), 1),
                -float(item.get("confidence") or 0),
                normalize_path(item.get("path")),
                item.get("line", 0),
            )
        )
        if len(items) > max_comments and isinstance(metadata.get("summary"), dict):
            metadata["summary"].setdefault("notes", []).append(
                f"Showing the top {max_comments} of {len(items)} findings (max-comments)."
            )
        items = items[:max_comments]

    with open(items_path, "w", encoding="utf-8") as output:
        json.dump(items, output, ensure_ascii=False, indent=2)

    review_body = env("REVIEW_BODY") or build_summary(metadata, items)
    write_output("item-count", len(items))
    write_output("total-count", total_count)
    write_output("skipped-existing-count", skipped_existing)
    write_output("resolved-count", resolved_count)
    write_output("should-fail", "true" if fail else "false")
    write_output("summary", build_summary(metadata, items))
    write_output("review-body", review_body)
    print(f"Wrote {len(items)} new item(s) to {items_path} ({total_count} current finding(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

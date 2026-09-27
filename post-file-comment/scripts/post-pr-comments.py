#!/usr/bin/env python3
"""
Generic PR-comment poster.

Reads a JSON array from ITEMS_FILE -- each item may be shaped however the
caller likes, nested arbitrarily -- renders each one through the template
file at MESSAGE_TEMPLATE_FILE, and posts the results as inline review
comments on a Forgejo/Gitea pull request.

Template placeholders and the PATH_FIELD/LINE_FIELD inputs all use the
same small dotted/indexed path syntax to reach into a nested item, e.g.:
    {location.file}
    {range.start.line}
    {tags[0]}
so items can come from any tool's JSON output as long as one consistent
path/line lookup is configured -- the rest of an item's shape is free-form.

api-url/owner/repo/pr-number/head-sha/token all come straight from the
action's inputs, which default to ${{ github.* }} expressions in
action.yml -- this script does no auto-detection of its own.
"""

import json
import os
import re
import sys
from urllib import error
from urllib import request


def die(message):
    print(f"ERROR: {message}")
    sys.exit(1)


def env(name, required=True, default=""):
    value = os.environ.get(name, default)
    if required and not value.strip():
        die(f"Required input/env var {name} is empty.")
    return value


def env_optional(name):
    return os.environ.get(name, "").strip()


def env_bool(name, default=False):
    value = os.environ.get(name, "").strip().lower()
    if value in {"true", "1", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    return default


def resolve_context():
    """Read api-url/owner/repo/pr-number/head-sha/token straight from the
    action's inputs. These all have ${{ github.* }} defaults in action.yml,
    so no auto-detection is needed here -- an empty value just means the
    default expression itself resolved empty (e.g. a non-pull_request
    trigger) and the caller needs to pass it explicitly."""

    api_url = env_optional("API_URL")
    owner = env_optional("OWNER")
    repo = env_optional("REPO")
    pr_number = env_optional("PR_NUMBER")
    head_sha = env_optional("HEAD_SHA")
    token = env_optional("TOKEN")

    missing = [
        name
        for name, value in (
            ("api-url", api_url),
            ("owner", owner),
            ("repo", repo),
            ("pr-number", pr_number),
            ("head-sha", head_sha),
            ("token", token),
        )
        if not value
    ]

    if missing:
        die(
            "Could not resolve: "
            + ", ".join(missing)
            + ". These default to ${{ github.* }} expressions in "
            "action.yml, which only resolve on a pull_request-triggered "
            "job -- pass them explicitly as inputs otherwise."
        )

    return api_url, owner, repo, pr_number, head_sha, token


def normalize_path(path):
    path = str(path).strip().strip("\"'").replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    while path.startswith("/"):
        path = path[1:]
    return path


def load_items(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        die(f"Failed to read items file '{path}': {exc}")

    if not isinstance(data, list):
        die(f"Items file '{path}' must contain a JSON array.")

    return data


def load_template_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as exc:
        die(f"Failed to read message template file '{path}': {exc}")


# ------------------------------------------------------------
# Dotted/indexed path lookup, e.g. "location.range.start.line"
# or "tags[0].name", used for both PATH_FIELD/LINE_FIELD and for
# {placeholder} substitution in the template -- lets an item be
# any shape the caller's tool happens to emit.
# ------------------------------------------------------------

PATH_TOKEN_RE = re.compile(r"[^.\[\]]+|\[\d+\]")


def get_nested(item, dotted_path):
    """Returns (value, found). found=False if any step of the path is
    missing/out of range, so callers can distinguish "empty string" from
    "field doesn't exist"."""

    tokens = PATH_TOKEN_RE.findall(dotted_path)
    if not tokens:
        return None, False

    current = item

    for token in tokens:
        if token.startswith("["):
            index = int(token[1:-1])
            if not isinstance(current, list):
                return None, False
            if index >= len(current) or index < -len(current):
                return None, False
            current = current[index]
        else:
            if not isinstance(current, dict) or token not in current:
                return None, False
            current = current[token]

    return current, True


PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_.\[\]]+)\}")


def render_template(template, item):
    def replace(match):
        expr = match.group(1)
        value, found = get_nested(item, expr)
        if not found:
            # Leave unresolved placeholders literal rather than failing
            # the whole run -- easier to spot in the rendered comment
            # than a stack trace, and doesn't block unrelated items.
            return match.group(0)
        return str(value)

    return PLACEHOLDER_RE.sub(replace, template)


def build_comments(items, template, path_field, line_field, dedupe):
    comments = []
    seen = set()
    skipped = 0

    for item in items:
        raw_path, path_found = get_nested(item, path_field)
        raw_line, line_found = get_nested(item, line_field)

        if not path_found or not raw_path:
            skipped += 1
            continue

        if not line_found:
            skipped += 1
            continue

        try:
            line = int(raw_line)
        except (TypeError, ValueError):
            skipped += 1
            continue

        if line < 1:
            skipped += 1
            continue

        path = normalize_path(raw_path)
        body = render_template(template, item)

        if not body.strip():
            skipped += 1
            continue

        if dedupe:
            key = (path, line, body)
            if key in seen:
                continue
            seen.add(key)

        comments.append(
            {
                "path": path,
                "body": body,
                "new_position": line,
                "old_position": 0,
            }
        )

    return comments, skipped


def post_review(api_url, owner, repo, pr_number, head_sha, token, review_body, comments):
    url = f"{api_url.rstrip('/')}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"

    payload = {
        "event": "COMMENT",
        "commit_id": head_sha,
        "comments": comments,
    }

    # Top-level review summary is optional -- an empty/blank review_body
    # means "just the inline comments, no top-level comment".
    if review_body and review_body.strip():
        payload["body"] = review_body

    data = json.dumps(payload).encode("utf-8")

    req = request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    try:
        with request.urlopen(req, timeout=60) as response:
            if 200 <= response.status < 300:
                return True
            print(f"ERROR: Forgejo API returned HTTP {response.status}.")
            return False
    except error.HTTPError as exc:
        # Deliberately do not print request payload or response body.
        print(f"ERROR: Forgejo API returned HTTP {exc.code}.")
        return False
    except error.URLError:
        print("ERROR: Could not connect to Forgejo API.")
        return False
    except TimeoutError:
        print("ERROR: Forgejo API request timed out.")
        return False


def write_output(name, value):
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        return
    try:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")
    except OSError as exc:
        print(f"WARNING: could not write output '{name}': {exc}")


def main():
    items_file = env("ITEMS_FILE")
    message_template_file = env("MESSAGE_TEMPLATE_FILE")
    message_template = load_template_file(message_template_file)
    path_field = env("PATH_FIELD", required=False, default="path")
    line_field = env("LINE_FIELD", required=False, default="line")
    review_body_template = env(
        "REVIEW_BODY",
        required=False,
        default="🤖 **Automated comments**\n\nPosting {count} comment(s).",
    )
    include_review_body = bool(review_body_template.strip())
    dedupe = env_bool("DEDUPE", default=True)
    fail_on_comments = env_bool("FAIL_ON_COMMENTS", default=False)

    api_url, owner, repo, pr_number, head_sha, token = resolve_context()
    print(f"Resolved target: {api_url} {owner}/{repo}#{pr_number} @ {head_sha[:12]}")

    items = load_items(items_file)
    print(f"Loaded {len(items)} item(s) from {items_file}.")

    comments, skipped = build_comments(
        items,
        message_template,
        path_field,
        line_field,
        dedupe,
    )

    print(f"Built {len(comments)} comment(s); skipped {skipped} item(s).")
    write_output("comments-posted", str(len(comments)))

    if not comments:
        print("No comments to post.")
        return 1 if (fail_on_comments and skipped) else 0

    review_body = render_template(review_body_template, {"count": len(comments)})

    if include_review_body:
        print("Posting review (with top-level summary comment)...")
    else:
        print("Posting review (inline comments only, no top-level summary)...")

    success = post_review(
        api_url=api_url,
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        head_sha=head_sha,
        token=token,
        review_body=review_body,
        comments=comments,
    )

    if not success:
        return 1

    print(f"Posted {len(comments)} review comment(s).")

    return 1 if fail_on_comments else 0


if __name__ == "__main__":
    sys.exit(main())
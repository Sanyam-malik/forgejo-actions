#!/usr/bin/env python3
"""
AI code review for Forgejo/Gitea pull requests.

Fetches the PR diff, sends each changed file (chunked to fit the model's
context) to any OpenAI-compatible /chat/completions endpoint (Ollama,
llama.cpp server, vLLM, OpenAI, ...), validates the returned findings
against the lines that are actually visible in the diff, and writes a JSON
array of comment items for the generic "Post PR Comments" action.

Stdlib only. No linters involved -- the model is the reviewer.
"""

import concurrent.futures
import fnmatch
import hashlib
import json
import os
import re
import secrets
import socket
import sys
import time
from pathlib import Path
from urllib import error
from urllib import request

SEVERITY_RANK = {"info": 1, "warning": 2, "error": 3}
SEVERITY_EMOJI = {"error": "🛑", "warning": "⚠️", "info": "💡"}
VALID_FAIL_LEVELS = {"none", "any", "info", "warning", "error"}

CATEGORY_LABELS = {
    "bug": "Bug",
    "security": "Security",
    "performance": "Performance",
    "reliability": "Reliability",
    "maintainability": "Maintainability",
    "testing": "Testing",
    "design": "Design",
    "docs": "Documentation",
}
CATEGORY_ALIASES = {
    "correctness": "bug",
    "logic": "bug",
    "error-handling": "reliability",
    "error_handling": "reliability",
    "robustness": "reliability",
    "readability": "maintainability",
    "style": "maintainability",
    "test": "testing",
    "tests": "testing",
    "documentation": "docs",
    "architecture": "design",
    "api": "design",
    "vulnerability": "security",
}
SEVERITY_ALIASES = {
    "critical": "error",
    "high": "error",
    "major": "error",
    "medium": "warning",
    "moderate": "warning",
    "warn": "warning",
    "low": "info",
    "minor": "info",
    "nit": "info",
    "suggestion": "info",
    "note": "info",
}

DEFAULT_EXCLUDES = (
    "package-lock.json,yarn.lock,pnpm-lock.yaml,poetry.lock,Pipfile.lock,"
    "Cargo.lock,go.sum,composer.lock,Gemfile.lock,*.lock,"
    "*.min.js,*.min.css,*.map,*.svg,*.png,*.jpg,*.jpeg,*.gif,*.ico,*.pdf,"
    "*.woff,*.woff2,*.ttf,*.zip,*.gz,*.jar,*.snap,*.pb.go,*_generated.*,"
    "node_modules/*,vendor/*,dist/*,build/*"
)

FINGERPRINT_RE = re.compile(r"<!--\s*ai-review:([0-9a-f]{8,40})\s*-->")
# Second marker added when a finding's fingerprint disappears from a later
# run (i.e. it looks fixed) and we've edited the comment to say so. See
# mark_fixed_comments() -- Forgejo's REST API has no "resolve conversation"
# endpoint (only an undocumented, session-authenticated web route), so
# editing the comment body is the actual, stable mechanism.
RESOLVED_RE = re.compile(r"<!--\s*ai-review-resolved:([0-9a-f]{8,40})\s*-->")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
MAX_LINE_CHARS = 400
SNAP_DISTANCE = 3


class LLMError(Exception):
    pass


# ------------------------------------------------------------
# small helpers
# ------------------------------------------------------------

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
    except ValueError:
        die(f"Input {name} must be a number, got '{raw}'.")


def env_limit(name):
    """Optional cap: unset, 0 or negative all mean 'no limit' (returns None)."""
    value = env_num(name, 0)
    return value if value > 0 else None


def write_output(name, value):
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        return
    value = str(value)
    try:
        with open(output_file, "a", encoding="utf-8") as f:
            if "\n" in value:
                delimiter = f"EOF_{secrets.token_hex(8)}"
                f.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
            else:
                f.write(f"{name}={value}\n")
    except OSError as exc:
        print(f"WARNING: could not write output '{name}': {exc}")


def split_patterns(raw):
    return [p.strip() for p in re.split(r"[,\n]", raw or "") if p.strip()]


def path_matches(path, patterns):
    base = path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(base, p) for p in patterns)


def normalize_path(path):
    path = str(path).strip().strip("\"'").replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


# ------------------------------------------------------------
# Forgejo API
# ------------------------------------------------------------

def forgejo_get(ctx, suffix, accept="application/json", timeout=60):
    url = f"{ctx['api_url'].rstrip('/')}/repos/{ctx['owner']}/{ctx['repo']}{suffix}"
    req = request.Request(
        url,
        method="GET",
        headers={"Authorization": f"token {ctx['token']}", "Accept": accept},
    )
    with request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def edit_pull_comment(api_url, owner, repo, comment_id, body, token):
    url = f"{api_url.rstrip('/')}/repos/{owner}/{repo}/issues/comments/{comment_id}"
    req = request.Request(
        url,
        data=json.dumps({"body": body}).encode("utf-8"),
        method="PATCH",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with request.urlopen(req, timeout=60) as response:
        return 200 <= response.status < 300


def forgejo_get_paged(ctx, suffix, limit=50, max_pages=20):
    results = []
    previous = None
    joiner = "&" if "?" in suffix else "?"
    for page in range(1, max_pages + 1):
        data = json.loads(forgejo_get(ctx, f"{suffix}{joiner}page={page}&limit={limit}"))
        if not isinstance(data, list) or not data or data == previous:
            break
        results.extend(data)
        if len(data) < limit:
            break
        previous = data
    return results


def fetch_pr_meta(ctx):
    try:
        data = json.loads(forgejo_get(ctx, f"/pulls/{ctx['pr_number']}"))
        return str(data.get("title") or ""), str(data.get("body") or "")
    except Exception as exc:  # metadata is nice-to-have only
        print(f"WARNING: could not fetch PR title/description: {exc}")
        return "", ""


def fetch_diff(ctx):
    try:
        return forgejo_get(ctx, f"/pulls/{ctx['pr_number']}.diff", accept="text/plain")
    except error.HTTPError as exc:
        die(f"Could not fetch pull-request diff (HTTP {exc.code}).")
    except (error.URLError, TimeoutError):
        die("Could not fetch pull-request diff.")


def fetch_existing_comments(ctx):
    """Earlier AI comments on this PR that carry our fingerprint marker.
    Best effort: on any failure we warn and treat it as 'nothing posted
    yet' -- we never fail the run just to de-duplicate or auto-resolve,
    since posting a duplicate comment is far less harmful than silently
    dropping findings."""
    found = []
    try:
        for review in forgejo_get_paged(ctx, f"/pulls/{ctx['pr_number']}/reviews"):
            review_id = review.get("id")
            if review_id is None:
                continue
            comments = forgejo_get_paged(
                ctx, f"/pulls/{ctx['pr_number']}/reviews/{review_id}/comments"
            )
            for comment in comments:
                comment_id = comment.get("id")
                body = str(comment.get("body") or "")
                fingerprints = FINGERPRINT_RE.findall(body)
                if comment_id is None or not fingerprints:
                    continue
                found.append(
                    {
                        "id": comment_id,
                        "body": body,
                        # Exactly one fingerprint marker per comment, always
                        # (we render it once, at post time).
                        "fingerprint": fingerprints[0],
                        "already_resolved": bool(RESOLVED_RE.search(body)),
                    }
                )
    except Exception as exc:
        print(f"WARNING: could not load existing review comments ({exc}); not de-duplicating.")
    return found


def mark_fixed_comments(ctx, stale_comments, head_sha):
    """Edit each comment whose finding is no longer present, so the thread
    reads as resolved without relying on a native 'resolve conversation'
    API -- Forgejo's REST API does not expose one (only an undocumented,
    session-authenticated web route), so this comment edit is the actual,
    stable mechanism."""
    fixed_note = (
        f"✅ **Fixed** by `{head_sha[:12]}` (no longer detected on the latest commit)."
        if head_sha
        else "✅ **Fixed** (no longer detected on the latest commit)."
    )

    resolved = 0
    for comment in stale_comments:
        new_body = (
            f"{comment['body'].rstrip()}\n\n---\n{fixed_note}"
            f"\n<!-- ai-review-resolved:{comment['fingerprint']} -->"
        )
        try:
            if edit_pull_comment(ctx['api_url'], ctx['owner'], ctx['repo'], comment['id'], new_body, ctx['token']):
                resolved += 1
            else:
                print(f"WARNING: could not mark comment {comment['id']} as fixed.")
        except Exception as exc:
            print(f"WARNING: could not mark comment {comment['id']} as fixed ({exc}).")

    return resolved


# ------------------------------------------------------------
# diff parsing / rendering
# ------------------------------------------------------------

def parse_diff(diff_text):
    """Return a list of {path, entries:[(kind, new_no, text)]}.
    kind is one of: hunk, add, ctx, del. Deleted/binary files are dropped."""
    files = []
    current = None
    in_hunk = False
    new_no = 0

    for raw in diff_text.splitlines():
        if raw.startswith("diff --git "):
            current = {"path": None, "deleted": False, "binary": False, "entries": []}
            files.append(current)
            in_hunk = False
            continue

        if current is None:
            continue

        if not in_hunk:
            if raw.startswith("+++ "):
                target = raw[4:].split("\t")[0].strip()
                if target == "/dev/null":
                    current["deleted"] = True
                else:
                    current["path"] = normalize_path(target[2:] if target.startswith("b/") else target)
                continue
            if raw.startswith("deleted file mode"):
                current["deleted"] = True
                continue
            if raw.startswith("rename to ") and not current["path"]:
                current["path"] = normalize_path(raw[len("rename to "):])
                continue
            if raw.startswith("Binary files") or raw.startswith("GIT binary patch"):
                current["binary"] = True
                continue

        match = HUNK_RE.match(raw)
        if match:
            in_hunk = True
            new_no = int(match.group(1))
            current["entries"].append(("hunk", None, raw))
            continue

        if not in_hunk:
            continue

        if raw.startswith("+"):
            current["entries"].append(("add", new_no, raw[1:]))
            new_no += 1
        elif raw.startswith("-"):
            current["entries"].append(("del", None, raw[1:]))
        elif raw.startswith("\\"):
            continue  # "\ No newline at end of file"
        else:
            current["entries"].append(("ctx", new_no, raw[1:] if raw.startswith(" ") else raw))
            new_no += 1

    return [
        f for f in files
        if f["path"] and not f["deleted"] and not f["binary"]
        and any(kind == "add" for kind, _, _ in f["entries"])
    ]


def render_entry(entry):
    kind, number, text = entry
    if len(text) > MAX_LINE_CHARS:
        text = text[:MAX_LINE_CHARS] + " …[truncated]"
    if kind == "hunk":
        return text
    if kind == "add":
        return f"{number:>5} + {text}"
    if kind == "ctx":
        return f"{number:>5}   {text}"
    return f"      - {text}"


def chunk_entries(entries, max_chars):
    """Split annotated diff lines into chunks under max_chars. Line numbers
    are on every line, so cutting mid-hunk never loses position info."""
    chunks, current, size = [], [], 0
    for entry in entries:
        rendered = render_entry(entry)
        if current and size + len(rendered) + 1 > max_chars:
            chunks.append(current)
            current, size = [], 0
        current.append(rendered)
        size += len(rendered) + 1
    if current:
        chunks.append(current)
    return ["\n".join(chunk) for chunk in chunks]


# ------------------------------------------------------------
# LLM call
# ------------------------------------------------------------

def call_llm(cfg, system_prompt, user_prompt):
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if cfg["api_key"]:
        headers["Authorization"] = f"Bearer {cfg['api_key']}"

    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
        "stream": False,
    }
    if cfg["json_mode"]:
        payload["response_format"] = {"type": "json_object"}

    adaptations = 0
    transient = 0

    while True:
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        try:
            with request.urlopen(req, timeout=cfg["timeout"]) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            break
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            lowered = body.lower()

            # Different OpenAI-compatible servers reject different optional
            # parameters; drop/rename the offending one and retry.
            if exc.code in (400, 422) and adaptations < 4:
                adaptations += 1
                if "max_completion_tokens" in lowered and "max_tokens" in payload:
                    payload["max_completion_tokens"] = payload.pop("max_tokens")
                    continue
                if "temperature" in lowered and "temperature" in payload:
                    payload.pop("temperature")
                    continue
                if "response_format" in payload:
                    payload.pop("response_format")
                    continue

            if exc.code in (408, 429, 500, 502, 503, 504) and transient < 3:
                transient += 1
                time.sleep(2 ** transient)
                continue

            raise LLMError(f"HTTP {exc.code}: {body}")
        except (error.URLError, TimeoutError, socket.timeout, ConnectionError) as exc:
            if transient < 2:
                transient += 1
                time.sleep(2 ** transient)
                continue
            raise LLMError(f"connection failed: {exc}")
        except json.JSONDecodeError:
            raise LLMError("endpoint returned a non-JSON response")

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("unexpected response shape (no choices[0].message.content)")

    if isinstance(content, list):
        content = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )

    return str(content or "")


def extract_findings(text):
    """Pull the findings list out of a model reply, tolerating reasoning
    tags, markdown fences, chatty preambles, and replies truncated by
    max_tokens (in which case every complete finding object is salvaged)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    decoder = json.JSONDecoder()

    salvaged = []
    saw_empty_list = False
    index = 0
    attempts = 0

    while index < len(text) and attempts < 300:
        if text[index] not in "{[":
            index += 1
            continue

        attempts += 1
        try:
            obj, consumed = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            index += 1
            continue

        if isinstance(obj, dict):
            for key in ("findings", "issues", "comments", "results"):
                if isinstance(obj.get(key), list):
                    return obj[key]
            if "message" in obj and "line" in obj:
                salvaged.append(obj)
        elif isinstance(obj, list):
            if obj and all(isinstance(i, dict) for i in obj):
                return obj
            if not obj:
                saw_empty_list = True

        index += consumed

    if salvaged:
        return salvaged
    if saw_empty_list:
        return []

    raise LLMError("could not find a JSON findings object in the model reply")


# ------------------------------------------------------------
# finding validation
# ------------------------------------------------------------

def normalize_severity(value):
    value = str(value or "").strip().lower()
    value = SEVERITY_ALIASES.get(value, value)
    return value if value in SEVERITY_RANK else "info"


def normalize_category(value):
    value = str(value or "").strip().lower()
    value = CATEGORY_ALIASES.get(value, value)
    return value if value in CATEGORY_LABELS else "maintainability"


def to_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def snap_line(line, allowed):
    if line in allowed:
        return line
    nearby = [n for n in allowed if abs(n - line) <= SNAP_DISTANCE]
    if not nearby:
        return None
    return min(nearby, key=lambda n: (abs(n - line), n))


def code_fence(code):
    fence = "```"
    while fence in code:
        fence += "`"
    return fence


def clean_suggestion(raw):
    text = str(raw or "").strip("\n")
    if not text.strip():
        return ""
    text = re.sub(r"^\s*```[\w+-]*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)
    return text.rstrip()


def make_item(raw, file_info, line_text, model):
    """Validate one raw finding; returns an item dict or None."""
    if not isinstance(raw, dict):
        return None

    message = str(raw.get("message") or raw.get("description") or "").strip()
    line = to_int(raw.get("line"))
    if not message or line is None:
        return None

    line = snap_line(line, file_info["allowed"])
    if line is None:
        return None

    severity = normalize_severity(raw.get("severity"))
    category = normalize_category(raw.get("category"))

    try:
        confidence = float(raw.get("confidence", 0.7))
    except (TypeError, ValueError):
        confidence = 0.7
    confidence = max(0.0, min(1.0, confidence))

    title = str(raw.get("title") or "").strip()
    if not title:
        title = re.split(r"(?<=[.!?])\s", message, maxsplit=1)[0][:80]
        # A one-sentence message would just repeat the derived title.
        if message.rstrip(". ") == title.rstrip(". "):
            message = ""

    end_line = to_int(raw.get("end_line"))
    line_range = str(line)
    if end_line and line < end_line <= line + 50:
        line_range = f"{line}-{end_line}"

    suggestion = clean_suggestion(raw.get("suggestion"))
    suggestion_block = ""
    if suggestion:
        fence = code_fence(suggestion)
        suggestion_block = f"**Suggested change**\n\n{fence}\n{suggestion}\n{fence}"

    normalized_line = re.sub(r"\s+", " ", line_text.get(line, "")).strip()
    normalized_title = re.sub(r"\W+", " ", title.lower()).strip()
    fingerprint = hashlib.sha1(
        f"{file_info['path']}|{category}|{normalized_title}|{normalized_line}".encode("utf-8")
    ).hexdigest()[:12]

    label = CATEGORY_LABELS[category]
    return {
        "path": file_info["path"],
        "line": line,
        "line_range": line_range,
        "severity": severity,
        "category": category,
        "confidence": round(confidence, 2),
        "title": title,
        "message": message,
        "suggestion": suggestion,
        "suggestion_block": suggestion_block,
        "header": f"{SEVERITY_EMOJI[severity]} **{label}** · {severity}",
        "footer": (
            f"<sub>🤖 AI review · {model} · confidence {int(round(confidence * 100))}%"
            " · may be wrong, please verify</sub>"
        ),
        "fingerprint": fingerprint,
        "fingerprint_marker": f"\n<!-- ai-review:{fingerprint} -->",
    }


# ------------------------------------------------------------
# prompt assembly
# ------------------------------------------------------------

def read_text(path, limit=None):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        die(f"Could not read '{path}': {exc}")
    return text[:limit] if limit else text


def build_system_prompt(focus):
    prompt_file = env("SYSTEM_PROMPT_FILE") or str(
        Path(__file__).resolve().parent / "prompts" / "system.md"
    )
    prompt = read_text(prompt_file)

    focus_items = split_patterns(focus)
    focus_text = (
        "\n".join(f"- {item}" for item in focus_items)
        if focus_items
        else "- all of the areas below"
    )
    prompt = prompt.replace("<<FOCUS>>", focus_text)
    prompt = prompt.replace("<<MAX_FINDINGS>>", "no fixed limit")

    guidelines_file = env("GUIDELINES_FILE")
    if guidelines_file:
        if Path(guidelines_file).is_file():
            prompt += (
                "\n\n## Project-specific guidelines\n"
                "Follow these repository conventions when reviewing:\n\n"
                + read_text(guidelines_file, limit=6000)
            )
        else:
            print(f"WARNING: guidelines file '{guidelines_file}' not found; ignoring.")

    extra = env("EXTRA_INSTRUCTIONS")
    if extra:
        prompt += f"\n\n## Additional instructions\n{extra}"

    return prompt


def build_user_prompt(title, body, segments):
    """segments: list of (file_info, part_index, part_total, annotated_diff)."""
    parts = []
    if title:
        parts.append(f"Pull request title: {title}")
    if body.strip():
        parts.append(f"Pull request description:\n{body.strip()[:2000]}")
    parts.append(
        "The diffs below show the NEW version of each file. The left column is the "
        'line number in the new file. Lines marked "+" were added, unmarked lines are '
        'unchanged context, and lines marked "-" were removed (they have no number). '
        "Report findings only on numbered lines."
    )
    if len(segments) > 1:
        parts.append(
            'This request contains several files. Set "file" on every finding to the '
            "exact path from its section header."
        )
    for file_info, idx, total, chunk in segments:
        note = f" (part {idx} of {total})" if total > 1 else ""
        parts.append(f"=== FILE: {file_info['path']}{note} ===\n```diff\n{chunk}\n```")
    return "\n\n".join(parts)


def resolve_file(segments, raw_file):
    """Map the model's 'file' value back to one of the files in this request."""
    if len(segments) == 1:
        return segments[0][0]

    wanted = normalize_path(raw_file or "")
    if not wanted:
        return None

    infos = {}
    for segment in segments:
        infos.setdefault(segment[0]["path"], segment[0])

    if wanted in infos:
        return infos[wanted]

    matches = [
        info for path, info in infos.items()
        if path.endswith("/" + wanted)
        or wanted.endswith("/" + path)
        or path.rsplit("/", 1)[-1] == wanted
    ]
    return matches[0] if len(matches) == 1 else None


def make_jobs(units, max_chars, batch):
    """Group diff chunks into requests. Small chunks share a request (up to
    max_chars) so a PR with many small files needs only a few model calls;
    big chunks always go alone."""
    if not batch:
        return [[unit] for unit in units]

    jobs, current, size = [], [], 0
    threshold = max_chars // 2

    for unit in units:
        length = len(unit[3])
        if length > threshold:
            if current:
                jobs.append(current)
                current, size = [], 0
            jobs.append([unit])
            continue
        if current and size + length > max_chars:
            jobs.append(current)
            current, size = [], 0
        current.append(unit)
        size += length

    if current:
        jobs.append(current)
    return jobs


def job_label(job):
    names = []
    for unit in job:
        name = unit[0]["path"]
        if name not in names:
            names.append(name)
    label = ", ".join(names)
    return label if len(label) <= 90 else label[:87] + "..."


# ------------------------------------------------------------
# main
# ------------------------------------------------------------

def should_fail(items, fail_level):
    if fail_level == "none" or not items:
        return False
    if fail_level == "any":
        return True
    threshold = SEVERITY_RANK[fail_level]
    return any(SEVERITY_RANK.get(i["severity"], 1) >= threshold for i in items)


def build_summary(items, model, files_reviewed, notes):
    counts = {sev: sum(1 for i in items if i["severity"] == sev) for sev in SEVERITY_RANK}
    parts = [
        f"{SEVERITY_EMOJI[sev]} {counts[sev]} {sev}"
        for sev in ("error", "warning", "info")
        if counts[sev]
    ]
    lines = [
        f"🤖 **AI code review** · `{model}`",
        "",
        f"Reviewed {files_reviewed} changed file(s) and found {len(items)} "
        f"issue(s){': ' + ' · '.join(parts) if parts else ''}.",
    ]
    for note in notes:
        lines.append(f"- {note}")
    lines += ["", "_AI-generated review; it can be wrong or miss context. Please verify before acting._"]
    return "\n".join(lines)


def main():
    base_url = env("AI_BASE_URL")
    model = env("AI_MODEL")
    if not base_url:
        die("Input ai-base-url is required.")
    if not model:
        die("Input ai-model is required.")

    fail_level = env("FAIL_LEVEL", "none").lower()
    if fail_level not in VALID_FAIL_LEVELS:
        die(f"Unsupported fail level: {fail_level}")

    level = env("LEVEL", "warning").lower()
    if level not in SEVERITY_RANK:
        die(f"Unsupported level: {level} (use info, warning, or error)")

    ctx = {
        "api_url": env("API_URL"),
        "owner": env("OWNER"),
        "repo": env("REPO"),
        "pr_number": env("PR_NUMBER"),
        "token": env("TOKEN"),
    }
    missing = [k for k, v in ctx.items() if not v]
    if missing:
        die(
            "Missing context: " + ", ".join(m.replace("_", "-") for m in missing)
            + ". This action must run on a pull_request-triggered job."
        )
    # Only used for the "Fixed by <sha>" note on auto-resolved comments;
    # its absence should never block the run, so it's not in ctx's
    # required-context check above.
    head_sha = env("HEAD_SHA")

    cfg = {
        "base_url": base_url,
        "api_key": env("AI_API_KEY"),
        "model": model,
        "temperature": env_num("AI_TEMPERATURE", 0.1, float),
        "max_tokens": env_num("AI_MAX_TOKENS", 4096),
        "timeout": env_num("AI_TIMEOUT", 180),
        "json_mode": env_bool("AI_JSON_MODE", True),
    }

    min_confidence = env_num("MIN_CONFIDENCE", 0.5, float)
    max_comments = env_limit("MAX_COMMENTS")
    max_files = env_limit("MAX_FILES")
    max_requests = env_limit("MAX_REQUESTS")
    max_chars = max(2000, env_num("MAX_CHARS", 20000))
    concurrency = max(1, env_num("CONCURRENCY", 4))
    batch_files = env_bool("BATCH_FILES", True)
    skip_existing = env_bool("SKIP_EXISTING", True)
    fail_on_ai_error = env_bool("FAIL_ON_AI_ERROR", False)
    items_output = env("ITEMS_OUTPUT", "ai-review-items.json")

    includes = split_patterns(env("INCLUDE"))
    raw_exclude = env("EXCLUDE")
    excludes = [] if raw_exclude.lower() == "none" else split_patterns(raw_exclude or DEFAULT_EXCLUDES)

    # Look up earlier AI comments in the background while the model works.
    background = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    existing_future = (
        background.submit(fetch_existing_comments, ctx) if skip_existing else None
    )

    # ---- diff -> reviewable files ----
    print(f"Fetching diff for PR #{ctx['pr_number']}...")
    files = parse_diff(fetch_diff(ctx))
    print(f"Files with added lines: {len(files)}")

    notes = []
    selected = []
    for f in files:
        if includes and not path_matches(f["path"], includes):
            continue
        if path_matches(f["path"], excludes):
            continue
        selected.append(f)

    excluded_count = len(files) - len(selected)
    if excluded_count:
        print(f"Excluded by include/exclude patterns: {excluded_count}")

    if max_files and len(selected) > max_files:
        skipped = len(selected) - max_files
        notes.append(f"{skipped} file(s) skipped (over the max-files limit of {max_files}).")
        print(f"Skipping {skipped} file(s) over max-files={max_files}")
        selected = selected[:max_files]

    title, body = fetch_pr_meta(ctx)
    system_prompt = build_system_prompt(env("FOCUS"))

    # ---- build requests ----
    units = []
    for f in selected:
        f["allowed"] = {n for kind, n, _ in f["entries"] if kind in ("add", "ctx")}
        f["line_text"] = {n: text for kind, n, text in f["entries"] if kind in ("add", "ctx")}
        chunks = chunk_entries(f["entries"], max_chars)
        for idx, chunk in enumerate(chunks, start=1):
            units.append((f, idx, len(chunks), chunk))

    jobs = make_jobs(units, max_chars, batch_files)

    if max_requests and len(jobs) > max_requests:
        dropped = len(jobs) - max_requests
        notes.append(f"{dropped} request(s) skipped (over the max-requests limit of {max_requests}).")
        print(f"Skipping {dropped} request(s) over max-requests={max_requests}")
        jobs = jobs[:max_requests]

    files_reviewed = len({unit[0]["path"] for job in jobs for unit in job})
    print(
        f"Sending {len(jobs)} request(s) covering {files_reviewed} file(s) to "
        f"{cfg['base_url']} (model {cfg['model']}, concurrency {concurrency})"
    )

    # ---- call the model ----
    def review_one(job):
        label = job_label(job)
        try:
            reply = call_llm(cfg, system_prompt, build_user_prompt(title, body, job))
            raw_findings = extract_findings(reply)
        except LLMError as exc:
            print(f"  FAILED {label}: {exc}")
            return job, None
        print(f"  ok     {label}: {len(raw_findings)} raw finding(s)")
        return job, raw_findings

    started = time.time()
    if concurrency == 1 or len(jobs) <= 1:
        results = [review_one(job) for job in jobs]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(review_one, jobs))
    print(f"Model calls finished in {time.time() - started:.1f}s")

    failed = sum(1 for _, findings in results if findings is None)
    if failed:
        notes.append(f"{failed} of {len(results)} AI request(s) failed; results may be incomplete.")
        print(f"::warning::AI code review: {failed} of {len(results)} request(s) failed; results may be incomplete.")

    # ---- validate / filter ----
    items, seen = [], set()
    dropped_invalid = 0
    for job, raw_findings in results:
        for raw in raw_findings or []:
            raw_file = raw.get("file") if isinstance(raw, dict) else None
            file_info = resolve_file(job, raw_file)
            if file_info is None:
                dropped_invalid += 1
                continue
            item = make_item(raw, file_info, file_info["line_text"], cfg["model"])
            if item is None:
                dropped_invalid += 1
                continue
            if item["fingerprint"] in seen:
                continue
            seen.add(item["fingerprint"])
            items.append(item)

    print(f"Findings after validation: {len(items)} (dropped invalid/off-diff: {dropped_invalid})")

    items = [i for i in items if SEVERITY_RANK[i["severity"]] >= SEVERITY_RANK[level]]
    items = [i for i in items if i["confidence"] >= min_confidence]
    print(f"Findings after level '{level}' / confidence {min_confidence}: {len(items)}")

    total_count = len(items)
    # Evaluated on ALL current findings, not just the new ones, so a PR
    # with an unresolved error keeps failing even though its comment
    # already exists.
    fail = should_fail(items, fail_level)
    print(f"Fail level: {fail_level} -> {'FAIL' if fail else 'ok'}")

    skipped_existing = 0
    resolved_count = 0
    if existing_future is not None:
        current_fingerprints = {i["fingerprint"] for i in items}
        existing_comments = existing_future.result()

        # A finding whose fingerprint used to have a comment but is not in
        # this run's results looks fixed -- mark it, but only once.
        stale = [
            c
            for c in existing_comments
            if not c["already_resolved"] and c["fingerprint"] not in current_fingerprints
        ]
        if stale:
            print(f"{len(stale)} earlier finding(s) look fixed; marking their comments...")
            resolved_count = mark_fixed_comments(ctx, stale, head_sha)
            print(f"Marked {resolved_count} of {len(stale)} comment(s) as fixed.")

        # Skip reposting only fingerprints that are both still open (not
        # marked fixed) and still present in this run's findings. A
        # fingerprint we just marked fixed is deliberately left out, so if
        # the same issue reappears later it gets a brand new comment
        # instead of silently staying marked fixed.
        already_open = {
            c["fingerprint"]
            for c in existing_comments
            if not c["already_resolved"] and c["fingerprint"] in current_fingerprints
        }
        before = len(items)
        items = [i for i in items if i["fingerprint"] not in already_open]
        skipped_existing = before - len(items)
        if skipped_existing:
            print(f"Skipped {skipped_existing} finding(s) already commented on earlier.")
    background.shutdown(wait=False)

    items.sort(key=lambda i: (-SEVERITY_RANK[i["severity"]], -i["confidence"], i["path"], i["line"]))
    if max_comments and len(items) > max_comments:
        notes.append(f"Showing the top {max_comments} of {len(items)} findings (max-comments).")
        items = items[:max_comments]

    with open(items_output, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(items)} item(s) to {items_output} ({total_count} current finding(s) in total).")

    write_output("item-count", len(items))
    write_output("total-count", total_count)
    write_output("skipped-existing-count", skipped_existing)
    write_output("resolved-count", resolved_count)
    write_output("should-fail", "true" if fail else "false")
    write_output("requests-failed", failed)
    write_output("summary", build_summary(items, cfg["model"], files_reviewed, notes))

    if failed and fail_on_ai_error:
        print("fail-on-ai-error is set and at least one AI request failed.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
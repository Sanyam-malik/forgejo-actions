#!/usr/bin/env python3
"""
Ask an OpenAI-compatible chat-completions endpoint to explain a single
linter finding, given some surrounding source context.

The linter finding is treated as ground truth — the model is only asked
to describe it in plain English and suggest a fix. The instructions that
enforce that are kept in an external file (system_prompt.txt) so this
script's logic and the wording of the prompt can be edited/reviewed/
versioned independently, e.g. from a Forgejo Action step.

Exit codes:
  0 - success, JSON result printed to stdout
  1 - configuration / usage error (bad args, missing env, bad files)
  2 - the AI call failed or returned something unusable
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SYSTEM_PROMPT_FILE = os.path.join(SCRIPT_DIR, "prompts", "system_prompt.txt")

# HTTP statuses worth retrying — transient/server-side/rate-limit issues.
RETRYABLE_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}

FENCE_RE = re.compile(
    r"^```[a-zA-Z0-9_-]*\s*\n(.*?)\n?```\s*$",
    re.DOTALL,
)


def die(message):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        die(f"{name} is required")
    return value


def env_float(name, default):
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        print(
            f"WARNING: {name}={raw!r} is not a valid float, using {default}",
            file=sys.stderr,
        )
        return default


def env_int(name, default):
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        print(
            f"WARNING: {name}={raw!r} is not a valid int, using {default}",
            file=sys.stderr,
        )
        return default


def build_endpoint(base_url):
    base_url = base_url.rstrip("/")
    if base_url.endswith("/chat/completions"):
        return base_url
    return f"{base_url}/chat/completions"


def load_system_prompt(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    except OSError as exc:
        die(f"Could not read system prompt file {path!r}: {exc}")

    if not prompt:
        die(f"System prompt file {path!r} is empty")

    return prompt


def load_json_file(path, label):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as exc:
        die(f"Could not read {label} file {path!r}: {exc}")
    except json.JSONDecodeError as exc:
        die(f"{label} file {path!r} is not valid JSON: {exc}")


def load_text_file(path, label, max_chars=None):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as exc:
        die(f"Could not read {label} file {path!r}: {exc}")

    if max_chars and len(text) > max_chars:
        omitted = len(text) - max_chars
        head = text[:max_chars]
        text = (
            f"{head}\n\n"
            f"[... truncated {omitted} characters to fit context limit ...]"
        )

    return text


def strip_code_fence(content):
    """Handle models that wrap JSON in ```json ... ``` fences."""
    match = FENCE_RE.match(content.strip())
    if match:
        return match.group(1).strip()
    return content


def parse_ai_json(content):
    content = strip_code_fence(content.strip())

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        print("AI returned invalid suggestion JSON.", file=sys.stderr)
        return None

    if not isinstance(result, dict):
        print("AI JSON response was not an object.", file=sys.stderr)
        return None

    description = result.get("description", "")
    suggestion = result.get("suggestion", "")

    if not isinstance(description, str):
        description = ""
    if not isinstance(suggestion, str):
        suggestion = ""

    description = description.strip()
    suggestion = suggestion.strip()

    if not description and not suggestion:
        print("AI response had no usable description or suggestion.", file=sys.stderr)
        return None

    return {"description": description, "suggestion": suggestion}


def request_once(url, headers, data, timeout):
    """Single HTTP attempt. Returns (status_or_None, parsed_body_or_None, error_str_or_None)."""
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body), None
    except urllib.error.HTTPError as exc:
        # Don't leak response bodies (may contain sensitive upstream detail).
        return exc.code, None, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return None, None, f"connection error: {exc.reason}"
    except TimeoutError:
        return None, None, "request timed out"
    except json.JSONDecodeError:
        return None, None, "invalid JSON in response body"


def call_ai(
    base_url,
    api_key,
    model,
    temperature,
    max_tokens,
    finding,
    source_context,
    system_prompt,
    timeout,
    max_retries,
    backoff_seconds,
):
    url = build_endpoint(base_url)

    user_prompt = json.dumps(
        {"finding": finding, "source_context": source_context},
        ensure_ascii=False,
        indent=2,
    )

    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    last_error = None

    for attempt in range(1, max_retries + 1):
        started = time.monotonic()
        status, response_data, error = request_once(url, headers, data, timeout)
        elapsed = time.monotonic() - started

        if error is None:
            print(
                f"AI call succeeded on attempt {attempt}/{max_retries} "
                f"({elapsed:.1f}s)",
                file=sys.stderr,
            )
            break

        last_error = error
        print(
            f"AI call attempt {attempt}/{max_retries} failed: {error} "
            f"({elapsed:.1f}s)",
            file=sys.stderr,
        )

        retryable = status is None or status in RETRYABLE_STATUSES
        if not retryable or attempt == max_retries:
            print(f"AI call failed, not retrying: {last_error}", file=sys.stderr)
            return None

        sleep_for = backoff_seconds * (2 ** (attempt - 1))
        time.sleep(sleep_for)
    else:
        return None

    try:
        content = response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print("AI endpoint returned an unexpected response shape.", file=sys.stderr)
        return None

    if not isinstance(content, str) or not content.strip():
        print("AI endpoint returned empty content.", file=sys.stderr)
        return None

    return parse_ai_json(content)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Explain a linter finding via an AI chat-completions endpoint."
    )
    parser.add_argument("finding_file", help="Path to a JSON file with the linter finding")
    parser.add_argument("source_context_file", help="Path to a text file with surrounding source code")
    parser.add_argument(
        "--system-prompt-file",
        default=os.environ.get("AI_SYSTEM_PROMPT_FILE", DEFAULT_SYSTEM_PROMPT_FILE),
        help="Path to the system prompt (default: %(default)s, or $AI_SYSTEM_PROMPT_FILE)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    finding = load_json_file(args.finding_file, "finding")

    max_source_chars = env_int("AI_MAX_SOURCE_CHARS", 20000)
    source_context = load_text_file(
        args.source_context_file, "source context", max_chars=max_source_chars
    )

    system_prompt = load_system_prompt(args.system_prompt_file)

    base_url = required_env("AI_BASE_URL")
    model = required_env("AI_MODEL")
    api_key = os.environ.get("AI_API_KEY", "").strip()

    temperature = env_float("AI_TEMPERATURE", 0.0)
    max_tokens = env_int("AI_MAX_TOKENS", 1024)
    timeout = env_int("AI_TIMEOUT", 120)
    max_retries = max(1, env_int("AI_MAX_RETRIES", 3))
    backoff_seconds = env_float("AI_RETRY_BACKOFF_SECONDS", 2.0)

    result = call_ai(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        finding=finding,
        source_context=source_context,
        system_prompt=system_prompt,
        timeout=timeout,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
    )

    if result is None:
        sys.exit(2)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
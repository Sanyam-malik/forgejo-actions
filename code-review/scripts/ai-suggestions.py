#!/usr/bin/env python3

import json
import os
import sys
import urllib.error
import urllib.request


def die(message):
    print(
        f"ERROR: {message}",
        file=sys.stderr,
    )
    sys.exit(1)


def required_env(name):
    value = os.environ.get(
        name,
        "",
    ).strip()

    if not value:
        die(
            f"{name} is required"
        )

    return value


def build_endpoint(base_url):
    base_url = base_url.rstrip("/")

    if base_url.endswith(
        "/chat/completions"
    ):
        return base_url

    return (
        f"{base_url}"
        "/chat/completions"
    )


def call_ai(
    base_url,
    api_key,
    model,
    temperature,
    max_tokens,
    finding,
    source_context,
):
    url = build_endpoint(
        base_url
    )

    system_prompt = """
You are a code-review explanation assistant.

A deterministic linter has already identified the finding.
The linter finding is authoritative.

You MUST NOT create new findings.
You MUST NOT dispute or evaluate whether the linter is correct.

Your job is only to explain the existing finding using the
provided source-code context.

Return:

1. description
   A concise explanation of what the linter finding means and
   why it matters in this specific piece of source code.

2. suggestion
   A concise, actionable suggestion for fixing the finding.

Rules:

- Do not invent facts.
- Do not assume code that is not shown.
- Do not claim behavior that cannot be established from the
  supplied source.
- Do not repeat the complete linter message.
- Keep the description concise.
- Keep the suggestion concise.
- Do not include Markdown code fences.
- Return ONLY valid JSON.

Required JSON format:

{
  "description": "string",
  "suggestion": "string"
}
""".strip()

    user_prompt = json.dumps(
        {
            "finding": finding,
            "source_context": source_context,
        },
        ensure_ascii=False,
        indent=2,
    )

    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    }

    data = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    headers = {
        "Content-Type": (
            "application/json"
        ),
        "Accept": (
            "application/json"
        ),
    }

    if api_key:
        headers["Authorization"] = (
            f"Bearer {api_key}"
        )

    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers=headers,
    )

    try:
        with urllib.request.urlopen(
            req,
            timeout=120,
        ) as response:

            response_data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except urllib.error.HTTPError as exc:
        # Do not expose response body.
        print(
            f"AI HTTP error: {exc.code}",
            file=sys.stderr,
        )
        return None

    except urllib.error.URLError:
        print(
            "AI connection error.",
            file=sys.stderr,
        )
        return None

    except TimeoutError:
        print(
            "AI request timed out.",
            file=sys.stderr,
        )
        return None

    except json.JSONDecodeError:
        print(
            "AI endpoint returned invalid JSON.",
            file=sys.stderr,
        )
        return None

    try:
        content = (
            response_data[
                "choices"
            ][0][
                "message"
            ][
                "content"
            ]
        )
    except (
        KeyError,
        IndexError,
        TypeError,
    ):
        print(
            "AI endpoint returned an "
            "unexpected response.",
            file=sys.stderr,
        )
        return None

    if not isinstance(
        content,
        str,
    ):
        return None

    content = content.strip()

    # Some models return:
    #
    # ```json
    # {...}
    # ```
    #
    if content.startswith("```"):
        lines = content.splitlines()

        if lines:
            lines = lines[1:]

        if (
            lines
            and lines[-1].strip()
            == "```"
        ):
            lines = lines[:-1]

        content = "\n".join(
            lines
        ).strip()

    try:
        result = json.loads(
            content
        )
    except json.JSONDecodeError:
        print(
            "AI returned invalid suggestion JSON.",
            file=sys.stderr,
        )
        return None

    if not isinstance(
        result,
        dict,
    ):
        return None

    description = result.get(
        "description",
        "",
    )

    suggestion = result.get(
        "suggestion",
        "",
    )

    if not isinstance(
        description,
        str,
    ):
        description = ""

    if not isinstance(
        suggestion,
        str,
    ):
        suggestion = ""

    description = description.strip()
    suggestion = suggestion.strip()

    if not description and not suggestion:
        return None

    return {
        "description": description,
        "suggestion": suggestion,
    }


def main():
    if len(sys.argv) != 3:
        die(
            "Usage: ai-suggestions.py "
            "<finding-json> "
            "<source-context-file>"
        )

    finding_file = sys.argv[1]
    source_context_file = sys.argv[2]

    try:
        with open(
            finding_file,
            "r",
            encoding="utf-8",
        ) as f:
            finding = json.load(f)

        with open(
            source_context_file,
            "r",
            encoding="utf-8",
            errors="replace",
        ) as f:
            source_context = f.read()

    except Exception as exc:
        die(
            f"Failed to read AI input: {exc}"
        )

    base_url = required_env(
        "AI_BASE_URL"
    )

    model = required_env(
        "AI_MODEL"
    )

    api_key = os.environ.get(
        "AI_API_KEY",
        "",
    ).strip()

    try:
        temperature = float(
            os.environ.get(
                "AI_TEMPERATURE",
                "0",
            )
        )
    except ValueError:
        temperature = 0.0

    try:
        max_tokens = int(
            os.environ.get(
                "AI_MAX_TOKENS",
                "1024",
            )
        )
    except ValueError:
        max_tokens = 1024

    result = call_ai(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        finding=finding,
        source_context=source_context,
    )

    if result is None:
        sys.exit(2)

    print(
        json.dumps(
            result,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
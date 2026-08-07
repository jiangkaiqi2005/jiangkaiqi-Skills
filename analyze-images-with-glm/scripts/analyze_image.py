#!/usr/bin/env python3
"""Send local images or image URLs to GLM-4.6V-Flash for analysis."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4.6v-flash"
API_KEY_ENV_NAMES = ("ZAI_API_KEY", "ZHIPUAI_API_KEY", "BIGMODEL_API_KEY")


def get_api_key() -> str:
    for name in API_KEY_ENV_NAMES:
        value = os.environ.get(name)
        if value:
            return value
    names = ", ".join(API_KEY_ENV_NAMES)
    raise ValueError(f"No API key found. Set one of these environment variables: {names}")


def encode_image(source: str) -> str:
    if source.startswith(("http://", "https://")):
        return source

    path = Path(source).expanduser()
    if not path.is_file():
        raise ValueError(f"Image file does not exist or is not a file: {path}")
    return base64.b64encode(path.read_bytes()).decode("ascii")


def build_payload(images: list[str], prompt: str) -> dict[str, object]:
    content: list[dict[str, object]] = [
        {"type": "image_url", "image_url": {"url": encode_image(image)}}
        for image in images
    ]
    content.append({"type": "text", "text": prompt})
    return {
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "thinking": {"type": "enabled"},
    }


def extract_answer(response: dict[str, object]) -> str:
    try:
        choices = response["choices"]
        message = choices[0]["message"]  # type: ignore[index]
        content = message["content"]  # type: ignore[index]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("API response did not contain choices[0].message.content") from exc

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [item.get("text", "") for item in content if isinstance(item, dict)]
        answer = "".join(part for part in parts if isinstance(part, str))
        if answer:
            return answer
    raise ValueError("API response content was empty or had an unsupported format")


def parse_api_error(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body.strip() or "No response body"

    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(payload)


def analyze(images: list[str], prompt: str, timeout: float) -> str:
    payload = json.dumps(build_payload(images, prompt), ensure_ascii=False).encode("utf-8")
    request = Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {get_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"BigModel API returned HTTP {exc.code}: {parse_api_error(body)}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach the BigModel API: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("BigModel API returned invalid JSON") from exc

    if not isinstance(data, dict):
        raise RuntimeError("BigModel API returned an unexpected JSON value")
    return extract_answer(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze one or more images with the free GLM-4.6V-Flash model."
    )
    parser.add_argument(
        "--image",
        action="append",
        required=True,
        help="Local image path or HTTP(S) URL. Repeat for multiple images.",
    )
    parser.add_argument("--prompt", required=True, help="Specific question about the image(s).")
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="HTTP timeout in seconds (default: 180).",
    )
    args = parser.parse_args()

    try:
        answer = analyze(args.image, args.prompt, args.timeout)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

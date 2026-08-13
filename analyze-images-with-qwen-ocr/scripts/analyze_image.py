#!/usr/bin/env python3
"""Send local images or image URLs to Qwen3.5-OCR for text extraction."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/responses"
MODEL = "qwen3.5-ocr"
API_KEY_ENV_NAMES = ("QWEN35_OCR_API_KEY", "DASHSCOPE_API_KEY")
SUPPORTED_MIME_TYPES = {
    "image/bmp",
    "image/heic",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}
MAX_BASE64_BYTES = 10 * 1024 * 1024


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

    mime_type, _ = mimetypes.guess_type(path.name)
    if mime_type not in SUPPORTED_MIME_TYPES:
        supported = ", ".join(sorted(SUPPORTED_MIME_TYPES))
        raise ValueError(f"Unsupported image type for {path}. Supported MIME types: {supported}")

    encoded = base64.b64encode(path.read_bytes())
    if len(encoded) > MAX_BASE64_BYTES:
        raise ValueError(f"Base64-encoded image exceeds the 10 MB API limit: {path}")
    return f"data:{mime_type};base64,{encoded.decode('ascii')}"


def build_payload(images: list[str], prompt: str) -> dict[str, object]:
    content: list[dict[str, str]] = [
        {"type": "input_image", "image_url": encode_image(image)} for image in images
    ]
    content.append({"type": "input_text", "text": prompt})
    return {
        "model": MODEL,
        "input": [{"role": "user", "content": content}],
    }


def extract_answer(response: dict[str, object]) -> str:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = response.get("output")
    if not isinstance(output, list):
        raise ValueError("API response did not contain output text")

    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            for key in ("text", "ocr_result"):
                value = block.get(key)
                if isinstance(value, str) and value:
                    parts.append(value)
    if parts:
        return "\n".join(parts)
    raise ValueError("API response output was empty or had an unsupported format")


def parse_api_error(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body.strip() or "No response body"

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        if isinstance(error, str):
            return error
        return str(payload.get("message") or payload)
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
        raise RuntimeError(f"DashScope API returned HTTP {exc.code}: {parse_api_error(body)}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach the DashScope API: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("DashScope API returned invalid JSON") from exc

    if not isinstance(data, dict):
        raise RuntimeError("DashScope API returned an unexpected JSON value")
    return extract_answer(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract text from one or more images with Qwen3.5-OCR."
    )
    parser.add_argument(
        "--image",
        action="append",
        required=True,
        help="Local image path or HTTP(S) URL. Repeat for multiple images.",
    )
    parser.add_argument("--prompt", required=True, help="Specific OCR or extraction request.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP timeout in seconds (default: 120).",
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

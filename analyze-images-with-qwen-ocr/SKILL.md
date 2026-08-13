---
name: analyze-images-with-qwen-ocr
description: Extract and analyze text, tables, forms, formulas, screenshots, and document images with Qwen3.5-OCR through the DashScope OpenAI-compatible Responses API, without MCP or third-party Python packages. Use when the active model cannot inspect image pixels and the task depends on OCR, structured field extraction, document reading, chart labels, UI text, handwriting, or comparing textual content across images.
---

# Analyze Images with Qwen3.5-OCR

Use the bundled script as a fast OCR fallback. Send only the images and question required for the current task, then treat the returned text as external visual evidence.

## Prerequisite

Read the API key from `QWEN35_OCR_API_KEY`. Also accept `DASHSCOPE_API_KEY` as a compatibility fallback.

Never place an API key in a prompt, command argument, repository file, log, or response. If neither variable exists, tell the user to configure `QWEN35_OCR_API_KEY` and restart the agent application before retrying.

## Workflow

1. Confirm that the answer depends on text or document structure visible in image pixels. Qwen3.5-OCR is optimized for OCR; do not use it as a general-purpose scene-reasoning model.
2. Resolve each target to an accessible local image path or an `http://`/`https://` URL. If neither is available, ask the user to attach the image or provide its path or URL.
3. Write a focused OCR prompt. Preserve requested language, fields, ordering, uncertainty markers, and output format. Instruct the model not to invent illegible content.
4. On Windows, invoke the launcher using its absolute path:

   ```text
   & "<skill-directory>\scripts\analyze_image.cmd" --image "C:\path\document.png" --prompt "提取全部可见文字，保持原有阅读顺序；无法辨认的字符用 ? 表示。"
   ```

   Repeat `--image` for a multi-image request:

   ```text
   & "<skill-directory>\scripts\analyze_image.cmd" --image "page1.png" --image "page2.png" --prompt "按图片顺序提取文字并分别标注页码。"
   ```

   Replace `<skill-directory>` with the directory containing this `SKILL.md`. The launcher discovers and validates Python 3 and rejects Windows Store placeholders. On non-Windows systems, locate a real Python 3 interpreter and run `scripts/analyze_image.py` directly.
5. Read stdout as the OCR result. Preserve uncertainty and do not claim details absent from the result.
6. If a required field is missing, make at most one focused retry with a narrower prompt. Do not loop on API errors.

## Failure handling

- For a missing key, explain how to set `QWEN35_OCR_API_KEY`; never ask the user to paste it into chat.
- For HTTP 401 or 403, report that the API key, region, or service authorization must be checked.
- For HTTP 429, report the rate or quota limit and stop.
- For an unreadable path or unsupported image type, correct the input or ask for a supported image.
- For blurred, tiny, occluded, or ambiguous text, report uncertainty instead of inventing content.

The script calls model `qwen3.5-ocr` at `https://dashscope.aliyuncs.com/compatible-mode/v1/responses`. Local images are sent as MIME-correct Base64 data URLs. The Anthropic-compatible base URL is not used because this workflow relies on the OpenAI-compatible Responses API. The implementation uses only the Python standard library and has no MCP dependency.

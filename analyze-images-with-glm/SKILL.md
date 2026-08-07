---
name: analyze-images-with-glm
description: Analyze local images, screenshots, or image URLs with the free GLM-4.6V-Flash vision model through the BigModel HTTP API, without MCP or third-party Python packages. Use when the active model cannot see images and a task requires visual description, OCR, chart or diagram reading, UI inspection, object identification, image comparison, or other pixel-dependent reasoning.
---

# Analyze Images with GLM

Use the bundled script as a vision fallback. Send only the images and question needed for the current task, then use the returned text as visual evidence in the main response.

## Prerequisite

Require one of these environment variables to contain a BigModel API key, in priority order:

1. `ZAI_API_KEY`
2. `ZHIPUAI_API_KEY`
3. `BIGMODEL_API_KEY`

Never place an API key in a prompt, command argument, repository file, or response. If no key is configured, tell the user to create one in the BigModel console and set `ZAI_API_KEY` in the environment before retrying.

## Workflow

1. Confirm that the answer depends on image pixels. Do not call the vision model merely because an image is mentioned.
2. Resolve each target to an accessible local file path or an `http://`/`https://` URL. If neither is available, ask the user to attach the image or provide its path or URL.
3. Turn the user's request into a specific visual question. Preserve requested fields, coordinates, language, and output format. Prefer a targeted question over a generic request to describe the image.
4. On Windows, run the bundled launcher. It discovers and validates a real Python 3 interpreter, rejects Windows Store placeholders, and resolves the Python script relative to the launcher:

   ```text
   & "<skill-directory>\scripts\analyze_image.cmd" --image "C:\path\screen.png" --prompt "Read every visible error message exactly and identify the failing UI component."
   ```

   Add `--image` again for comparisons or multi-image questions:

   ```text
   & "<skill-directory>\scripts\analyze_image.cmd" --image "before.png" --image "after.png" --prompt "Compare these images in order and list only visible UI regressions."
   ```

   Replace `<skill-directory>` with the directory containing this `SKILL.md`. Do not invoke bare `python` without validating it. On non-Windows systems, locate a real Python 3 interpreter and run `scripts/analyze_image.py` directly.
5. Read stdout as the model's answer. Treat it as an observation, not as infallible ground truth. Preserve uncertainty and do not claim to have directly seen details absent from the returned text.
6. If the answer misses a required detail, make at most one focused retry with the same image and a narrower prompt. Do not loop on API failures.

## Failure handling

- For a missing environment variable, explain how to set `ZAI_API_KEY`; do not request that the user paste the key into chat.
- For HTTP 401 or 403, report that the API key or account authorization must be checked.
- For HTTP 429, report the rate or quota limit and stop.
- For an unreadable path, correct the path or ask for an accessible image.
- For unsupported or ambiguous visual evidence, state the limitation instead of inventing content.

The Windows launcher searches active virtual environments, Conda, the Python Launcher, `PATH`, the Python registry, and common Anaconda/Miniconda locations across filesystem drives. It accepts only an executable whose version output identifies Python 3. The Python script calls `glm-4.6v-flash` at the official chat-completions endpoint and sends local images as Base64. It uses only the Python standard library and has no MCP dependency.

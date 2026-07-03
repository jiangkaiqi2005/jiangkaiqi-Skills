---
name: hcod-result-reporting
description: Use when HyperCOD/VMamba experiment results are ready and Codex needs to archive train logs, choose or confirm an output root, generate train-log HTML visualizations, identify the best iteration, or collect paper-style metrics.
---

# HCOD Result Reporting

## Overview

Archive a finished HyperCOD experiment into a clear outputs folder, produce a compact report, and verify which checkpoint should be treated as best. The core rule is to classify the experiment family before naming folders; never dump method-family results into the baseline bucket just because paths look similar.

## Workflow

1. Locate the source run directory and artifacts.
   - Find `train.nohup.log`, config, checkpoints, existing `paper_metrics*`, and any previous HTML reports.
   - Read project notes when version semantics are unclear: `CHANGELOG.md`, `version_modules.md`, run-local notes, and nearby configs.

2. Choose the output family name before creating files.
   - Inspect existing directories under the user-specified output root when one is provided. `E:\ViM\outputs` is only an example of a possible root, not a default.
   - Use the method family, not the implementation shortcut. Examples:
     - Basic/baseline experiments: `hcod_hsi_basic_cache_160k/<run-name>`
     - HSC-SAM imitation experiments: `hcod_hsc_sam_cache_160k/<run-name>`
     - RGB/spectral experiments: follow existing `hcod_rgb_*` naming.
   - If unsure whether a run is baseline, HSC-SAM imitation, ablation, or another family, infer from run notes/configs first; ask the user only if local evidence is ambiguous.
   - Keep child folders versioned and descriptive, for example `hcod_hsc_sam_v0.1_cache_160k`.

3. Create or use the destination.
   - If the user did not specify an output root, ask where to put the results before creating or copying files. Do not assume `E:\ViM\outputs`.
   - If the user specifies `E:\ViM\outputs` or another existing convention, prefer that real path when mounted or accessible.
   - If the requested drive is unavailable, create a same-structure local mirror under the repo only as a fallback, such as `outputs/<family>/<run>`, and clearly say it is not the requested root.
   - Copy `train.nohup.log` into the destination. Do not copy unrelated run notes whose labels conflict with the method family.

4. Parse the training log.
   - Extract train points from `Iter(train)` lines: iter, loss, decode/aux losses, accuracy, lr, time.
   - Extract validation points from `Iter(val)` summary lines: iter, `aAcc`, `mIoU`, `mAcc`, `mDice`, timing.
   - Associate validation rows with the immediately preceding checkpoint save when the val line does not include the iter.

5. Pick the best iteration.
   - Default rule: highest validation `mIoU`; break ties by `mDice`, then `aAcc`.
   - If the user names a different primary metric, use that and state the rule.
   - Compare the best point with the latest point. Mention when training loss improves but validation quality regresses.

6. Generate the HTML visualization.
   - Match the style of the closest existing report when the user provides one; otherwise create a self-contained HTML file that opens directly.
   - Include summary cards, training loss curves, validation metric curves, validation table, best-iter conclusion, paper metrics, and the reproduce command.
   - Avoid external CDN dependencies unless the existing report already requires them.

7. Establish paper-style metrics for the selected iter.
   - Prefer running the project tool:

```bash
CUDA_VISIBLE_DEVICES=<gpu> python segmentation/tools/evaluate_hcod_paper_metrics.py \
  <config> <checkpoint> \
  --split test \
  --with-flops \
  --out-dir <destination>/paper_metrics_iter<iter>
```

   - Save `summary_paper_metrics.json`, `summary_paper_metrics.csv`, `per_image_paper_metrics.csv`, and `metrics_command.txt`.
   - If the command fails, debug the root cause. If valid metrics already exist from the same config/checkpoint, copying them is acceptable only with an explicit note in `metrics_command.txt` and the final response.
   - Remove failed-run debris such as timestamped work dirs that only contain failed configs/logs.

8. Verify before reporting completion.
   - Confirm expected files exist and are non-empty.
   - Re-read the validation CSV/JSON and recompute best iter.
   - Confirm the HTML contains embedded data, the best iter, and chart elements.
   - Scan the destination for stale/wrong family names.
   - State anything that could not be verified, such as unavailable `E:` mount or missing browser tooling.

## Required Outputs

- `train.nohup.log`
- `train_log_visualization_<version>.html`
- `validation_summary_<version>.csv`
- `best_iter_analysis_<version>.md`
- `paper_metrics_iter<best_iter>/summary_paper_metrics.json`
- `paper_metrics_iter<best_iter>/summary_paper_metrics.csv`
- `paper_metrics_iter<best_iter>/per_image_paper_metrics.csv`
- `paper_metrics_iter<best_iter>/metrics_command.txt`

## Common Mistakes

- Do not assume `hcod_hsi_basic_cache_160k` is correct just because the source work dir contains HSI/cache/160k. That folder is for baseline/basic runs.
- Do not assume the output root. If the user did not name one, ask first.
- Do not say files were downloaded to the requested root when only a local mirror was created.
- Do not pick the final checkpoint as best without checking validation metrics.
- Do not hide paper-metrics failures. Record the exact failure and whether metrics were copied from an existing successful run.
- Do not leave wrong-name temporary outputs after the user confirms they downloaded the mirror; remove the local mirror when asked.

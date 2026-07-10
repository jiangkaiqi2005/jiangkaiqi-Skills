---
name: structuring-research-workflows
description: Use when a computer vision research method, paper, codebase, model, dataset pipeline, experiment, or deployment system needs to be explained as a rigorous step-by-step workflow or prepared for a publication-style architecture or process diagram.
---

# Structuring Research Workflows

## Overview

Turn computer vision research material into two source-grounded text deliverables: a detailed workflow and a copy-ready prompt for drawing the same workflow as a polished academic figure. Support the full vision research spectrum rather than assuming a particular CNN, Transformer, 2D/3D representation, or learning paradigm. Keep both deliverables structurally identical so every visual module can be traced back to the written method.

## Required References

Read both files on every invocation:

- `references/workflow-template.md` for extracting and writing the detailed workflow.
- `references/diagram-prompt.md` for constructing the complete diagram-generation prompt.

## Output Contract

Return exactly these two top-level sections in the user's language:

1. `详细科研流程`
2. `完整流程图生成提示词`

Place the complete diagram prompt in one fenced text block so it can be pasted directly into ChatGPT or another image-generation system.

Generate text only. Do not call `imagegen`, create an image, or add a third deliverable unless the user explicitly makes a separate request for an actual image.

## Workflow

1. Inspect all supplied material: prose, papers, equations, code, configs, logs, tables, and reference figures.
2. Establish the source of truth. Prefer executable code and active configuration for an implementation diagram; prefer the paper for a paper-method diagram. State material conflicts instead of silently merging them.
3. Build a method graph containing inputs, preprocessing, ordered core stages, branches, joins, objectives, outputs, evaluation, and training-only or inference-only paths.
4. Record exact names, shapes, units, formulas, parameters, and directionality where supported. Mark absent values as `未提供` or `not specified`; never invent them.
5. Write `详细科研流程` using `references/workflow-template.md`.
6. Convert the same method graph into `完整流程图生成提示词` using `references/diagram-prompt.md`.
7. Cross-check one-to-one coverage: every written stage appears in the diagram prompt, every visual module is supported by the written workflow, and every branch reconnects correctly.

## Computer Vision Adaptation

Choose visual primitives from the actual vision task instead of forcing every method into a 3D CNN or generic tensor pipeline:

| Vision research content | Preferred visual primitives |
|---|---|
| Classification, detection, segmentation, or keypoint tasks | images, labels, boxes, masks, heatmaps, feature maps, pyramids, prediction heads |
| Restoration, enhancement, super-resolution, or inverse imaging | degraded/clean image pairs, degradation models, multi-scale features, residual paths, reconstructed outputs |
| Video understanding, action recognition, or tracking | frame sequences, temporal axes, clips, trajectories, memory states, track identities |
| Depth, pose, neural rendering, point cloud, or 3D vision | cameras, rays, depth maps, point clouds, voxels, meshes, projections, coordinate frames |
| Vision Transformers and representation learning | patches, tokens, embeddings, attention or state-space blocks, multi-scale representations |
| Self-supervised, semi-supervised, weakly supervised, or domain-adaptive learning | multi-view augmentations, labeled/unlabeled paths, pseudo-labels, consistency links, source/target domains |
| Vision-language and multimodal learning | image encoders, text tokens, shared embeddings, cross-modal alignment, prompts, retrieval or generation outputs |
| Generative vision and diffusion models | latent variables, noise levels, denoising trajectories, conditions, samplers, generated images |
| Remote sensing, medical imaging, and spectral imaging | modality-specific images, image volumes, spectral cubes, acquisition channels, annotations, clinical or geographic outputs |
| Compression, acceleration, and deployment | teacher/student paths when present, pruning or quantization blocks, hardware targets, latency, memory, throughput |
| Classical vision and geometry | keypoints, descriptors, matches, transforms, optimization loops, geometric constraints |

Use task-specific visual symbols only when supported by the source. Do not add a CNN, Transformer, attention module, distillation path, or 3D tensor merely because it is common in computer vision.

## Accuracy Rules

- Preserve formulas, dimensions, units, stage order, and train/eval distinctions exactly.
- Separate main flow from auxiliary branches with distinct line styles.
- Explain ambiguous or conflicting evidence before the two deliverables when clarification is essential; otherwise list the assumption inside `详细科研流程`.
- Do not claim a method is faithful to a paper when it is an adaptation.
- Do not add fashionable modules, metrics, datasets, or experimental details absent from the source.
- Do not use this skill as a generic workflow formatter for research outside computer vision.

## Example Invocation

```text
Use $structuring-research-workflows to analyze the attached computer vision paper and implementation config. Treat the active config as the source of truth, explain any paper-versus-code differences, then return the detailed workflow and the complete publication-style diagram prompt only.
```

## Visual Rules That Must Survive Every Prompt

- Use a clean white academic canvas and a single restrained title line.
- Never place a blue banner, colored ribbon, badge, star decoration, slogan, or subtitle strip beneath the title.
- Permit only thin hairline rules beside the title when useful.
- Use restrained semantic colors, fine borders, coherent arrows, and task-appropriate computer vision objects.
- Reserve at least 6% safe margin on every side and at least 10% at the bottom.
- Keep all content inside the central 88% of the canvas; shrink or reflow modules instead of cropping.
- Require a final text, topology, and cropping checklist in the diagram prompt.

## Final Check

Before responding, verify:

- There are exactly two top-level output sections.
- The detailed workflow is source-grounded and complete.
- The diagram prompt is self-contained and copy-ready.
- The title area contains no colored banner or promotional decoration.
- The prompt adapts across broad computer vision tasks without defaulting to one architecture family.
- No actual image-generation tool was invoked.

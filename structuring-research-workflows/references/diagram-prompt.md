# Publication-Style Computer Vision Diagram Prompt

Use this reference to produce the `完整流程图生成提示词` section. Write one self-contained prompt that a user can paste into ChatGPT or another image-generation system. Replace generic placeholders with the actual method graph; do not leave bracketed template fields in the final prompt.

## Prompt Structure

Construct the prompt in the following order.

### 1. Primary Request

State that the system must create a new, high-resolution, publication-style computer vision workflow or architecture diagram. If the user supplied a reference image, say it is a style reference only and that obsolete structure or text must not be copied.

Name the exact method, vision task, and visual story in one sentence: input modality → central mechanism → prediction, reconstruction, rendering, generation, or deployment output.

### 2. Canvas and Safe Area

Require:

- landscape orientation, normally 16:9 or a wider ratio when the method is long;
- high resolution, preferably at least 2048×1152;
- pure white background;
- at least 6% safe margin on all sides;
- at least 10% empty safe area below the lowest module;
- all effective content inside the central 88% of the canvas;
- no cropped title, formulas, arrows, legends, outputs, or bottom row.

Tell the generator to reduce module size, wrap text, or reflow rows when space is tight. It must never solve crowding by cutting off the bottom.

### 3. Title Treatment

Specify one centered title line using the exact method name. Optional thin horizontal hairlines may sit to the left and right of the title.

Include these prohibitions verbatim in meaning:

- no blue banner under the title;
- no colored subtitle strip;
- no ribbon, badge, star, slogan, or promotional decoration;
- no oversized marketing typography.

### 4. Visual Language

Request a refined academic aesthetic:

- fine borders and modest corner radii;
- crisp arrows with visible arrowheads;
- restrained semantic colors, not one dominant hue;
- minimal or no shadow;
- no gradients, glow, bokeh, decorative blobs, or watermark;
- consistent type scale and generous internal padding;
- exact scientific notation and sharp text.

Assign colors by function after understanding the method. A useful default is:

- blue for inputs, observations, and data transformations;
- cyan or dashed blue for auxiliary or offline branches;
- purple for the central analytical or computational mechanism;
- green for integration, outputs, predictions, or conclusions;
- orange-red for objectives, losses, constraints, metrics, and saved artifacts;
- gray for context, assumptions, or inactive/reference paths.

Adapt the palette when a vision task or modality benefits from it, while keeping contrast and functional consistency.

### 5. Computer Vision Objects

Choose visual objects from the actual vision method:

- source images, labels, boxes, masks, keypoints, heatmaps, feature maps, pyramids, and prediction heads for 2D recognition;
- degraded/clean image pairs, residual paths, multi-scale features, and reconstructed outputs for restoration and enhancement;
- frame strips, clips, temporal axes, trajectories, memory states, and track identities for video understanding and tracking;
- cameras, rays, coordinate frames, depth maps, point clouds, voxels, meshes, projections, and rendered views for 3D vision and geometry;
- patches, tokens, embeddings, attention or state-space stages, and multi-scale representations for Transformer-style or sequence-based vision models;
- multi-view augmentations, labeled and unlabeled paths, pseudo-labels, consistency links, teacher/student branches only when present, and source/target domains for self-supervised, semi-supervised, weakly supervised, or domain-adaptive learning;
- image encoders, text tokens, prompts, shared embeddings, alignment paths, retrieval results, and generated responses for vision-language and multimodal methods;
- noise levels, latent variables, denoising trajectories, conditions, samplers, and generated images for diffusion or generative vision;
- modality-specific image volumes, spectral cubes, acquisition channels, annotations, and geographic or clinical outputs for medical, remote-sensing, and spectral imaging;
- keypoints, descriptors, correspondences, transforms, geometric constraints, and optimization loops for classical vision;
- compressed models, quantization or pruning stages, hardware devices, latency, memory, throughput, and exported runtimes for deployment research.

Do not force every method into a CNN, 3D tensor, feature pyramid, Transformer, or end-to-end neural pipeline. Use only objects supported by the source.

### 6. Explicit Layout Map

Translate the method graph into named canvas regions. Give approximate vertical bands so the generator cannot improvise a cropped layout. Prefer:

```text
0%–9%: single title line
12%–42%: inputs, preprocessing, and early core stages
44%–72%: central mechanism, branches, aggregation, and outputs
76%–90%: objectives, evaluation, legend, and artifacts
90%–100%: protected empty bottom margin
```

Change these bands when the method needs a different topology, but always reserve the bottom safe area. State each module's left-to-right or top-to-bottom position and each branch's start and endpoint.

### 7. Module-by-Module Content

List every module in reading order. For each module provide exact visible text in quotes, then describe its scientific icon or data object. Include, when supported:

- title;
- operation or mechanism;
- input and output notation;
- channels, spatial resolutions, tokens, frames, points, views, dimensions, scales, coordinate systems, or sample counts;
- key parameter;
- phase note such as training only, inference only, or offline.

Keep labels concise enough to render. Put longer explanations in a small note box rather than shrinking all text.

### 8. Connections and Branch Semantics

Define every arrow:

- solid arrows for the main path;
- dashed arrows for auxiliary, offline, supervision, or reference paths;
- feedback arrows only when feedback truly exists;
- distinct objective arrows for loss, constraints, or optimization;
- clear merge points for parallel branches.

Require lines to avoid crossing text and unrelated modules. State explicitly when a branch affects only an objective and not the main output.

### 9. Bottom Row and Legend

Place objectives, formulas, metrics, outputs, artifacts, and a compact legend in the bottom information band. Keep them above the protected empty margin. Require formulas to remain complete on one or two readable lines.

Only include a legend when multiple color or line semantics actually need explanation.

### 10. Exact Negative Constraints

Add method-specific exclusions from the source analysis. Also always forbid:

- fabricated stages, modules, formulas, parameters, datasets, metrics, or results;
- copied obsolete labels from a reference image;
- duplicated or missing modules;
- wrong branch direction;
- tiny unreadable text;
- overlapping boxes or arrows;
- cropped bottom content;
- title banners and promotional decoration.

### 11. Preflight Checklist

End the prompt by instructing the image generator to verify internally before rendering:

1. The method name and version are exact.
2. Every written workflow stage appears once in the figure.
3. Stage order, branch direction, merges, and phase distinctions are correct.
4. Formulas, dimensions, units, and labels match the supplied source.
5. The title has no banner beneath it.
6. All content remains inside the safe area.
7. The bottom row and blank bottom margin are fully visible.
8. Text is sharp, correctly spelled, and contained within its module.
9. No unsupported scientific element was added.
10. The final output is only the complete diagram, without explanatory prose or watermark.

## Prompt Output Rule

Return the assembled image-generation prompt inside one fenced `text` block. Do not generate the image while using this skill.

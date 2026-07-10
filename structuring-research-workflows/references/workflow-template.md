# Detailed Computer Vision Research Workflow Template

Use this reference to produce the `详细科研流程` section. Match the user's language while preserving official technical names, symbols, formulas, dimensions, and units.

## 1. Establish Scope

Begin with a compact scope statement containing:

- the method, system, or experiment name;
- whether the description follows a paper, implementation, configuration, or proposed design;
- the vision task, input modality, and main input-to-output objective;
- any explicitly excluded component.

If sources disagree, identify the selected source of truth and describe the difference. Do not blend variants into a nonexistent architecture.

## 2. Build the Method Graph

Extract these nodes before writing prose:

1. Visual inputs, modalities, annotations, and data provenance
2. Validation, pairing, sampling, augmentation, normalization, or preprocessing
3. Ordered core stages, whether learned or classical
4. Intermediate images, features, tokens, temporal states, geometric entities, or latent representations
5. Auxiliary, parallel, skip, recurrent, teacher/student, or multi-scale branches when present
6. Fusion, merge, alignment, projection, and aggregation points
7. Objective functions, losses, geometric constraints, or optimization targets
8. Prediction heads, reconstruction modules, rendering stages, or task outputs
9. Inference postprocessing such as decoding, thresholding, matching, suppression, tracking, or sampling
10. Evaluation metrics, visualizations, checkpoints, exported models, and deployment outputs
11. Training-only, inference-only, offline, preprocessing-only, or deployment-only paths

For each node capture, when available:

- purpose;
- operation or mechanism;
- input and output;
- shape, channel count, spatial resolution, token count, frame count, point count, scale, coordinate system, or sample count;
- important parameter values;
- connection to the next node;
- execution phase.

## 3. Write the Detailed Workflow

Use numbered stages. Each stage should answer four questions without forcing rigid labels:

1. What enters this stage?
2. What operation happens?
3. What leaves the stage?
4. Why is the stage needed?

Use compact equations or mappings when they improve precision, for example:

```text
raw visual data → validation and preprocessing → model-ready inputs
images [B,C,H,W] → visual encoder → features [B,C',H',W']
frames → temporal modeling → clip representation or frame-wise predictions
images + camera parameters → geometry or rendering stage → depth, pose, point cloud, or novel view
L_total = L_primary + λL_auxiliary
```

Do not manufacture tensor shapes when a source does not provide them. Classical vision, geometry, tracking, and deployment workflows may be better described with image scales, keypoint counts, coordinate frames, iteration counts, temporal windows, latency, memory, or throughput.

## 4. Describe Branches Explicitly

For every non-main path, state:

- where it starts;
- whether it is parallel, auxiliary, feedback, residual, or offline;
- where it ends or rejoins;
- whether it exists during training, inference, analysis, or all phases.

Never imply that an auxiliary output feeds the main prediction when it only contributes an objective or diagnostic.

## 5. Objectives and Outputs

Write exact formulas when supplied. Otherwise describe the objective verbally and mark unspecified weights or coefficients as `未提供`.

Separate:

- primary objective or hypothesis;
- auxiliary objective or regularization;
- combined objective;
- postprocessing;
- reported metrics;
- probability maps, labels, boxes, masks, keypoints, restored images, generated images, tracks, depth, pose, point clouds, rendered views, files, plots, checkpoints, or deployed models.

## 6. Assumptions and Evidence

End the detailed workflow with a short `口径与假设` paragraph only when needed. Include unresolved values, paper-versus-code differences, or interpretation choices. Do not repeat settled facts.

## Quality Checklist

- Every stage has a supported input, operation, and output.
- Stage order and branch direction are unambiguous.
- Exact formulas, dimensions, units, and parameters are preserved.
- Unsupported details are absent or marked as unspecified.
- The narrative can be mapped directly to diagram modules without reinterpretation.

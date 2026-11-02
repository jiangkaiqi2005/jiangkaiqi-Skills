---
name: hcod-result-reporting
description: HyperCOD 实验 run 的目录契约与交付流程。在 hcod_* 仓库里收尾训练完的 run、评测 checkpoint、生成或交付结果报告、整理或校验 work_dirs 时使用。
---

# HCOD 结果交付

每个 run 是 `work_dirs/` 下的一个目录，结构固定。用户每次只下载 `report/`，所以 `report/` 必须自成一体：三件套齐全、离线可开、和评测结果一致。

## 目录契约

```
work_dirs/                         # 根目录只放 run 目录
  <repo>_v<版本>[_<tag>]/          # 例：hcod_3dcnn_v0.4.2.0、hcod_sam2_unet_v0.1.1.0_rgb_noada
    run.json                       # 清单，见下文
    config.yaml | config.py        # 本 run 实际使用的配置
    train/                         # train.log train.nohup.log metrics.csv native_validation_latest.json training_complete.json，及训练期写出的其他 csv/json
    checkpoints/                   # best_<指标>.pth latest.pth
    eval/<ckpt>_e<epoch>_<split>[_<variant>]/
                                   # summary.json summary.csv per_image.csv command.txt eval.log，及该评测的其他产物
    analysis/<名字>/               # 可选：阈值扫描、诊断、可视化等非标准评测
    report/                        # 交付目录
      summary.json                 # = eval/<best>/summary.json 的复制件
      report.html                  # 自包含：数据和图都内嵌，不引用 CDN 或外部文件
      analysis.md                  # best 的选择依据和指标
      validation_summary.csv       # 可选
      figures/                     # 可选
```

- **文件名不带版本号**：版本只出现在 run 目录名里。
- **eval 目录名**：`<ckpt>` 是 checkpoint 文件名去掉 `.pth`（`best_mae`、`best_cod_mean`、`latest`），`<epoch>` 取 summary 或 checkpoint 里记录的 epoch，`<split>` 是 `val`/`test`。同一 checkpoint、同一 split 用不同协议评测时加 `_<variant>`（如 `_native512`、`_crf`）。例：`eval/best_mae_e57_test/`、`eval/latest_e100_val/`。
- **单一事实源**：`report/summary.json` 是复制件（不是软链接，下载后不会断），源头是 `run.json` 里 `report_source` 指向的那个 eval。
- **代码在仓库里**：评测、报告脚本放在仓库的 `tools/`（没有就用现有的 `scripts/`），`run.json` 只记命令；run 目录只放产物。
- **仓库其他目录**：数据缓存放仓库的 `cache/`，临时诊断放 `scratch/`。
- **父 run 的评测归父 run**：给子 run 做对比时，父 run 的 checkpoint 评测写进父 run 的 `eval/`，子 run 的 `analysis.md` 引用它的路径。

### run.json

```json
{
  "run": "hcod_3dcnn_v0.4.2.0",
  "repo": "hcod_3dcnn_baseline",
  "version": "0.4.2.0",
  "tag": null,
  "status": "done",
  "git_commit": "6def3df",
  "config": "config.yaml",
  "source_config": "configs/hcod_3dcnn_v0.4.2.0.yaml",
  "dataset": "HyperCOD",
  "split": "原划分 train/val/test",
  "best": {
    "checkpoint": "checkpoints/best_mae.pth",
    "epoch": 41,
    "rule": "验证集 MAE 最低",
    "eval": "eval/best_mae_e41_test"
  },
  "metrics": {"test": {"MAE": 0.00283, "S_measure": 0.844}, "val": {"MAE": 0.00234}},
  "report_source": "eval/best_mae_e41_test/summary.json",
  "commands": {"train": "...", "eval": "...", "report": "..."},
  "notes": []
}
```

- `status` 只取 `running`、`done`、`failed`。
- `metrics` 抄 summary 里的核心指标，键名沿用该仓库 summary 的写法。
- `notes` 记删掉的流程文件里值得留下的结论：验收是否通过、改名历史、评测失败原因、checkpoint 身份对不上等。
- 查不到的字段写 `null`，在 notes 里说明原因。

## 流程

### 1. 训练中

训练脚本按仓库现有方式写日志和 checkpoint；pid、lock、queue、launch 记录这些运行时文件可以临时放在 run 根目录。此时 `run.json` 的 `status` 为 `running`。别的 agent 判断一个 run 是否在跑：pid 对应进程活着（`ps -p`、`nvidia-smi`），或日志几分钟内还在增长。在跑的 run 只读不动。

### 2. 收尾

训练结束、进程退出后：

1. 训练产物移进 `train/`，checkpoint 用 `mv` 移进 `checkpoints/`（磁盘紧张；`.pth` 内容保持原样）。
2. **删除流程审计文件**：pid、lock、queue、launch、acceptance、review、rework、gpu receipt、cleanup、protected/source inventory、verification、status 这类记录流程本身的文件。删之前把结论写进 `run.json` 的 `notes`。
3. 写 `run.json`，`status` 改为 `done` 或 `failed`。

### 3. 评测

用仓库里的评测脚本，输出直接指向 `eval/<ckpt>_e<epoch>_<split>/`：

- `evaluate_hcod_paper_metrics.py`（3dcnn、deeplabv3、unet）和 `evaluate_hrssd_paper_metrics.py`：`--out-dir` 必填，直接写 `summary.json`、`summary.csv`、`per_image.csv`、`command.txt`。
- `scripts/evaluate.py`（sam2、vmamba、segman）：`--output eval/<ckpt>_e<epoch>_<split>/summary.json`；不传时写到 run 根目录 `test_<ckpt>.json`，收尾时移进对应 eval 目录并改名为 `summary.json`。

stdout 存成同目录的 `eval.log`。脚本没写 `command.txt` 时手写一份完整可复现的命令。

### 4. 选 best

规则写进 `run.json` 的 `best.rule`，只依据验证集。默认规则：

- `hcod_sam2_unet`、`hcod_vmamba_upernet`、`hcod_segman_baseline`：`best_cod_mean`（`training_complete.json` 的 `default_test_checkpoint`）。
- `hcod_3dcnn_baseline`：`best_iou`（验证集 IoU 最高，并列依次比 Dice、更低的 MAE）。
- `hcod_deeplabv3_baseline`、`hcod_unet_baseline`：`best_mae`。

设计文档或用户指定了别的规则时以指定为准。

### 5. 报告

先写好 `run.json`（`best`、`report_source`），再用仓库里的 `tools/generate_report.py` 生成 `report/`。输入、产物和参数见脚本 `--help`。6 个仓库的这份脚本内容相同，改一份就要同步改其余 5 份。

```bash
python tools/generate_report.py work_dirs/<run>            # dry-run：打印每个文件是新建、覆盖还是跳过
python tools/generate_report.py work_dirs/<run> --write
```

dry-run 没有警告、每个文件都是预期的动作时才加 `--write`。写完后看一眼 `analysis.md` 的结论是否符合实际，再跑下面的自检。

## 交付前自检

运行校验脚本，全部通过才算交付；检查项以脚本 docstring 为准：

```bash
python ~/.agents/skills/hcod-result-reporting/check_run.py <repo>/work_dirs/<run>
python ~/.agents/skills/hcod-result-reporting/check_run.py --work-dirs <repo>/work_dirs   # 整个仓库
```

最后告诉用户 `report/` 的绝对路径，以及脚本没覆盖、你也没能验证的项。

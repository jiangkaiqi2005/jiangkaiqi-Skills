# analyze-images-with-glm

让不具备多模态视觉能力的模型（如 DeepSeek V4）也能读懂图片。

这是一个 Agent Skill。Codex、Claude Code 等 Agent 负责调用脚本，脚本把本地图片或图片 URL 发给智谱 `GLM-4.6V-Flash`；视觉模型分析像素后，再把文字结果交回当前模型继续处理。

有些模型擅长写代码、查资料和操作文件，却不能直接读取截图中的像素。例如 DeepSeek V4 的 [Anthropic 兼容接口](https://api-docs.deepseek.com/guides/anthropic_api) 不支持图片消息；Qwen Code 会为 Qwen3-Coder 等文本主模型另配一个 [`visionModel`](https://qwenlm.github.io/qwen-code-docs/en/users/configuration/settings/)；通过 Ollama 或 vLLM 运行的纯文本模型也需要类似的视觉桥。给它们一个图片路径，不等于让它们看见了图片。

## 能做什么

- 读取截图、扫描件和表格中的文字；
- 分析图表、流程图和界面布局；
- 定位截图中的报错或 UI 问题；
- 比较多张图片的可见差异。

这个 Skill 只分析已有图片，不生成或编辑图片。它不需要 MCP，也不依赖第三方 Python 包。

## 使用前准备

- 一个支持 Agent Skills 的 Agent，例如 Codex App、Codex CLI 或 Claude Code；
- Python 3；
- 能访问智谱 API 的网络；
- 一个[智谱 BigModel API Key](https://open.bigmodel.cn/usercenter/apikeys)。[`GLM-4.6V-Flash`](https://docs.bigmodel.cn/cn/guide/models/free/glm-4.6v-flash) 目前是免费模型，但仍需 API Key，额度和限流以智谱平台为准。

## 安装

### 让 Agent 安装

把下面这段话发给一个支持 Agent Skills 的 Agent：

```text
请从 https://github.com/jiangkaiqi2005/analyze-images-with-glm 下载并安装 analyze-images-with-glm Skill。
请先确认当前 Agent 的用户级 Skills 目录：Codex 使用 ~/.agents/skills，Claude Code 使用 ~/.claude/skills。安装后检查目标目录中直接包含 SKILL.md、scripts/ 和 agents/，并验证 Skill 能被发现。不要读取、回显或保存我的 API Key。
```

Codex 用户也可以直接让 `$skill-installer` 安装这个仓库。

### 手动下载

把仓库克隆到对应目录：

| Agent | 安装目录 |
| --- | --- |
| Codex App / Codex CLI | `~/.agents/skills/analyze-images-with-glm` |
| Claude Code | `~/.claude/skills/analyze-images-with-glm` |

以 Codex 为例，Windows PowerShell：

```powershell
$skillRoot = Join-Path $env:USERPROFILE ".agents\skills"
New-Item -ItemType Directory -Force -Path $skillRoot | Out-Null
git clone https://github.com/jiangkaiqi2005/analyze-images-with-glm `
    (Join-Path $skillRoot "analyze-images-with-glm")
```

macOS 或 Linux：

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/jiangkaiqi2005/analyze-images-with-glm \
  ~/.agents/skills/analyze-images-with-glm
```

使用 Claude Code 时，把命令中的 `.agents/skills` 改成 `.claude/skills`。也可以在 GitHub 点击 **Code → Download ZIP**，解压后将仓库目录放到上表中的位置。若 Agent 没有发现新 Skill，重启一次。

## 配置 API Key

脚本依次读取 `ZAI_API_KEY`、`ZHIPUAI_API_KEY`、`BIGMODEL_API_KEY`，推荐使用 `ZAI_API_KEY`。不要把密钥写进提示词、仓库文件或命令参数。

Windows PowerShell：

```powershell
$secureKey = Read-Host "请输入 ZAI_API_KEY" -AsSecureString
$env:ZAI_API_KEY = [Net.NetworkCredential]::new("", $secureKey).Password
Remove-Variable secureKey
```

macOS 或 Linux：

```bash
read -rsp "请输入 ZAI_API_KEY: " ZAI_API_KEY
echo
export ZAI_API_KEY
```

从同一个终端启动 Agent，它才能读取这个环境变量。

## 使用

在 Codex 中可以直接点名 Skill：

```text
$analyze-images-with-glm 逐字读取 error.png 中的报错，并结合当前仓库判断最可能出错的代码位置。
```

在 Claude Code 或其他兼容 Agent 中，直接说出 Skill 名称和图片任务：

```text
请使用 analyze-images-with-glm Skill 比较 before.png 和 after.png，只列出可见的 UI 差异。
```

也可以要求固定输出格式：

```text
请使用 analyze-images-with-glm 读取 invoice.png，提取日期、商家、总金额和订单号，以 JSON 返回；看不清的字段写 null。
```

需要单独测试脚本时，在 Skill 目录运行：

```powershell
scripts\analyze_image.cmd --image "C:\path\to\screen.png" --prompt "逐字读取截图中的报错。"
```

macOS 或 Linux：

```bash
python3 scripts/analyze_image.py \
  --image "/path/to/screen.png" \
  --prompt "逐字读取截图中的报错。"
```

`--image` 支持本地路径和 HTTP(S) URL；比较多张图片时重复传入 `--image`。

## 隐私与限制

- 图片和问题会发送给智谱 BigModel，请勿上传无权共享的内容；
- API Key 只应保存在环境变量中；
- 视觉模型可能误读模糊文字或细小元素，重要结果仍需对照原图。

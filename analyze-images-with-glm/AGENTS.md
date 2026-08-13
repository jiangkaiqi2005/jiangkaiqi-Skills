# 项目定位

本仓库是一个 Codex 技能：当当前模型无法直接查看图片，而任务又依赖像素内容时，调用智谱 BigModel 的免费 `glm-4.6v-flash` 视觉模型完成图片描述、OCR、图表/界面读取、对象识别和多图比较。它是视觉能力的后备通道，不是通用聊天客户端，也不负责图片生成或编辑。

# 目录与职责

- `SKILL.md`：技能入口和行为契约，规定何时调用、如何组织视觉问题、失败时如何处理。
- `agents/openai.yaml`：Codex 中展示的名称、简介和默认提示词。
- `scripts/analyze_image.cmd`：Windows 入口，把所有参数原样转给 PowerShell 启动器。
- `scripts/find_python_and_run.ps1`：依次搜索虚拟环境、Conda、Python Launcher、`PATH`、注册表和常见安装目录；排除 Windows Store 占位程序，只接受可运行的 Python 3。
- `scripts/analyze_image.py`：唯一的 API 客户端实现，仅使用 Python 标准库。
- `CLAUDE.md`：必须保持为指向本文件的符号链接，避免维护两份代理说明。

# 运行链路

1. 调用方重复传入 `--image`，并提供一个具体的 `--prompt`；`--timeout` 默认 180 秒。
2. Windows 启动器定位真实的 Python 3，并执行相对路径下的 `analyze_image.py`。
3. HTTP(S) 图片 URL 原样发送；本地文件先检查存在性，再读取为 Base64 字符串。
4. 脚本构造单条 user message：图片内容在前，文本问题在后，模型固定为 `glm-4.6v-flash`，并启用思考模式。
5. 请求以非流式 POST 发送到 BigModel Chat Completions 接口；成功答案写入 stdout，参数、文件、网络、HTTP 或响应格式错误写入 stderr，并以退出码 1 结束。

# 开发约束

- 保持实现小而直接。项目当前无第三方 Python 依赖、SDK 或 MCP 依赖；除非需求明确且标准库确实无法满足，否则不要引入依赖。
- 修改必须与请求直接相关，不重构相邻代码，不顺手调整文案或格式。
- `SKILL.md` 是行为事实来源。若命令行参数、模型名、端点、密钥名称、响应解析或启动器搜索策略变化，必须同步更新其中对应说明。
- 若修改用户可见的技能名称、简介或默认调用语句，同步检查 `agents/openai.yaml`。
- 保持 `--image` 可重复使用，并保持本地路径与 HTTP(S) URL 两种输入方式；多图顺序具有语义，不得重排。
- 保持 API 回答只输出到 stdout，诊断信息只输出到 stderr；不要吞掉被调用 Python 进程的退出码。
- 不增加无需求支撑的重试循环。视觉答案缺少关键细节时最多做一次更聚焦的重试，API 失败时停止。

# 密钥与隐私

- API 密钥只允许从环境变量读取，优先级固定为 `ZAI_API_KEY`、`ZHIPUAI_API_KEY`、`BIGMODEL_API_KEY`。
- 不得把密钥写入代码、配置、命令参数、提示词、日志、测试夹具或提交记录，也不得要求用户把密钥粘贴到对话中。
- 只上传完成当前任务必需的图片和问题。新增调试输出时，不得打印 Authorization 请求头、完整请求体或敏感图片内容。
- 真实 API 调用会把图片发送给外部服务；常规验证优先使用离线检查，只有明确需要端到端验证时才使用最小、非敏感样例。

# 验证要求

按改动范围执行最小但充分的检查：

```powershell
# Python 语法
python -m py_compile scripts/analyze_image.py

# Windows 启动链和命令行参数（不读取 API 密钥、不发网络请求）
.\scripts\analyze_image.cmd --help

# PowerShell 脚本语法
$errors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path .\scripts\find_python_and_run.ps1),
    [ref]$null,
    [ref]$errors
)
if ($errors.Count) { $errors | Format-List; exit 1 }
```

修改 Python 数据处理时，还应以临时小文件覆盖本地 Base64 编码、URL 原样保留、缺失文件报错、payload 多图顺序和两种响应内容格式。修改错误处理时，验证失败返回非零退出码且不泄露密钥。只有在环境已安全配置 API 密钥时，才可额外执行一次真实图片的端到端调用。

# 提交规范

- 提交前检查 `git status --short` 和暂存区 diff，只暂存本次范围内的路径。
- 提交标题和正文使用中文，正文说明改了什么以及如何验证，且均不得为空。
- 不添加 `Co-authored-by` 或其他协作者 trailer。

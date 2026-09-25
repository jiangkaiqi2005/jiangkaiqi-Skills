---
name: upgrade-codex-server
description: 在无 sudo 的共用 SSH 服务器上升级 OpenAI Codex CLI（standalone 布局）并排障代理隧道与桌面端识别问题。Use when the user asks to 升级/更新 codex、update Codex CLI on the server、桌面端识别不到新版本、缺少 codex-code-mode-host、终端命令无法启动、codex 断网/代理不通、RemoteForward 隧道问题、或 codex update 假成功。
---

# 升级服务器端 Codex CLI（standalone + SSH 反向隧道）

## 环境地图（动任何东西前先记住这套布局）

- 启动入口：`~/.local/bin/codex` —— 是个 bash 包装脚本：注入代理 env（`http(s)_proxy=127.0.0.1:<端口>`）后 exec 真二进制。**升级时只改里面的端口号，结构不变**
- 实际程序：`~/.codex/packages/standalone/`
  - `releases/<版本>-x86_64-unknown-linux-musl/` 每版本一个目录
  - `current` 软链指向当前版本，升级 = 新建目录 + 切软链
  - 完整目录必须含：`bin/codex`、`bin/codex-code-mode-host`、`codex-path/rg`、`codex-resources/{bwrap,zsh}`、`codex-package.json`
- 代理链路：服务器上的端口是 **Windows 侧 SSH 反向隧道**（`~/.ssh/config` 的 `codex-besci` 条目含 `RemoteForward 17898 127.0.0.1:7897`，7897 是 Windows 上的 Clash 混合端口）。用户用桌面端/SSH 连服务器时隧道自动建立，断开自动消失——**不需要手动开隧道窗口**
- 服务器无 sudo、无真 curl（可能有一个 wget 垫片 `~/.local/bin/curl`）、无 npm；python3 可用
- 本机是多人共用服务器：**代理监听端口会被其他同学的 RemoteForward 抢占**（17897 已被占，现用 17898）。端口被占时换新端口：改 Windows config 的 RemoteForward + 包装脚本两处

## 标准升级流程

1. 体检：`bash ~/.qoder/skills/upgrade-codex-server/scripts/codex_env_check.sh`
   - 解读 `tunnel` 行：chatgpt TLS OK = 健康；baidu OK 而 chatgpt FAIL = 隧道活着但境外路由坏（节点失效或端口被占）
   - `[FAIL]` 项按提示处理后重跑，直到 ALL OK（或先修隧道再升级）
2. 升级：`bash ~/.qoder/skills/upgrade-codex-server/scripts/install_codex_from_npm.sh [版本号]`
   - 缺省装 GitHub 最新版；数据源是官方 npm 平台包 `@openai/codex@<ver>-linux-x64.tgz`——**这是唯一含完整组件（含 code-mode-host）的官方渠道**
   - 脚本自动：下载→按布局装好→切 `current`→杀残留 app-server→清控制 socket
3. 让用户重连桌面端（app-server 会用新二进制重新拉起）。验证：`ps -ef | grep app-server` 看新进程启动时间晚于安装时间

## 排障对照表

| 症状 | 原因 | 处理 |
|---|---|---|
| 桌面端识别旧版本 | 远程 `codex app-server` 是常驻进程，升级后旧进程还活着 | 杀掉 gaohb 名下 `codex.*app-server` 进程 + `rm ~/.codex/app-server-control/app-server-control.sock`，桌面端重连 |
| 所有终端命令无法启动，报缺 `bin/codex-code-mode-host` | 桌面端固定传 `-c features.code_mode_host=true`，而 GitHub release tar.gz 只含主程序 | 用 `install_codex_from_npm.sh` 重装（npm 平台包含全套组件）；不要用 GitHub tar.gz 手动拼装 |
| `codex update` 报 "Update ran successfully" 但版本没变 | 假成功：本机无 curl，内部 `curl \| sh` 静默失败 | 不信它；用体检脚本 + npm 安装器。若隧道健康也可先给 curl 造 wget 垫片再跑 `codex update` |
| 隧道 baidu 通、境外全 FAIL（TLS EOF） | 隧道活着但指向的代理境外路由坏：节点失效，或监听端口被他人会话占用 | 先让用户在 Windows 验证 `curl.exe -x http://127.0.0.1:7897 -I https://chatgpt.com`（403+Cloudflare 头 = 通）。Windows 通、服务器不通 ⇒ 端口被占 ⇒ 换新端口（改 config RemoteForward + 包装脚本，两处都要改），重连后确认无 `Warning: remote port forwarding failed` |
| Windows 端 `ssh -D` 报 `bind ... Permission denied` | Windows 保留端口段（Hyper-V/WSL）或端口已被桌面端自己的连接占用 | `netsh interface ipv4 show excludedportrange protocol=tcp` 查；通常桌面端已自动建好隧道，手动命令可省 |
| wget 走代理报 SSL EOF / urllib SSLEOFError | 不是 wget 的问题，是隧道境外路径坏 | 先修隧道再谈下载 |
| 服务器 DNS 解析不了 github.com | 校园网无直连，一切外网必须走隧道 | 同上，修隧道 |

## 回滚

`ln -sfn ~/.codex/packages/standalone/releases/<旧版本>-x86_64-unknown-linux-musl ~/.codex/packages/standalone/current`，然后同上清理 app-server + socket，桌面端重连。

## 经验教训

- GitHub API 拿最新版本号：`https://api.github.com/repos/openai/codex/releases/latest`，tag 形如 `rust-v0.153.4`
- SOCKS5 隧道连通性测试必须用 python 原始 socket（本机 wget 的 TLS 栈过代理有兼容问题、没有 curl）；SOCKS 应答要 `recv(1024)` 读完再起 TLS，否则假报 WRONG_VERSION_NUMBER
- `chatgpt.com` 用 curl 测返回 403 + `Cf-Mitigated: challenge` 是正常的（Cloudflare 人机验证页），连接本身是通的
- 不要用 GitHub 第三方镜像下载二进制（供应链风险）

## Resources

- `scripts/codex_env_check.sh` — 一键体检：布局/版本/隧道/端口占用/残留 app-server，退出码非 0 表示有问题
- `scripts/install_codex_from_npm.sh` — 从官方 npm 平台包安装/升级到任意版本，自动切软链、清理残留进程

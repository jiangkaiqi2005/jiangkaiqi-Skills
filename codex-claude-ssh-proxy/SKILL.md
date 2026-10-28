---
name: codex-claude-ssh-proxy
description: 用本机常驻 SSH 反向隧道给远端 Codex 和 Claude Desktop 会话提供 HTTP 代理，并排障远端断网、代理端口不监听、网络导致的登录失败及重复 Claude CLI 安装。适用于 Windows 客户端和 Linux 远端。
---

# Codex / Claude 远端常驻代理

目标：远端 Codex 和 Claude 各用一个回环端口走本机 HTTP 代理。转发由本机**一条常驻隧道**持有：登录自启、断线自动重连，与桌面端的 SSH 连接解耦。打开桌面端即可使用，不需要手开终端。

## 转发为何与桌面端连接解耦

把 `RemoteForward` 或带 `-R` 的 `ProxyCommand` 挂在桌面端的 SSH 别名上，代理会随连接起落：

- Claude Desktop 每个远程会话会开多条 SSH：控制、SFTP、每个终端标签各一条，命令行都含 `ClearAllForwardings=yes`。挂在 `ProxyCommand` 上的 `-R` 让每条连接都去抢同一端口，只有一条能绑定成功；它退出后，其余连接不会接管。
- 断网重连时，远端旧 sshd 可能仍占着端口，新连接的 `-R` 因此失败。`ExitOnForwardFailure=no` 让这次失败静默，SSH 照常可用而代理缺失，之后也不会重试。Codex 只有一条连接，同样会这样断掉。
- 共用服务器上，端口还可能被其他用户的转发占用。

常驻隧道设置 `ExitOnForwardFailure=yes`：绑定失败就退出，5 秒后重试，直到端口确实在监听。

## 确定失败层

1. 远端检查端口监听：`ss -ltn | grep -E ':(PORT_A|PORT_B)\b'`。端口不在监听时，问题在隧道，不在工具。
2. 本机检查代理：`curl.exe -x http://127.0.0.1:7897 -sS -o NUL -w "%{http_code}" https://api.anthropic.com`。
3. 确认实际进程读取的端口：在远端读 `/proc/<pid>/environ` 中的 `https_proxy`，进程包括 Codex 的 `codex app-server`，以及 Claude 的 `~/.claude/remote/ccd-cli/*`、`~/.claude/remote/srv/*`。配置文件写的端口不代表进程实际用的端口。
4. 分开检查 SSH 连通、端口监听、HTTP 请求及认证。无令牌访问 API 返回 `401` 只证明链路通；成功的认证接口或实际模型响应才证明认证成功。`Authentication failed` 可能由网络造成。

远端常没有真正的 curl，可用 Python 标准库探测，每个端口各测一次：

```python
import urllib.request, urllib.error
proxy = "http://127.0.0.1:17899"  # 替换为本次要测的端口
opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
for url in ("https://api.anthropic.com/v1/models", "https://api.openai.com/v1/models"):
    try:
        with opener.open(url, timeout=8) as response:
            print(url, response.status)
    except urllib.error.HTTPError as error:
        print(url, "HTTP", error.code)
    except Exception as error:
        print(url, type(error).__name__, str(error)[:160])
```

Windows 侧的进程、日志和计划任务检查，读 [windows-diagnostics.md](references/windows-diagnostics.md)。

## 建立常驻隧道

1. **选端口**：每个工具一个远端端口。在远端用 `ss -ltn` 确认端口空闲；共用服务器上已被别人占用的端口，换一个新的。
2. **整理 SSH 配置**（先备份）：
   - 隧道目标用一个不带转发、不带 `ProxyCommand` 的普通别名，需要免密钥口令登录（`BatchMode=yes` 能直接连上）。
   - 删除 Codex、Claude 别名中的 `RemoteForward`，以及带 `-R` 的 `ProxyCommand`。桌面端连接只承载会话。
3. **部署脚本**：把 [`scripts/ssh-proxy-tunnel.ps1`](scripts/ssh-proxy-tunnel.ps1) 和 [`scripts/install-ssh-proxy-tunnel.ps1`](scripts/install-ssh-proxy-tunnel.ps1) 复制到稳定的本机目录（如 `~/.ssh`）。日志写在脚本旁边，脚本只允许一个实例运行。
4. **注册登录自启**：注册计划任务属于持久化改动，agent 的权限通常会拦下，交给用户执行。给出**一条** PowerShell 命令，路径写 `$env:USERPROFILE`：

   ```powershell
   powershell -NoProfile -File "$env:USERPROFILE\.ssh\install-ssh-proxy-tunnel.ps1" -Target SSH_ALIAS -RemotePorts 17898,17899
   ```

   卸载：`Unregister-ScheduledTask -TaskName ssh-proxy-tunnel -Confirm:$false`，再从备份恢复 SSH 配置。
5. **重连会话**：让用户重连已打开的 Codex 和 Claude 远程会话，旧连接仍按旧配置建立。

完成标志：远端所有选定端口都在监听，日志没有反复出现 `remote port forwarding failed`。反复出现时，说明端口被占：先查远端占用者，是自己残留的 sshd 就结束它，是别人的就换端口。

## 让实际 CLI 读取代理

代理变量只作用于 Codex 和 Claude，不改全局 shell 和其他应用。使用 HTTP(S) 代理，不直接填 SOCKS 端口。

**Claude**：桌面端可能按绝对路径启动 `~/.claude/remote/ccd-cli/<版本>-<构建号>`，绕过 PATH 上的包装脚本。把代理合并到**远端** `~/.claude/settings.json` 的 `env`，保留既有设置：

```json
{
  "env": {
    "http_proxy": "http://127.0.0.1:17899",
    "https_proxy": "http://127.0.0.1:17899",
    "HTTP_PROXY": "http://127.0.0.1:17899",
    "HTTPS_PROXY": "http://127.0.0.1:17899"
  }
}
```

四种大小写都写，避免优先级更高的旧值继续指向别的端口；`NO_PROXY` 保留回环项。

**Codex**：由远端启动入口注入代理变量。改端口后，确认重连后的 `codex app-server` 进程环境里是新端口。Codex 的安装布局和入口脚本见 `upgrade-codex-server` skill。

## 复用一份远端 Claude CLI

以实际进程和日志确认受管 CLI；桌面端不会因为 PATH 上已有 `claude` 就必然复用手工安装。用户要求精简时，将终端入口改为 exec 已验证的受管二进制；升级后可按受管目录的版本排序选择可执行文件。先验证 `claude --version` 和实际请求，再清理确认多余且未运行的手工安装。

备份入口和必要的安装信息，保留账户、会话、插件及当前受管安装。共用二进制不等于共用桌面端令牌；独立终端需要认证时运行 `claude auth login`。

## 完成条件

- 用户重新登录 Windows 后，不开任何终端，计划任务处于运行状态，远端各端口在监听。
- 隧道断开后能自动恢复：结束隧道的 ssh 进程或短暂断网，一分钟内端口重新出现。
- 每个端口的 HTTP 探测都能到达 Anthropic 和 OpenAI，两个工具的实际进程环境指向各自端口。
- Codex 与 Claude 的实际消息，或现有授权下的无工具 CLI 请求成功。必要的令牌只在测试进程内存中使用，输出脱敏。
- 记录实际端口、配置改动、备份位置和结果，区分用户反馈、当前实测及未验证的场景。

维护本服务器或需要具体证据时，读 [besci-case.md](references/besci-case.md)。其中的端口与版本是案例值，不是通用默认。

## 依据

- [OpenSSH `-R`、`ExitOnForwardFailure`、`ServerAliveInterval`](https://man.openbsd.org/ssh_config)
- [Claude 用户级代理配置及变量优先级](https://code.claude.com/docs/en/network-config)
- [Claude Desktop SSH 会话](https://code.claude.com/docs/en/desktop#ssh-sessions)

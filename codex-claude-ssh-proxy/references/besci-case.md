# besci 案例

这是实测记录；维护时重新检查端口、受管版本和当前设置。

## 环境

- Windows 用户目录 `C:\Users\25330`；Microsoft Store 包 `Claude_2.31226.0.0_x64__pzs8sxrjxfjjc`；本机代理为 Clash Verge 混合端口 `127.0.0.1:7897`。
- 远端 `gaohb@10.246.1.4:22`；目录 `/home/students/undergraduate/gaohb`。服务器为多人共用，没有 sudo，也没有真正的 curl。
- SSH 别名：Claude 用 `claude-besci`，Codex 用 `codex-besci`，隧道用不带转发的 `Host 10.246.1.4`。
- 端口：Codex `17898`，Claude `17899`。17897 曾被其他用户占用。
- 桌面端实际启动系统 OpenSSH 和 `claude-ssh-broker.exe`，命令行含 `ClearAllForwardings=yes`。

实际应用数据目录：

```text
C:\Users\25330\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude
```

## 当前配置（2026-10-27 起）

- `~/.ssh/config`：已删除 `codex-besci` 的 `RemoteForward 17898` 和 `claude-besci` 的 `RemoteForward 17899` 及 `ProxyCommand`。备份为 `~/.ssh/config.bak-20261027`。
- 隧道脚本：`~/.ssh/besci-tunnel.ps1`，一条 ssh 同时转发 17898 和 17899，日志为 `~/.ssh/besci-tunnel.log`。由 `~/.ssh/install-besci-tunnel.ps1` 注册为计划任务 `besci-tunnel`，登录时运行。这两个是本 skill 脚本的早期写死版本，行为相同。
- 远端 `~/.claude/settings.json` 的四个代理变量指向 `http://127.0.0.1:17899`，`NO_PROXY` 为 `localhost,127.0.0.1,::1`。
- 远端 `codex app-server` 进程环境中 `https_proxy=http://127.0.0.1:17898`。

## 旧方案为何失效

2026-10-09 起，转发由 `claude-besci` 的 `ProxyCommand ssh.exe -T -o ClearAllForwardings=no -o ExitOnForwardFailure=no -R 127.0.0.1:17899:127.0.0.1:7897 -W %h:%p 10.246.1.4` 承载，Codex 则靠 `codex-besci` 的 `RemoteForward`。

2026-10-27 网络中断后，Codex 和 Claude 都连不上，现场情况：

- 本机经 7897 访问 Anthropic 和 OpenAI 正常。
- 远端 17898 和 17899 都没有监听，而两个工具的进程仍分别指向这两个端口。
- Claude Desktop 一个会话开了 4 条 SSH（控制、SFTP、2 个终端），每条都带一个 `-R 17899` 的 ProxyCommand 子进程；Codex 有 1 条连接。

推断：重连时远端旧会话仍占着端口，`-R` 静默失败；旧会话超时释放端口后，没有连接再去绑定。这一点没有日志直接证实。

## 更早的验收（2026-10-09，旧方案）

- 直连实际 CLI 请求：`Failed to authenticate. API Error: 403 Request not allowed`；同一桌面端令牌经代理后，账户和模型列表返回 200。说明网络问题会被界面误报为认证失败。
- 终端入口 `~/.local/bin/claude` 在 `~/.claude/remote/ccd-cli` 中按版本排序选择可执行文件；当时受管版本 `2.1.293-63201613aae3`，已清理手工安装的 2.1.295 standalone。
- 备份：`~/.claude/backups/remote-config-20261009T083659Z/`，包括旧包装脚本、被删安装的包信息和 SHA-256、切换前的 `settings.before-17899.json`；不含已删除的二进制或 OAuth 令牌。

## 待验证

常驻隧道安装后：远端两个端口是否在监听、每个端口的 HTTP 探测、重新登录后自动启动、断线后自动恢复、两个工具的实际消息。

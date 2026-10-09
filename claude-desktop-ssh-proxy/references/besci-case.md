# besci 案例

这是本次会话的实测记录；维护时重新检查端口、受管版本和当前设置。

## 环境与根因

- Windows 用户目录 `C:\Users\25330`；Microsoft Store 包 `Claude_2.31226.0.0_x64__pzs8sxrjxfjjc`。
- 远端 `gaohb@10.246.1.4:22`；目录 `/home/students/undergraduate/gaohb`。
- 桌面端实际启动系统 OpenSSH 和 `claude-ssh-broker.exe`，不能套用旧版内置 SSH2 客户端的结论。
- 实际 SSH host 是 `claude-besci`，原 SSH 配置已有 `RemoteForward 17899 127.0.0.1:7897`。
- 主连接及 SFTP 命令行均含 `-o ClearAllForwardings=yes`，这是未自动创建 17899 的直接原因。
- 初始 `ProxyCommand=none` 对应原配置中未设置 ProxyCommand；增加该项并重启后，17899 自动出现。

实际应用数据目录：

```text
C:\Users\25330\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude
```

## 已采用配置

保留普通 `Host 10.246.1.4` 的直连、用户名和密钥配置。在 `Host claude-besci` 段增加：

```sshconfig
  ProxyCommand ssh.exe -T -o ClearAllForwardings=no -o ExitOnForwardFailure=no -R 127.0.0.1:17899:127.0.0.1:7897 -W %h:%p 10.246.1.4
```

远端 `~/.claude/settings.json` 四个 HTTP(S) 代理变量使用 `http://127.0.0.1:17899`；回环绕过项为 `localhost,127.0.0.1,::1`。之前的 17898 属于 Codex，只作临时验证，已切换离开。

终端入口 `~/.local/bin/claude` 在 `~/.claude/remote/ccd-cli` 中按版本排序选择可执行文件；当前受管版本 `2.1.293-63201613aae3`。已清理手工安装的 2.1.295 standalone，回收 256,114,434 字节，保留账户、会话和插件。

备份：`~/.claude/backups/remote-config-20261009T083659Z/`，包括旧包装脚本、删除安装的包信息和 SHA-256、切换前的 `settings.before-17899.json`；不含已删除的二进制或 OAuth 令牌。

## 验收与边界

- 早期直连实际 CLI 请求：`Failed to authenticate. API Error: 403 Request not allowed`。
- 早期同一桌面端令牌经 Codex 17898，账户和模型列表返回 200，CLI 返回 `OK`。证明网络能被界面误报为认证失败。
- 用户增加 ProxyCommand、任务结束后重启，并反馈“连上了”。
- 当前远端检查：17899 监听，经该端口无令牌访问 `/v1/models` 返回 401。
- 已把远端用户设置从 17898 切到 17899；清除测试进程继承的代理变量，让实际受管 CLI 只读用户设置，使用桌面端现有令牌发送无工具请求，返回 `OK`、退出码 0。令牌仅在内存中使用。
- 未专门验证连续多次重连、转发拥有者退出后的接管或关闭 Codex 后的全套生命周期；专用端口的请求成功不代表这些场景全部通过。

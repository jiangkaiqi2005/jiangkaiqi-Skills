---
name: claude-desktop-ssh-proxy
description: 配置或排障 Claude Desktop 的 SSH 远端 HTTP 代理、网络导致的登录失败及重复 CLI 安装，使代理随桌面端连接自动建立。适用于 Windows、Microsoft Store 安装和 Linux 远端；不用于 Qoder 或 Codex 自身的网络配置。
---

# Claude Desktop SSH 自动代理

目标：打开 Claude Desktop 并连接远端即可使用本机 HTTP 代理，终端复用桌面端管理的远端 CLI。隧道由桌面端连接带起，验收使用 Claude 自己的代理端口。

## 确定失败层

1. 核对产品、客户端版本、实际 **SSH host** 字段、SSH 配置及远端 CLI 路径。连接显示名与 SSH 别名是两个字段。
2. 分开检查 SSH 连通、代理端口监听、HTTP 请求及认证。无令牌访问 API 返回 `401` 只证明链路通；成功的认证接口或实际模型响应才证明认证成功。
3. 读取当前客户端实际 SSH 参数。需要 Windows 命令、Microsoft Store 数据目录或复制注意事项时，读 [windows-diagnostics.md](references/windows-diagnostics.md)。旧版内置 SSH 客户端的报告不能替代当前进程证据。
4. 对照直连与指定代理的同一请求。`Authentication failed` 可能由网络造成；仅有账户元数据或缺少远端 `.credentials.json` 都不能判定桌面端令牌失效。

远端探测可用 Python 标准库，避免把 curl→wget 垫片当作真正的 curl：

```python
import urllib.request, urllib.error
proxy = "http://127.0.0.1:17899"  # 替换为本次选定端口
opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
try:
    with opener.open("https://api.anthropic.com/v1/models", timeout=8) as response:
        print(response.status)
except urllib.error.HTTPError as error:
    print("HTTP", error.code)
except Exception as error:
    print(type(error).__name__, str(error)[:160])
```

## 自动建立转发

采用实际客户端支持的 SSH 配置。若实际参数含 `ClearAllForwardings=yes`，外层配置中的 `RemoteForward` 会被清除；配置文件的 `ClearAllForwardings no` 无法覆盖命令行参数。

检查客户端是否采用用户设置的 `ProxyCommand`。原配置未设置该项时，命令行出现 `ProxyCommand=none` 不能单独证明客户端不支持它。

可用 ProxyCommand 时，由内部 OpenSSH 同时承载 SSH 通道和反向转发。替换以下模板的地址、用户、密钥、别名和两个端口；已有合适的普通别名时直接复用：

```sshconfig
Host claude-transport
  HostName SERVER_ADDRESS
  User SSH_USER
  IdentityFile ~/.ssh/id_ed25519
  ServerAliveInterval 60
  ServerAliveCountMax 3

Host claude-remote
  HostName SERVER_ADDRESS
  User SSH_USER
  IdentityFile ~/.ssh/id_ed25519
  ProxyCommand ssh.exe -T -o ClearAllForwardings=no -o ExitOnForwardFailure=no -R 127.0.0.1:17899:127.0.0.1:7897 -W %h:%p claude-transport
  ServerAliveInterval 60
  ServerAliveCountMax 3
```

关键约束：

- 内部连接使用普通 transport 别名，避免指回自己造成递归；该别名不带其他代理命令或无关转发。
- Windows 使用 `ssh.exe`；其他平台按实际 OpenSSH 路径调整。保持主机密钥验证。
- `-W` 默认隐含清除转发，内部调用必须显式设置 `ClearAllForwardings=no`。
- Claude 可能同时建立主连接和 SFTP 连接。内部的 `ExitOnForwardFailure=no` 容许后续连接遇到同端口已绑定；代价是转发失败不一定让 SSH 退出，必须实测端口及 HTTP 请求。
- 转发属于成功绑定端口的内部 SSH 连接，另一条连接不会自动接管。若 SSH 仍连接但代理消失，检查连接归属并重新连接；一次成功不代表所有重连场景稳定。

只修改本次 Claude 别名相关项并保留备份。用户有任务正在运行时，保留会话，等任务结束后再完全退出并重开桌面端。若新参数仍明确覆盖 ProxyCommand 且转发未建立，保留可用配置并定位客户端覆盖项，不靠重复重装 CLI 解决。

## 让实际 CLI 读取代理

桌面端可能按绝对路径启动 `~/.claude/remote/ccd-cli/<版本>-<构建号>`，绕过 PATH 包装脚本。把代理合并到**远端** `~/.claude/settings.json` 的 `env`，保留既有设置：

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

同步四种大小写，避免高优先级的旧值继续路由到别的端口；保留或按需求合并 `NO_PROXY` 的回环项。使用 HTTP(S) 代理，不直接填 SOCKS 端口。代理作用于 Claude，保持全局 shell 和其他应用配置不变。

先验证新隧道可用再切换。暂借 Codex 等其他连接的端口时，明确记录依赖，验收前切换到 Claude 自己的端口。

## 复用一份远端 CLI

以实际进程和日志确认受管 CLI；桌面端不会因为 PATH 上已有 `claude` 就必然复用手工安装。用户要求精简时，将终端入口改为 exec 已验证的受管二进制；升级后可按受管目录的版本排序选择可执行文件。先验证 `claude --version` 和实际请求，再清理确认多余且未运行的手工安装。

备份入口和必要的安装信息，保留账户、会话、插件及当前受管安装。共用二进制不等于共用桌面端令牌；独立终端需要认证时运行 `claude auth login`。

## 完成条件

- 正常启动桌面端、选择 SSH 连接后，Claude 专用端口自动出现，没有额外常开终端或手工隧道承载该端口。
- 指定该端口的 HTTP 探测到达 Anthropic，用户设置也指向该端口。
- 桌面端实际消息或现有授权下的无工具 CLI 请求成功。必要的令牌只在测试进程内存中使用，输出脱敏，不保存或复制为终端登录凭据。
- 终端入口指向可运行的受管 CLI；如做去重，交代清理范围与备份位置。
- 记录实际版本、参数、端口和结果，区分用户反馈、当前实测及未验证的重连行为。

维护本服务器或需要具体证据时，读 [besci-case.md](references/besci-case.md)。版本号与端口是案例值，不是通用默认配置。

## 依据

- [OpenSSH `-W`、`-R` 参数](https://man.openbsd.org/ssh)
- [Claude 用户级代理配置及变量优先级](https://code.claude.com/docs/en/network-config)
- [Claude Desktop SSH 会话](https://code.claude.com/docs/en/desktop#ssh-sessions)

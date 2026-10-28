# Windows SSH 诊断

每次给用户**一个**可复制的 PowerShell 代码框。多条命令容易粘成同一行；没有输出时先确认文件是否存在、过滤条件和命令是否原样执行，不把空输出当作成功。

## 读取实际连接

先看运行程序的位置，避免根据旧版路径猜安装形态：

```powershell
Get-Process | Select-Object ProcessName,Path | Select-String -Pattern Claude,Anthropic
```

查 SSH 与 broker 的父进程和路径：

```powershell
Get-CimInstance Win32_Process -Filter "Name='ssh.exe' OR Name='claude-ssh-broker.exe'" | Select-Object Name,ProcessId,ParentProcessId,ExecutablePath | Format-List
```

定位属于 Claude 的父 PID 后，替换下例的 `12345`，读取实际参数；输出前继续检查是否有未被此示例匹配的秘密：

```powershell
Get-CimInstance Win32_Process -Filter "Name='ssh.exe' AND ParentProcessId=12345" | Select-Object -ExpandProperty CommandLine | ForEach-Object { $_ -replace '(?i)(sk-ant-\S+|Bearer\s+\S+|(?:token|password|secret)(?:=|\s+)\S+)', '<REDACTED>' }
```

重点看 `ClearAllForwardings`、`ProxyCommand`、`-F` 配置文件、目标别名，以及主连接和 SFTP 是否用了不同参数。`ssh -G <别名>` 只说明普通 OpenSSH 的有效配置，不包含桌面端另外传入的覆盖参数。

## Microsoft Store 路径

`C:\Program Files\WindowsApps\Claude_<版本>_...\app\Claude.exe` 表示 MSIX 安装。进程报告的普通 Roaming 路径可能是虚拟路径，PowerShell 读取时要用包目录中的实际位置。

只枚举 Packages 目录的一级条目，再按输出定位包：

```powershell
Get-ChildItem -LiteralPath 'C:\Users\USERNAME\AppData\Local\Packages' -Directory | Select-Object Name | Select-String -Pattern Claude,Anthropic
```

常见实际数据根目录：

```text
C:\Users\USERNAME\AppData\Local\Packages\PACKAGE_FAMILY\LocalCache\Roaming\Claude
```

先列出该根目录或 `logs` 的直接子项，确定日志文件名。还可能看到 `ssh_configs.json`、`ssh-remote-server-state.json` 和 `ssh-remembered-passwords.json`；只读需要的字段，避免输出保存的密码或整个账户配置。

找到 `ssh.log` 后短尾读取实际路径。过滤后为空时，核对文件长度、修改时间及原始记录，再决定下一步。

## 常驻隧道状态

查计划任务和隧道进程：

```powershell
Get-ScheduledTask -TaskName ssh-proxy-tunnel | Select-Object TaskName,State; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'ssh.exe' -and $_.CommandLine -match ' -N ' } | Select-Object ProcessId,CommandLine | Format-List
```

读隧道日志末尾，日志在脚本旁边，文件名为任务名加 `.log`：

```powershell
Get-Content "$env:USERPROFILE\.ssh\ssh-proxy-tunnel.log" -Tail 30
```

日志每轮以 `connecting` 开始、以 `ssh exited (N)` 结束。反复出现 `remote port forwarding failed` 表示远端端口被占；反复出现认证或主机密钥错误，表示隧道目标别名不能用 `BatchMode` 登录。

## 复制可靠性

- 用户贴回的命令通常在 PowerShell 中运行。环境变量写 `$env:USERPROFILE`；`$USERPROFILE` 在 PowerShell 中为空，路径会变成 `/.ssh/...`。
- 遇到 `$env:APPDATA` 被复制成 `$env`、`$_.FullName` 变成 `$*.FullName` 或通配符插入多余反斜杠时，用完整路径和 fenced code 重新提供**单条**命令。
- 快速进程查询或一级目录列表通常足够，失去意义的递归搜索就停下。

服务器不能直接访问 Windows 时，先完成远端检查和可审阅的客户端改动，再请用户执行必要的一次性本机步骤，例如注册计划任务。

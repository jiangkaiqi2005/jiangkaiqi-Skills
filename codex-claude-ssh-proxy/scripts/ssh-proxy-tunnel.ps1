# 常驻 SSH 反向隧道：远端 127.0.0.1:<端口> -> 本机 HTTP 代理
# 断线或端口绑定失败时 ssh 退出，5 秒后重连。日志：脚本旁边的 <Name>.log
param(
  [Parameter(Mandatory)] [string]$Target,       # 不带转发的普通 SSH 别名，需能用 BatchMode 登录
  [Parameter(Mandatory)] [string]$RemotePorts,  # 逗号分隔，每个工具一个端口，如 17898,17899
  [string]$LocalProxy = '127.0.0.1:7897',
  [string]$Name = 'ssh-proxy-tunnel'
)

# 只允许一个实例，避免两个隧道互相抢端口
$mutex = New-Object System.Threading.Mutex($false, $Name)
if (-not $mutex.WaitOne(0)) { exit }

$log = Join-Path $PSScriptRoot "$Name.log"
if ((Test-Path $log) -and (Get-Item $log).Length -gt 1MB) { Remove-Item $log }

$forwards = foreach ($port in $RemotePorts -split '[,\s]+') { '-R'; "127.0.0.1:${port}:$LocalProxy" }

while ($true) {
  Add-Content $log "$(Get-Date -Format s) connecting"
  & ssh.exe -N -E $log `
    -o BatchMode=yes -o ExitOnForwardFailure=yes -o ConnectTimeout=15 `
    -o ServerAliveInterval=15 -o ServerAliveCountMax=3 `
    @forwards $Target
  Add-Content $log "$(Get-Date -Format s) ssh exited ($LASTEXITCODE), retry in 5s"
  Start-Sleep 5
}

# 注册计划任务：登录时在后台运行同目录的 ssh-proxy-tunnel.ps1，并立即启动一次
# 卸载：Unregister-ScheduledTask -TaskName <Name> -Confirm:$false
param(
  [Parameter(Mandatory)] [string]$Target,
  [Parameter(Mandatory)] [string]$RemotePorts,
  [string]$LocalProxy = '127.0.0.1:7897',
  [string]$Name = 'ssh-proxy-tunnel'
)

$script = Join-Path $PSScriptRoot 'ssh-proxy-tunnel.ps1'
$ports = ($RemotePorts -split '[,\s]+') -join ','  # 在会话内调用时数组会被拼成空格分隔
$arguments = "-NoProfile -WindowStyle Hidden -File `"$script`" -Target $Target -RemotePorts $ports -LocalProxy $LocalProxy -Name $Name"
$a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$t = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $Name -Action $a -Trigger $t -Settings $s -Description "SSH reverse tunnel: $Target $ports -> $LocalProxy" -Force | Out-Null
Start-ScheduledTask -TaskName $Name
Get-ScheduledTask -TaskName $Name | Select-Object TaskName, State

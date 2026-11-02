# 註冊 Windows 工作排程器：每日 08:30 背景執行 relay_scrape.py（司法院只放行台灣 IP）
#   - 錯過時間（關機/未登入）→ 下次開機登入後自動補跑（StartWhenAvailable）
#   - pythonw 背景執行不跳視窗，輸出寫入 relay.log
#   - 需先在本資料夾建立 .env：ADMIN_TOKEN=xxxx（與 GAS 專案屬性相同）
# 用法：powershell -ExecutionPolicy Bypass -File install_relay_task.ps1 [-Time 08:30] [-Uninstall]
param(
  [string]$Time = "08:30",
  [switch]$Uninstall
)

$TaskName = "法拍資料中繼抓取"
$Dir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Uninstall) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Output "已移除工作排程：$TaskName"
  return
}

$Pyw = (Get-Command pythonw -ErrorAction Stop).Source
if ($Pyw -like "*WindowsApps*") { throw "找到的是 Microsoft Store 捷徑 ($Pyw)，請安裝 python.org 版 Python" }
if (-not (Test-Path (Join-Path $Dir ".env"))) { Write-Warning "尚未建立 .env（ADMIN_TOKEN=...），排程會執行但無法送資料" }

$Action = New-ScheduledTaskAction -Execute $Pyw -Argument "relay_scrape.py --log relay.log" -WorkingDirectory $Dir
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
  -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 10)
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
  -Principal $Principal -Description "司法院擋雲端 IP，改由本機抓法拍資料送 GAS（$Dir\relay_scrape.py）" -Force | Out-Null

Write-Output "已註冊工作排程：$TaskName（每日 $Time，錯過會補跑）"
Write-Output "立即測試：Start-ScheduledTask -TaskName '$TaskName'；結果看 $Dir\relay.log"

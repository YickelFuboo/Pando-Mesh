# PowerShell 启动入口（在项目根目录执行: .\run.ps1）
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
& "$PSScriptRoot\run.bat"
exit $LASTEXITCODE

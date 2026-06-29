param(
    [Parameter(Mandatory = $true)]
    [int]$Port
)
$pids = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
if ($pids) {
    $pids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Write-Host "preLaunch: port $Port freed"
} else {
    Write-Host "preLaunch: port $Port is free"
}

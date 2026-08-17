# Youtube Card Reader - stop script (Windows PowerShell).
$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")

$BackendPort  = if ($env:YCR_BACKEND_PORT)  { $env:YCR_BACKEND_PORT }  else { 8420 }
$FrontendPort = if ($env:YCR_FRONTEND_PORT) { $env:YCR_FRONTEND_PORT } else { 15273 }

function Stop-PortProcess($port) {
  $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  if ($connections) {
    $targetPids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($targetPid in $targetPids) {
      try {
        $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
        if ($proc) {
          Write-Host "✓ stopping :$port (PID $targetPid - $($proc.ProcessName))..."
          Stop-Process -Id $targetPid -Force -ErrorAction Stop
        }
      } catch {
        Write-Warning "Could not stop PID $targetPid listening on :$port - $_"
      }
    }
  } else {
    Write-Host "· nothing listening on :$port"
  }
}

Write-Host "-> Stopping services..."
Stop-PortProcess $BackendPort
Stop-PortProcess $FrontendPort
Write-Host "Done."

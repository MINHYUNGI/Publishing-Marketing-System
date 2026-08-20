param([string]$ProjectDir)
$ErrorActionPreference = "Stop"
if (-not $ProjectDir) { $ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location -LiteralPath $ProjectDir

$log = Join-Path $env:TEMP "MiraeN_Publishing_Marketing_restart.log"
$ready = Join-Path $env:TEMP ("MiraeN_Publishing_Marketing_" + [guid]::NewGuid().ToString("N") + ".ready")

try {
    Remove-Item -LiteralPath $ready -Force -ErrorAction SilentlyContinue
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format s) restart helper started: $ProjectDir"

    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git -and (Test-Path -LiteralPath (Join-Path $ProjectDir ".git"))) {
        $safe = $ProjectDir -replace '\\','/'
        & git config --global --add safe.directory "$safe" 2>$null | Out-Null
        & git -C "$ProjectDir" fetch origin main 2>&1 | Add-Content -LiteralPath $log
        if ($LASTEXITCODE -ne 0) { throw "Git fetch failed." }
        & git -C "$ProjectDir" reset --hard origin/main 2>&1 | Add-Content -LiteralPath $log
        if ($LASTEXITCODE -ne 0) { throw "Git reset failed." }
    }

    $run = Join-Path $ProjectDir "run.ps1"
    if (-not (Test-Path -LiteralPath $run)) { throw "run.ps1 was not found." }

    $env:MIRAEN_READY_FILE = $ready
    $args = '-NoProfile -ExecutionPolicy Bypass -File "' + $run + '"'
    $p = Start-Process -FilePath "powershell.exe" -ArgumentList $args -WorkingDirectory $ProjectDir -PassThru
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format s) new run.ps1 started pid=$($p.Id), ready=$ready"

    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $ready) {
            Add-Content -LiteralPath $log -Value "$(Get-Date -Format s) new app window is ready"
            Remove-Item -LiteralPath $ready -Force -ErrorAction SilentlyContinue
            exit 0
        }
        if ($p.HasExited) {
            throw "The new process exited before its window was ready. Exit code: $($p.ExitCode)"
        }
        Start-Sleep -Milliseconds 400
    }
    throw "The new app window did not become ready within 120 seconds."
}
catch {
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format s) ERROR: $($_.Exception.Message)"
    Remove-Item -LiteralPath $ready -Force -ErrorAction SilentlyContinue
    try {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show(
            "Restart failed. The current app will remain open.`n`n$($_.Exception.Message)`n`nLog: $log",
            "Restart failed"
        ) | Out-Null
    } catch {}
    exit 1
}

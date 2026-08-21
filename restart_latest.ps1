param([string]$ProjectDir)
$ErrorActionPreference = "Stop"
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
$PSDefaultParameterValues['Add-Content:Encoding'] = 'utf8'
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
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & git -C "$ProjectDir" fetch origin main 2>&1 | Add-Content -LiteralPath $log
        $fetchExitCode = $LASTEXITCODE
        if ($fetchExitCode -eq 0) {
            $dirty = (& git -C "$ProjectDir" status --porcelain --untracked-files=no 2>$null)
            if ($dirty) { throw "Uncommitted tracked files exist. Commit or discard them before restarting to the latest version." }
            & git -C "$ProjectDir" merge --ff-only origin/main 2>&1 | Add-Content -LiteralPath $log
            $mergeExitCode = $LASTEXITCODE
        }
        $ErrorActionPreference = $oldPreference
        if ($fetchExitCode -ne 0) { throw "Git fetch failed. Exit code: $fetchExitCode" }
        if ($mergeExitCode -ne 0) { throw "Git fast-forward failed. Exit code: $mergeExitCode" }
    }

    $run = Join-Path $ProjectDir "run.ps1"
    if (-not (Test-Path -LiteralPath $run)) { throw "run.ps1 was not found." }

    $env:MIRAEN_READY_FILE = $ready
    $env:MIRAEN_SKIP_UPDATE = "1"
    $env:MIRAEN_LAUNCHER_REEXEC = "1"
    $args = '-NoProfile -ExecutionPolicy Bypass -File "' + $run + '"'
    $p = Start-Process -FilePath "powershell.exe" -ArgumentList $args -WorkingDirectory $ProjectDir -WindowStyle Hidden -PassThru
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

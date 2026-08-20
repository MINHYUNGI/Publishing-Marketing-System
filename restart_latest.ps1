param([string]$ProjectDir)
$ErrorActionPreference = "Stop"
if (-not $ProjectDir) { $ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
Set-Location -LiteralPath $ProjectDir
$log = Join-Path $env:TEMP "MiraeN_Publishing_Marketing_restart.log"
try {
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format s) restart helper started: $ProjectDir"
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git -and (Test-Path -LiteralPath (Join-Path $ProjectDir ".git"))) {
        $safe = $ProjectDir -replace '\\','/'
        & git config --global --add safe.directory "$safe" 2>$null | Out-Null
        & git -C "$ProjectDir" fetch origin main 2>&1 | Add-Content -LiteralPath $log
        if ($LASTEXITCODE -ne 0) { throw "GitHub 최신 버전 가져오기에 실패했습니다." }
        & git -C "$ProjectDir" reset --hard origin/main 2>&1 | Add-Content -LiteralPath $log
        if ($LASTEXITCODE -ne 0) { throw "GitHub 최신 버전 적용에 실패했습니다." }
    }
    $run = Join-Path $ProjectDir "run.ps1"
    if (-not (Test-Path -LiteralPath $run)) { throw "run.ps1을 찾을 수 없습니다." }
    $env:MIRAEN_UPDATE_REEXEC = "1"
    $args = '-NoProfile -ExecutionPolicy Bypass -File "' + $run + '"'
    $p = Start-Process -FilePath "powershell.exe" -ArgumentList $args -WorkingDirectory $ProjectDir -PassThru
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format s) new run.ps1 started pid=$($p.Id)"
    Start-Sleep -Seconds 2
    if ($p.HasExited -and $p.ExitCode -ne 0) { throw "새 프로그램 실행 프로세스가 즉시 종료되었습니다. 종료코드: $($p.ExitCode)" }
    exit 0
}
catch {
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format s) ERROR: $($_.Exception.Message)"
    try { Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show("최신 버전 재시작에 실패했습니다.`n`n$($_.Exception.Message)`n`n로그: $log", "재시작 실패") | Out-Null } catch {}
    exit 1
}

$ErrorActionPreference = "Stop"

try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location -LiteralPath $ScriptDir

    $Git = Get-Command git -ErrorAction SilentlyContinue
    if ($env:MIRAEN_SKIP_UPDATE -ne "1" -and $Git -and (Test-Path -LiteralPath (Join-Path $ScriptDir ".git"))) {
        $SafeDir = $ScriptDir -replace '\\','/'
        $OldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & git config --global --add safe.directory "$SafeDir" 2>$null | Out-Null
        $BeforeHead = (& git -C "$ScriptDir" rev-parse HEAD 2>$null | Select-Object -First 1)
        if ($BeforeHead) { $BeforeHead = $BeforeHead.Trim() }

        & git -C "$ScriptDir" fetch origin main 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $Dirty = (& git -C "$ScriptDir" status --porcelain --untracked-files=no 2>$null)
            if ($Dirty) {
                Write-Host "미커밋 변경을 보호하기 위해 GitHub 자동 업데이트를 건너뜁니다." -ForegroundColor Yellow
                $MergeExitCode = 0
            } else {
                & git -C "$ScriptDir" merge --ff-only origin/main 2>&1 | Out-Null
                $MergeExitCode = $LASTEXITCODE
            }
            if ($MergeExitCode -eq 0) {
                Write-Host "GitHub 최신 버전 확인 완료." -ForegroundColor DarkGreen
                $AfterHead = (& git -C "$ScriptDir" rev-parse HEAD 2>$null | Select-Object -First 1)
                if ($AfterHead) { $AfterHead = $AfterHead.Trim() }

                # run.ps1 자체가 갱신됐다면 최신 실행기를 한 번만 다시 시작합니다.
                if ($BeforeHead -and $AfterHead -and ($BeforeHead -ne $AfterHead) -and ($env:MIRAEN_LAUNCHER_REEXEC -ne "1")) {
                    Write-Host "실행기가 갱신되어 최신 실행기로 전환합니다." -ForegroundColor DarkGreen
                    $env:MIRAEN_LAUNCHER_REEXEC = "1"
                    $Args = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $ScriptDir "run.ps1") + '"'
                    Start-Process -FilePath "powershell.exe" -ArgumentList $Args -WorkingDirectory $ScriptDir | Out-Null
                    exit 0
                }
            } else {
                Write-Host "GitHub 최신 버전 적용에 실패하여 현재 파일로 실행합니다." -ForegroundColor Yellow
            }
        } else {
            Write-Host "GitHub 최신 버전 확인에 실패하여 현재 파일로 실행합니다." -ForegroundColor Yellow
        }
        $ErrorActionPreference = $OldPreference
    }
    Remove-Item Env:MIRAEN_LAUNCHER_REEXEC -ErrorAction SilentlyContinue
    Remove-Item Env:MIRAEN_SKIP_UPDATE -ErrorAction SilentlyContinue

    $AppHome = Join-Path $env:LOCALAPPDATA "MiraeN_Publishing_Marketing"
    $VenvDir = Join-Path $AppHome "venv_integrated_ai_v1"
    $PythonExe = Join-Path $VenvDir "Scripts\python.exe"
    $Requirements = Join-Path $ScriptDir "requirements.txt"

    if (-not (Test-Path -LiteralPath $PythonExe)) {
        New-Item -ItemType Directory -Force -Path $AppHome | Out-Null
        if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
            throw "Python 3가 설치되어 있지 않습니다."
        }
        & py -3 -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) { throw "Python 가상환경 생성에 실패했습니다." }
        & $PythonExe -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw "pip 업데이트에 실패했습니다." }
        & $PythonExe -m pip install -r $Requirements
        if ($LASTEXITCODE -ne 0) { throw "필수 Python 패키지 설치에 실패했습니다." }
    }

    Write-Host "출판 마케팅 운영 시스템을 시작합니다..." -ForegroundColor Cyan
    & $PythonExe -m app.main
    if ($LASTEXITCODE -ne 0) {
        throw "출판 마케팅 운영 시스템 실행 실패. 종료 코드: $LASTEXITCODE"
    }
}
catch {
    Write-Host ""
    Write-Host "실행 중 오류가 발생했습니다." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "이 창을 닫지 말고 오류 내용을 캡처해 주세요." -ForegroundColor Yellow
    Read-Host "Enter 키를 누르면 종료합니다"
}

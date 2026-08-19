$ErrorActionPreference = "Stop"

# Always use the directory containing this script as the application root.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ScriptDir

# GitHub 최신본 자동 반영
# 네트워크 드라이브의 ownership 판정과 PowerShell native-command 예외를 별도로 처리합니다.
$Git = Get-Command git -ErrorAction SilentlyContinue
if ($Git -and (Test-Path -LiteralPath (Join-Path $ScriptDir ".git"))) {
    $SafeDir = $ScriptDir -replace '\\','/'
    $OldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    & git config --global --add safe.directory "$SafeDir" 2>$null | Out-Null
    $FetchOutput = & git -C "$ScriptDir" fetch origin main 2>&1
    $FetchCode = $LASTEXITCODE

    if ($FetchCode -eq 0) {
        $ResetOutput = & git -C "$ScriptDir" reset --hard origin/main 2>&1
        $ResetCode = $LASTEXITCODE
        if ($ResetCode -eq 0) {
            Write-Host "GitHub 최신 버전 확인 완료." -ForegroundColor DarkGreen
        } else {
            Write-Host "GitHub 업데이트 적용에 실패하여 현재 버전으로 실행합니다." -ForegroundColor Yellow
            if ($ResetOutput) { Write-Host ($ResetOutput | Out-String) -ForegroundColor DarkYellow }
        }
    } else {
        Write-Host "GitHub 최신 버전 확인에 실패하여 현재 버전으로 실행합니다." -ForegroundColor Yellow
        if ($FetchOutput) { Write-Host ($FetchOutput | Out-String) -ForegroundColor DarkYellow }
    }
    $ErrorActionPreference = $OldPreference
}

$AppHome = Join-Path $env:LOCALAPPDATA "MiraeN_Publishing_Marketing"
$VenvDir = Join-Path $AppHome "venv_integrated_ai_v1"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$Requirements = Join-Path $ScriptDir "requirements.txt"

if (-not (Test-Path -LiteralPath $PythonExe)) {
    New-Item -ItemType Directory -Force -Path $AppHome | Out-Null
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $PyLauncher) { throw "Python 3가 설치되어 있지 않거나 py 명령을 찾을 수 없습니다." }
    & py -3 -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "Python 가상환경 생성에 실패했습니다." }
    & $PythonExe -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip 업데이트에 실패했습니다." }
    & $PythonExe -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw "필수 Python 패키지 설치에 실패했습니다." }
}

# 화면 패치를 순서대로 적용합니다.
$UiPatches = @(
    (Join-Path $ScriptDir "app\ui_runtime_patch.py"),
    (Join-Path $ScriptDir "app\admin_runtime_patch.py")
)
foreach ($UiPatch in $UiPatches) {
    if (Test-Path -LiteralPath $UiPatch) {
        & $PythonExe $UiPatch
        if ($LASTEXITCODE -ne 0) { throw "UI 패치 적용에 실패했습니다: $UiPatch" }
    }
}

& $PythonExe -m app.main
if ($LASTEXITCODE -ne 0) {
    throw "출판 마케팅 운영 시스템 실행에 실패했습니다. 종료 코드: $LASTEXITCODE"
}

$ErrorActionPreference = "Stop"

# Always use the directory containing this script as the application root.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ScriptDir

# GitHub 최신본 자동 반영. 네트워크 또는 Git 오류가 있어도 기존 로컬 버전으로 실행합니다.
try {
    $Git = Get-Command git -ErrorAction SilentlyContinue
    if ($Git -and (Test-Path -LiteralPath (Join-Path $ScriptDir ".git"))) {
        & git fetch origin main 2>$null
        if ($LASTEXITCODE -eq 0) {
            & git reset --hard origin/main 2>$null | Out-Null
        }
    }
} catch {
    Write-Host "GitHub 업데이트를 건너뛰고 현재 버전으로 실행합니다." -ForegroundColor Yellow
}

$AppHome = Join-Path $env:LOCALAPPDATA "MiraeN_Publishing_Marketing"
$VenvDir = Join-Path $AppHome "venv_integrated_ai_v1"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$Requirements = Join-Path $ScriptDir "requirements.txt"

if (-not (Test-Path -LiteralPath $PythonExe)) {
    New-Item -ItemType Directory -Force -Path $AppHome | Out-Null

    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $PyLauncher) {
        throw "Python 3가 설치되어 있지 않거나 py 명령을 찾을 수 없습니다."
    }

    & py -3 -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "Python 가상환경 생성에 실패했습니다." }

    & $PythonExe -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip 업데이트에 실패했습니다." }

    & $PythonExe -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw "필수 Python 패키지 설치에 실패했습니다." }
}

# 긴 UI 원본 전체를 덮어쓰지 않고 필요한 화면 변경만 안전하게 적용합니다.
$UiPatch = Join-Path $ScriptDir "app\ui_runtime_patch.py"
if (Test-Path -LiteralPath $UiPatch) {
    & $PythonExe $UiPatch
    if ($LASTEXITCODE -ne 0) { throw "UI 패치 적용에 실패했습니다." }
}

& $PythonExe -m app.main
if ($LASTEXITCODE -ne 0) {
    throw "출판 마케팅 운영 시스템 실행에 실패했습니다. 종료 코드: $LASTEXITCODE"
}

$ErrorActionPreference = "Stop"

# Always use the directory containing this script as the application root.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ScriptDir

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

& $PythonExe -m app.main
if ($LASTEXITCODE -ne 0) {
    throw "출판 마케팅 운영 시스템 실행에 실패했습니다. 종료 코드: $LASTEXITCODE"
}

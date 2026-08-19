@echo off
chcp 65001 >nul
setlocal
set "ROOT=Y:\출판사업본부\06. 출판 마케팅 운영 시스템"
set "REPO=https://github.com/MINHYUNGI/Publishing-Marketing-System.git"

if not exist "%ROOT%" mkdir "%ROOT%"
pushd "%ROOT%" || (
  echo [오류] 운영 폴더에 접근할 수 없습니다.
  pause
  exit /b 1
)

where git >nul 2>&1 || (
  echo [오류] Git이 설치되어 있지 않거나 PATH에 등록되어 있지 않습니다.
  echo Git for Windows 설치 후 다시 실행해 주세요.
  pause
  exit /b 1
)

if not exist ".git" (
  echo [초기 연결] GitHub 저장소를 연결합니다...
  git init
  git remote add origin "%REPO%"
) else (
  git remote get-url origin >nul 2>&1
  if errorlevel 1 (
    git remote add origin "%REPO%"
  ) else (
    git remote set-url origin "%REPO%"
  )
)

echo [업데이트 확인] 최신 버전을 확인합니다...
git fetch origin main
if errorlevel 1 (
  echo [경고] GitHub 업데이트를 받지 못했습니다.
  echo 기존 로컬 버전으로 실행을 계속합니다.
) else (
  git reset --hard origin/main
)

echo [실행] 출판 마케팅 운영 시스템을 시작합니다...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\run.ps1"

popd
endlocal

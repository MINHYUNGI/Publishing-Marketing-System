$ErrorActionPreference = "Stop"

try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location -LiteralPath $ScriptDir

    $Git = Get-Command git -ErrorAction SilentlyContinue
    if ($Git -and (Test-Path -LiteralPath (Join-Path $ScriptDir ".git"))) {
        $SafeDir = $ScriptDir -replace '\\','/'
        $OldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & git config --global --add safe.directory "$SafeDir" 2>$null | Out-Null
        & git -C "$ScriptDir" fetch origin main 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            & git -C "$ScriptDir" reset --hard origin/main 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) { Write-Host "GitHub 최신 버전 확인 완료." -ForegroundColor DarkGreen }
            else { Write-Host "GitHub 최신 버전 적용에 실패하여 현재 파일로 실행합니다." -ForegroundColor Yellow }
        } else { Write-Host "GitHub 최신 버전 확인에 실패하여 현재 파일로 실행합니다." -ForegroundColor Yellow }
        $ErrorActionPreference = $OldPreference
    }

    $AppHome = Join-Path $env:LOCALAPPDATA "MiraeN_Publishing_Marketing"
    $VenvDir = Join-Path $AppHome "venv_integrated_ai_v1"
    $PythonExe = Join-Path $VenvDir "Scripts\python.exe"
    $Requirements = Join-Path $ScriptDir "requirements.txt"

    if (-not (Test-Path -LiteralPath $PythonExe)) {
        New-Item -ItemType Directory -Force -Path $AppHome | Out-Null
        if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python 3가 설치되어 있지 않습니다." }
        & py -3 -m venv $VenvDir
        & $PythonExe -m pip install --upgrade pip
        & $PythonExe -m pip install -r $Requirements
    }

    $UiPatches = @(
        (Join-Path $ScriptDir "app\ui_runtime_patch.py"),(Join-Path $ScriptDir "app\admin_runtime_patch.py"),(Join-Path $ScriptDir "app\erp_daily_ui_patch.py"),(Join-Path $ScriptDir "app\performance_period_patch.py"),(Join-Path $ScriptDir "app\performance_timeline_ui_patch.py"),(Join-Path $ScriptDir "app\performance_timeline_group_patch.py"),(Join-Path $ScriptDir "app\performance_timeline_all_activities_patch.py"),(Join-Path $ScriptDir "app\global_font_scale_patch.py"),(Join-Path $ScriptDir "app\performance_font_scale_patch.py"),(Join-Path $ScriptDir "app\performance_header_layout_patch.py"),(Join-Path $ScriptDir "app\execution_ui_patch.py"),(Join-Path $ScriptDir "app\execution_ui_activation_patch.py"),(Join-Path $ScriptDir "app\execution_edit_button_font_patch.py"),(Join-Path $ScriptDir "app\execution_layout_drag_patch.py"),(Join-Path $ScriptDir "app\execution_reorder_ui_patch.py"),(Join-Path $ScriptDir "app\execution_drag_reorder_patch.py"),(Join-Path $ScriptDir "app\performance_timeline_execution_order_patch.py"),(Join-Path $ScriptDir "app\performance_timeline_resize_patch.py"),(Join-Path $ScriptDir "app\execution_text_hierarchy_patch.py"),(Join-Path $ScriptDir "app\sns_content_link_ui_patch.py"),(Join-Path $ScriptDir "app\execution_font_scale_live_patch.py"),(Join-Path $ScriptDir "app\execution_compact_row_patch.py"),(Join-Path $ScriptDir "app\execution_resizable_and_link_row_patch.py"),(Join-Path $ScriptDir "app\sns_link_save_fix_patch.py"),(Join-Path $ScriptDir "app\performance_stability_cleanup_patch.py"),(Join-Path $ScriptDir "app\sns_content_display_patch.py"),(Join-Path $ScriptDir "app\sns_content_readability_patch.py"),(Join-Path $ScriptDir "app\sns_remove_share_patch.py"),(Join-Path $ScriptDir "app\sns_youtube_only_metrics_patch.py"),(Join-Path $ScriptDir "app\sns_content_final_ui_patch.py"),(Join-Path $ScriptDir "app\restart_ui_patch.py")
    )

    foreach ($p in $UiPatches) {
        if (Test-Path -LiteralPath $p) {
            & $PythonExe $p
            if ($LASTEXITCODE -ne 0) { throw "UI 패치 적용 실패: $p" }
        }
    }

    Write-Host "출판 마케팅 운영 시스템을 시작합니다..." -ForegroundColor Cyan
    & $PythonExe -m app.main
    if ($LASTEXITCODE -ne 0) { throw "출판 마케팅 운영 시스템 실행 실패. 종료 코드: $LASTEXITCODE" }
}
catch {
    Write-Host ""; Write-Host "실행 중 오류가 발생했습니다." -ForegroundColor Red; Write-Host $_.Exception.Message -ForegroundColor Red; Write-Host ""; Write-Host "이 창을 닫지 말고 오류 내용을 캡처해 주세요." -ForegroundColor Yellow; Read-Host "Enter 키를 누르면 종료합니다"
}

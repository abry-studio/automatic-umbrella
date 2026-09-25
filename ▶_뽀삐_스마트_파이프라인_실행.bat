@echo off
chcp 65001 > nul
title [뽀삐] 현장 스마트 데이터 파이프라인 & 시트 뷰어
cd /d "%~dp0"

echo ==============================================================================
echo  🐕 뽀삐 현장 스마트 데이터 파이프라인 & 시트 뷰어 가동 중...
echo ==============================================================================
echo.
echo [1] 서버 가동 상태 확인 중...

REM 이미 8500 포트에서 서버가 실행 중인지 확인
netstat -ano | findstr :8500 > nul
if %errorlevel% equ 0 (
    echo [OK] 파이프라인 서버가 이미 백그라운드에서 실행 중입니다.
    goto launch_browser
)

echo [*] 파이프라인 백엔드 서버를 시작합니다...
REM 백그라운드 독립 창으로 실행하여 배치 파일 종료 시에도 서버가 꺼지지 않도록 설정
start "뽀삐_파이프라인_서버" /min python "pipeline_server.py"

echo [*] 서버 초기화 및 포트 준비 대기 중...
set /a retry=0

:check_loop
timeout /t 1 > nul
netstat -ano | findstr :8500 > nul
if %errorlevel% equ 0 (
    echo [OK] 서버가 정상적으로 준비되었습니다!
    goto launch_browser
)

set /a retry+=1
if %retry% lss 8 (
    echo    ... 서버 가동 대기 중 (%retry%/8)
    goto check_loop
)

:launch_browser
echo.
echo [2] 웹 브라우저를 실행합니다 (http://127.0.0.1:8500)
start http://127.0.0.1:8500

echo.
echo ==============================================================================
echo  ★ 가동 완료! 웹 화면에서 사진/엑셀을 넣거나 탭을 눌러 시트를 확인하세요.
echo ==============================================================================
timeout /t 2 > nul
exit

@echo off
REM Installs the "오늘 뭐 먹지?" lunch recommender to your local machine and opens it.
REM
REM Usage:
REM   curl -fsSL https://raw.githubusercontent.com/jeongjjeong/lunch-recommender/main/install.cmd -o install.cmd && install.cmd && del install.cmd

setlocal

set "BRANCH=main"
set "INSTALL_DIR=%USERPROFILE%\lunch-recommender"
set "TARGET_FILE=%INSTALL_DIR%\lunch_recommender.html"
set "REPO_RAW_URL=https://raw.githubusercontent.com/jeongjjeong/lunch-recommender/%BRANCH%/lunch_recommender.html"

echo Installing lunch recommender to %INSTALL_DIR% ...

if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
)

curl -fsSL "%REPO_RAW_URL%" -o "%TARGET_FILE%"
if errorlevel 1 (
    echo Failed to download lunch_recommender.html
    exit /b 1
)

echo Downloaded to %TARGET_FILE%
echo Opening in your default browser...

start "" "%TARGET_FILE%"

echo Done! Enjoy your lunch.

endlocal

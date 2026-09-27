@echo off
setlocal
cd /d "%~dp0"
echo Orlando MX v009 - geometry candidate build
echo Requires Python 3.12 or newer and internet for dependencies and official tools.
where py >nul 2>nul
if errorlevel 1 goto :usepython
set "V009_PY=py -3"
goto :setup
:usepython
where python >nul 2>nul
if errorlevel 1 goto :missing
set "V009_PY=python"
:setup
%V009_PY% -c "import sys; assert sys.version_info >= (3,12), 'Python 3.12 or newer is required'"
if errorlevel 1 goto :failed
if exist .venv-v009\Scripts\python.exe goto :install
%V009_PY% -m venv .venv-v009
if errorlevel 1 goto :failed
:install
.venv-v009\Scripts\python.exe -m pip install -r requirements-v009.txt
if errorlevel 1 goto :failed
.venv-v009\Scripts\python.exe TOOLS\build_v009.py
if errorlevel 1 goto :failed
echo.
echo COMPLETE: 12_RELEASE\OrlandoMX_2026_v009.pkz
echo Static and native QA passed. In-game ride testing remains required.
pause
exit /b 0
:missing
echo ERROR: Install Python 3.12 or newer, then run this file again.
goto :failed
:failed
echo.
echo BUILD FAILED. Keep the console output and DOCUMENTATION logs.
echo Do not install an older or partial v009 PKZ from a failed build.
pause
exit /b 1

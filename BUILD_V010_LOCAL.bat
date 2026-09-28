@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
py -3 -m venv .venv-v010
if errorlevel 1 exit /b 1
.venv-v010\Scripts\python.exe -m pip install -r requirements-v009.txt
if errorlevel 1 exit /b 1
.venv-v010\Scripts\python.exe TOOLS\build_v010.py
if errorlevel 1 exit /b 1
echo Complete: 12_RELEASE\OrlandoMX_2026_v010.pkz
pause

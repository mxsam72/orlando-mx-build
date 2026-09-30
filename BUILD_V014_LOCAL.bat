@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python -m pip install -r requirements-v009.txt
if errorlevel 1 exit /b 1
python TOOLS\build_v014.py
if errorlevel 1 exit /b 1
echo Built separate 12_RELEASE\OrlandoMX_2026_v014.pkz
endlocal

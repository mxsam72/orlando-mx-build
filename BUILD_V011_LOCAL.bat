@echo off
set PYTHONUTF8=1
py -3 -m pip install -r requirements-v009.txt
if errorlevel 1 exit /b 1
py -3 TOOLS\build_v011.py

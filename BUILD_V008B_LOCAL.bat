@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo Orlando MX v008b - dirt color and tree correction
echo ============================================================
echo.
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PYCMD=py -3"
) else (
  where python >nul 2>nul
  if not %ERRORLEVEL%==0 (
    echo ERROR: Python 3 was not found.
    pause
    exit /b 1
  )
  set "PYCMD=python"
)

%PYCMD% -c "from PIL import Image" >nul 2>nul
if errorlevel 1 (
  echo Pillow is required for the texture correction. Installing Pillow...
  %PYCMD% -m pip install pillow
  if errorlevel 1 goto :failed
)

echo [1/5] Restoring exact v007 native inputs...
%PYCMD% TOOLS\unpack_inputs.py
if errorlevel 1 goto :failed

echo.
echo [2/5] Re-applying verified v008 visual overlay...
%PYCMD% TOOLS\prepare_v008_local.py
if errorlevel 1 goto :failed

echo.
echo [3/5] Correcting dirt color and simplifying tree wall...
%PYCMD% TOOLS\v008b_visual_fix.py
if errorlevel 1 goto :failed

echo.
echo [4/5] Preparing separate v008b release folder...
%PYCMD% TOOLS\prepare_v008b_release.py
if errorlevel 1 goto :failed

echo.
echo [5/5] Compiling v008b with official PiBoSo Windows tools...
%PYCMD% TOOLS\build_windows_v008b.py
if errorlevel 1 goto :failed

echo.
echo ============================================================
echo BUILD COMPLETE
echo Output: 12_RELEASE\OrlandoMX_2026_v008b.pkz
echo ============================================================
pause
exit /b 0

:failed
echo.
echo ============================================================
echo BUILD FAILED - do not trust a partial v008b package.
echo Send ChatGPT a screenshot plus DOCUMENTATION logs.
echo ============================================================
pause
exit /b 1

@echo off
setlocal
cd /d "%~dp0"

set "PLUGIN_PYTHON="

rem Prefer the same local UI environments used by the RS_allin launcher.
call :try_python "%~dp0.venv\Scripts\python.exe"
call :try_python "%~dp0venv\Scripts\python.exe"
call :try_python "%~dp0env\Scripts\python.exe"
call :try_python "%~dp0..\.venv\Scripts\python.exe"
call :try_python "%~dp0..\venv\Scripts\python.exe"
call :try_python "%~dp0..\env\Scripts\python.exe"

rem PATH can contain multiple Python installations. Check all of them.
for /f "delims=" %%P in ('where python.exe 2^>nul') do call :try_python "%%P"
for /f "delims=" %%P in ('where py.exe 2^>nul') do call :try_python "%%P"

if not defined PLUGIN_PYTHON (
    echo [ERROR] No Python environment with PySide6 was found.
    echo The main program and this launcher may be using different Python installations.
    echo Put the UI environment in .venv, venv, or env at the repository root and retry.
    echo runtime\env\samroad_env is the algorithm environment and does not need PySide6.
    pause
    exit /b 1
)

echo UI Python: %PLUGIN_PYTHON%
if /i "%ROAD_CHANGE_PLUGIN_CHECK_ONLY%"=="1" exit /b 0

"%PLUGIN_PYTHON%" "%~dp0standalone.py"
set "PLUGIN_EXIT_CODE=%ERRORLEVEL%"
if not "%PLUGIN_EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] The plugin exited with code %PLUGIN_EXIT_CODE%.
    pause
)
exit /b %PLUGIN_EXIT_CODE%

:try_python
if defined PLUGIN_PYTHON exit /b 0
if not exist "%~1" exit /b 0
"%~1" -c "import PySide6" >nul 2>nul
if not errorlevel 1 set "PLUGIN_PYTHON=%~1"
exit /b 0

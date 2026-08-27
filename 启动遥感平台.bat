@echo off
setlocal
cd /d "%~dp0"

rem Prefer a project-local Python installation when one exists.
set "RSALLIN_PYTHONW="
if exist "%~dp0.venv\Scripts\pythonw.exe" set "RSALLIN_PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
if not defined RSALLIN_PYTHONW if exist "%~dp0venv\Scripts\pythonw.exe" set "RSALLIN_PYTHONW=%~dp0venv\Scripts\pythonw.exe"
if not defined RSALLIN_PYTHONW if exist "%~dp0env\Scripts\pythonw.exe" set "RSALLIN_PYTHONW=%~dp0env\Scripts\pythonw.exe"

if not defined RSALLIN_PYTHONW for /f "delims=" %%P in ('where pythonw.exe 2^>nul') do if not defined RSALLIN_PYTHONW set "RSALLIN_PYTHONW=%%P"
if defined RSALLIN_PYTHONW (
    start "" /b "%RSALLIN_PYTHONW%" "%~dp0main.py"
    exit /b 0
)

rem Fall back to the Python launcher or python.exe if pythonw is unavailable.
if exist "%~dp0.venv\Scripts\python.exe" set "RSALLIN_PYTHON=%~dp0.venv\Scripts\python.exe"
if not defined RSALLIN_PYTHON if exist "%~dp0venv\Scripts\python.exe" set "RSALLIN_PYTHON=%~dp0venv\Scripts\python.exe"
if not defined RSALLIN_PYTHON if exist "%~dp0env\Scripts\python.exe" set "RSALLIN_PYTHON=%~dp0env\Scripts\python.exe"
if not defined RSALLIN_PYTHON for /f "delims=" %%P in ('where py.exe 2^>nul') do if not defined RSALLIN_PYTHON set "RSALLIN_PYTHON=%%P"
if not defined RSALLIN_PYTHON for /f "delims=" %%P in ('where python.exe 2^>nul') do if not defined RSALLIN_PYTHON set "RSALLIN_PYTHON=%%P"

if not defined RSALLIN_PYTHON (
    echo 未找到 Python。请先安装 Python 3 并确保 python 或 py 已加入 PATH。
    pause
    exit /b 1
)

"%RSALLIN_PYTHON%" "%~dp0main.py"
if errorlevel 1 (
    echo 平台启动失败，请检查 requirements.txt 中的依赖是否已安装。
    pause
    exit /b 1
)

endlocal

@echo off
rem RectChr GUI launcher for Windows
setlocal
set "DIR=%~dp0"

if exist "%DIR%dist\RectChrGUI\RectChrGUI.exe" (
    start "" "%DIR%dist\RectChrGUI\RectChrGUI.exe"
    exit /b
)
if exist "%DIR%RectChrGUI\RectChrGUI.exe" (
    start "" "%DIR%RectChrGUI\RectChrGUI.exe"
    exit /b
)

rem ---- find python (prefer windowless pythonw) ----
where pythonw >nul 2>nul && goto havepyw
where python  >nul 2>nul && goto havepy
echo Python 3.9+ is required.
echo Install from https://www.python.org/downloads/ (tick "Add python.exe to PATH"),
echo then run:  pip install PySide6
pause
exit /b 1

:havepyw
set "PY=pythonw"
goto checkpyside

:havepy
set "PY=python"

:checkpyside
%PY% -c "import PySide6" >nul 2>nul
if %errorlevel%==0 goto launch

echo ============================================================
echo  First launch: installing PySide6 (about 1-2 minutes)...
echo  Please wait, this runs only once.
echo ============================================================
%PY% -m pip install PySide6
%PY% -c "import PySide6" >nul 2>nul
if %errorlevel%==0 goto launch

echo Default index failed, retrying with --user ...
%PY% -m pip install --user PySide6
%PY% -c "import PySide6" >nul 2>nul
if %errorlevel%==0 goto launch

echo Retrying with the Tsinghua mirror ...
%PY% -m pip install --user -i https://pypi.tuna.tsinghua.edu.cn/simple PySide6
%PY% -c "import PySide6" >nul 2>nul
if %errorlevel%==0 goto launch

echo.
echo [RectChr] Automatic PySide6 installation failed.
echo Please install it manually, then run RectChrGUI.bat again:
echo.
echo     %PY% -m pip install PySide6
echo.
pause
exit /b 1

:launch
start "" %PY% "%DIR%gui\main.py"
exit /b

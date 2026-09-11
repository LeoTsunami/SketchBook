@echo off
REM One-command Windows packager.
REM Example:
REM   scripts\package_release.bat --bump patch --notes "Beta for testers"
setlocal
set ROOT=%~dp0..
set PYTHON=%ROOT%\.venv\Scripts\python.exe
if not exist "%PYTHON%" set PYTHON=python
"%PYTHON%" "%ROOT%\scripts\package_release.py" %*
exit /b %ERRORLEVEL%

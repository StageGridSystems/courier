@echo off
setlocal
cd /d "%~dp0"

if not exist .venv (
  py -3.11 -m venv .venv 2>nul || py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
set PYTHONPATH=%CD%\src;%PYTHONPATH%
python -m courier %*
endlocal

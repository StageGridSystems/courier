@echo off
setlocal
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat
python -m pip install -e ".[build]"
pyinstaller packaging\courier.spec --noconfirm --distpath dist\windows --workpath build\windows
echo Built dist\windows\Courier.exe
endlocal

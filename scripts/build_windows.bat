@echo off
setlocal
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat
python -m pip install -e ".[build]" Pillow
set QT_QPA_PLATFORM=offscreen
python scripts\generate_app_icon.py
pyinstaller packaging\courier.spec --noconfirm --distpath dist\windows --workpath build\windows
echo Built dist\windows\Courier\Courier.exe
echo.
echo To build the Setup.exe (requires Inno Setup 6):
echo   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DMyAppVersion=0.1.0 packaging\windows\courier.iss
echo Output: dist\windows\Courier-Setup-^<version^>.exe
endlocal

@echo off
REM XPS Figure Studio - Windows baslatici
REM Ilk calistirmada sanal ortam kurar ve paketleri yukler.

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [HATA] Python bulunamadi. https://www.python.org/downloads/ adresinden
    echo Python 3.10+ kurun ve kurulum sirasinda "Add Python to PATH" secenegini isaretleyin.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Sanal ortam olusturuluyor...
    python -m venv .venv
    if errorlevel 1 (
        echo [HATA] Sanal ortam olusturulamadi.
        pause
        exit /b 1
    )
    echo Paketler yukleniyor, bu ilk seferde birkac dakika surebilir...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [HATA] Paketler yuklenemedi.
        pause
        exit /b 1
    )
)

echo XPS Figure Studio baslatiliyor... Tarayici otomatik acilacak.
".venv\Scripts\python.exe" -m streamlit run app.py
pause

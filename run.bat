@echo off
REM ---------------------------------------------------------------------------
REM  XPS Figure Studio - Windows baslatici (konsol penceresi gorunur)
REM  Ilk calistirmada sanal ortam kurar ve paketleri yukler.
REM
REM  Masaustu kisayolu icin kisayol_olustur.bat dosyasini kullanin; o kisayol
REM  pythonw.exe ile run.py'yi cagirir ve bu siyah pencere hic acilmaz.
REM ---------------------------------------------------------------------------

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [HATA] Python bulunamadi. https://www.python.org/downloads/ adresinden
    echo Python 3.10+ kurun ve kurulum sirasinda "Add python.exe to PATH" secenegini isaretleyin.
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
echo Kapatmak icin bu pencereyi kapatin veya Ctrl+C tuslayin.
".venv\Scripts\python.exe" run.py
pause

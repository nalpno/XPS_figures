@echo off
REM ---------------------------------------------------------------------------
REM  Masaustune "XPS Figure Studio" kisayolu olusturur.
REM  Kisayol pythonw.exe ile run.py'yi calistirir - siyah konsol penceresi cikmaz.
REM  Bu dosyaya bir kez cift tiklamak yeterlidir.
REM ---------------------------------------------------------------------------

setlocal
set "XPSDIR=%~dp0"

where pythonw.exe >nul 2>nul
if errorlevel 1 (
    echo [HATA] pythonw.exe bulunamadi.
    echo.
    echo Python kurulu degil ya da PATH'e eklenmemis.
    echo https://www.python.org/downloads/ adresinden kurarken
    echo "Add python.exe to PATH" kutusunu isaretleyin.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$dir = $env:XPSDIR.TrimEnd('\');" ^
  "$py = (Get-Command pythonw.exe).Source;" ^
  "$venv = Join-Path $dir '.venv\Scripts\pythonw.exe';" ^
  "if (Test-Path $venv) { $py = $venv }" ^
  "$link = Join-Path ([Environment]::GetFolderPath('Desktop')) 'XPS Figure Studio.lnk';" ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($link);" ^
  "$s.TargetPath = $py;" ^
  "$s.Arguments = '\"' + (Join-Path $dir 'run.py') + '\"';" ^
  "$s.WorkingDirectory = $dir;" ^
  "$s.Description = 'XPS Figure Studio';" ^
  "$icon = Join-Path $dir 'assets\xps.ico';" ^
  "if (Test-Path $icon) { $s.IconLocation = $icon }" ^
  "$s.Save();" ^
  "Write-Host '';" ^
  "Write-Host ('Kisayol olusturuldu: ' + $link);" ^
  "Write-Host ('Hedef: ' + $s.TargetPath + ' ' + $s.Arguments)"

if errorlevel 1 (
    echo [HATA] Kisayol olusturulamadi.
    pause
    exit /b 1
)

echo.
echo Masaustundeki "XPS Figure Studio" simgesine cift tiklayarak calistirabilirsiniz.
echo.
pause

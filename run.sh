#!/usr/bin/env bash
# XPS Figure Studio - macOS / Linux başlatıcı
# İlk çalıştırmada sanal ortam kurar ve paketleri yükler.
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[HATA] python3 bulunamadı. Python 3.10+ kurun."
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "Sanal ortam oluşturuluyor..."
    python3 -m venv .venv
    echo "Paketler yükleniyor, bu ilk seferde birkaç dakika sürebilir..."
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements.txt
fi

echo "XPS Figure Studio başlatılıyor... Tarayıcı otomatik açılacak."
exec .venv/bin/python -m streamlit run app.py

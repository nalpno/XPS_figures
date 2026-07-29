"""XPS Figure Studio başlatıcı.

Masaüstü kısayolu bunu çağırır::

    pythonw.exe "C:\\Users\\...\\XPS_figures\\run.py"

`pythonw.exe` konsol penceresi açmaz, bu yüzden:
  * çıktılar `run.log` dosyasına yazılır,
  * paket kurulumu sırasında küçük bir bilgi penceresi gösterilir,
  * hata olursa uyarı kutusu çıkar.

Klasörde `.venv` varsa (run.bat ile oluşan sanal ortam) betik kendini onun
Python'u ile yeniden başlatır; böylece paketler iki kez kurulmaz.
"""

from __future__ import annotations

import importlib.util
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
LOG = ROOT / "run.log"

# import adı -> pip paketi
REQUIREMENTS = {
    "streamlit": "streamlit>=1.50",
    "matplotlib": "matplotlib>=3.8",
    "numpy": "numpy>=1.24",
    "pandas": "pandas>=2.0",
    "openpyxl": "openpyxl>=3.1",
    "docx": "python-docx>=1.1",
    "PIL": "Pillow>=10.0",
}

DEFAULT_PORT = 8501
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


# ---------------------------------------------------------------------------
# pythonw yardımcıları
# ---------------------------------------------------------------------------
def redirect_output() -> None:
    """pythonw.exe altında stdout/stderr None'dır; Streamlit buna takılır."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    handle = open(LOG, "w", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = handle


def message_box(title: str, text: str, error: bool = False) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        (messagebox.showerror if error else messagebox.showinfo)(title, text)
        root.destroy()
    except Exception:                                     # noqa: BLE001
        pass


def splash(text: str):
    """İşlem sürerken gösterilen küçük pencere; tkinter yoksa None döner."""
    try:
        import tkinter as tk

        window = tk.Tk()
        window.title("XPS Figure Studio")
        window.resizable(False, False)
        icon = ROOT / "assets" / "xps.ico"
        if icon.exists() and os.name == "nt":
            try:
                window.iconbitmap(str(icon))
            except Exception:                             # noqa: BLE001
                pass
        tk.Label(window, text=text, justify="left", padx=28, pady=26).pack()
        window.update()
        return window
    except Exception:                                     # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# ortam hazırlığı
# ---------------------------------------------------------------------------
def venv_python() -> Path | None:
    """run.bat ile kurulmuş sanal ortamın yorumlayıcısı."""
    if os.name == "nt":
        for name in ("pythonw.exe", "python.exe"):
            candidate = ROOT / ".venv" / "Scripts" / name
            if candidate.exists():
                return candidate
    else:
        candidate = ROOT / ".venv" / "bin" / "python"
        if candidate.exists():
            return candidate
    return None


def reexec_in_venv() -> None:
    """Sanal ortam varsa betiği onun Python'u ile yeniden başlat (bir kez)."""
    if os.environ.get("XPSFIG_RELAUNCHED") == "1":
        return
    target = venv_python()
    if target is None:
        return
    try:
        if Path(sys.executable).resolve() == target.resolve():
            return
    except OSError:
        return

    os.environ["XPSFIG_RELAUNCHED"] = "1"
    os.execv(str(target), [str(target), str(Path(__file__).resolve())])


def missing_packages() -> list[str]:
    return [spec for module, spec in REQUIREMENTS.items()
            if importlib.util.find_spec(module) is None]


def install(packages: list[str]) -> None:
    window = splash(
        "Gerekli paketler kuruluyor.\n\n"
        "Bu yalnızca ilk açılışta yapılır ve\n"
        "birkaç dakika sürebilir. Lütfen bekleyin..."
    )
    command = [sys.executable, "-m", "pip", "install", *packages]
    process = subprocess.Popen(command, stdout=sys.stdout, stderr=sys.stderr,
                               creationflags=CREATE_NO_WINDOW)
    try:
        while process.poll() is None:
            if window is not None:
                window.update()
            time.sleep(0.1)
    finally:
        if window is not None:
            window.destroy()

    if process.returncode != 0:
        raise RuntimeError(
            "Paketler kurulamadı. İnternet bağlantınızı kontrol edin.\n\n"
            f"Ayrıntılar: {LOG}"
        )


# ---------------------------------------------------------------------------
# başlatma
# ---------------------------------------------------------------------------
def port_in_use(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def pick_port(start: int = DEFAULT_PORT) -> int:
    for port in range(start, start + 40):
        if not port_in_use(port):
            return port
    return start


def open_browser_when_ready(port: int) -> None:
    """Sunucu ayağa kalkınca tarayıcıyı aç (arka planda bekler)."""
    def worker() -> None:
        for _ in range(200):                # ~40 saniye
            if port_in_use(port):
                webbrowser.open(f"http://localhost:{port}")
                return
            time.sleep(0.2)

    threading.Thread(target=worker, daemon=True).start()


def launch(port: int) -> None:
    from streamlit.web import cli as stcli

    # headless=true olmazsa Streamlit ilk çalıştırmada konsoldan e-posta ister;
    # pythonw.exe altında konsol olmadığı için uygulama orada kilitlenir.
    sys.argv = [
        "streamlit", "run", str(APP),
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.fileWatcherType", "none",
    ]
    open_browser_when_ready(port)
    stcli.main()


def main() -> None:
    redirect_output()
    reexec_in_venv()
    os.chdir(ROOT)      # .streamlit/config.toml proje klasöründen okunsun

    if not APP.exists():
        message_box("XPS Figure Studio",
                    f"app.py bulunamadı:\n{APP}\n\n"
                    "Kısayol yanlış klasörü gösteriyor olabilir.", error=True)
        return

    # Zaten çalışıyorsa ikinci kopya başlatma, sadece sekmeyi aç.
    if port_in_use(DEFAULT_PORT):
        webbrowser.open(f"http://localhost:{DEFAULT_PORT}")
        return

    try:
        packages = missing_packages()
        if packages:
            install(packages)
        launch(pick_port())
    except SystemExit:
        raise
    except Exception as exc:                              # noqa: BLE001
        import traceback

        traceback.print_exc()
        message_box("XPS Figure Studio", f"Başlatılamadı:\n\n{exc}", error=True)


if __name__ == "__main__":
    main()

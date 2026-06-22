# -*- coding: utf-8 -*-
"""start_all.py — Khoi dong CA server VA duong ham trong 1 lan chay.

- Bat server FastAPI (uvicorn) o cong 8000.
- Bat Cloudflare tunnel, tu doc dia chi cong khai va:
    * in ra man hinh that to,
    * ghi vao file  current_url.txt  (de ban/ung dung khac doc).
- Nhan Ctrl+C de tat ca hai.

Chay qua  start_all.bat  (da kich hoat venv san).
"""

import os
import re
import sys
import time
import signal
import shutil
import threading
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8000
URL_FILE = os.path.join(BASE_DIR, "current_url.txt")
URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def find_cloudflared():
    p = shutil.which("cloudflared")
    if p:
        return p
    for c in [
        r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
        r"C:\Program Files\cloudflared\cloudflared.exe",
    ]:
        if os.path.exists(c):
            return c
    return None


def main():
    cloudflared = find_cloudflared()
    procs = []

    print("=" * 64)
    print(" VOICE STUDIO — khoi dong server + duong ham")
    print("=" * 64)

    # 1) Server
    print("\n[1/2] Bat server tai http://localhost:%d ..." % PORT)
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app",
         "--host", "0.0.0.0", "--port", str(PORT)],
        cwd=BASE_DIR,
    )
    procs.append(server)

    # 2) Tunnel (neu co cloudflared)
    if not cloudflared:
        print("\n[!] Khong tim thay cloudflared -> chi chay noi bo (LAN).")
        print("    Cai: winget install Cloudflare.cloudflared")
    else:
        print("[2/2] Bat duong ham ra internet ...")
        tunnel = subprocess.Popen(
            [cloudflared, "tunnel", "--url", "http://localhost:%d" % PORT],
            cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="ignore",
        )
        procs.append(tunnel)

        def watch():
            for line in iter(tunnel.stdout.readline, ""):
                m = URL_RE.search(line)
                if m:
                    url = m.group(0)
                    with open(URL_FILE, "w", encoding="utf-8") as f:
                        f.write(url + "\n")
                    print("\n" + "#" * 64)
                    print("#  DIA CHI CONG KHAI cua ban:")
                    print("#     " + url)
                    print("#  (da luu vao current_url.txt)")
                    print("#" * 64 + "\n")

        threading.Thread(target=watch, daemon=True).start()

    print("\nNhan Ctrl+C de tat tat ca.\n")
    try:
        while True:
            time.sleep(1)
            if server.poll() is not None:
                print("[!] Server da dung.")
                break
    except KeyboardInterrupt:
        print("\nDang tat...")
    finally:
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        try:
            if os.path.exists(URL_FILE):
                os.remove(URL_FILE)
        except OSError:
            pass


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""manage_keys.py — Cong cu dong lenh quan ly API key.

Cach dung:
    python manage_keys.py create [ten]     # tao key moi (hien thi 1 lan)
    python manage_keys.py list             # liet ke key
    python manage_keys.py revoke <id>      # thu hoi key
"""

import sys
import time
import apikeys


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "list"

    if cmd == "create":
        name = args[1] if len(args) > 1 else "default"
        raw, rec = apikeys.create_key(name)
        print("Da tao API key moi (LUU LAI NGAY - chi hien 1 lan):")
        print()
        print("   " + raw)
        print()
        print(f"   id={rec['id']}  ten={rec['name']}")
    elif cmd == "list":
        keys = apikeys.list_keys()
        if not keys:
            print("Chua co key nao. Tao bang: python manage_keys.py create")
            return
        for r in keys:
            t = time.strftime("%Y-%m-%d %H:%M", time.localtime(r["created"]))
            state = "REVOKED" if r.get("revoked") else "active"
            print(f"  id={r['id']}  [{state}]  ten={r['name']}  tao={t}")
    elif cmd == "revoke":
        if len(args) < 2:
            print("Thieu id. Vi du: python manage_keys.py revoke a1b2c3d4")
            return
        ok = apikeys.revoke(args[1])
        print("Da thu hoi." if ok else "Khong tim thay id.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

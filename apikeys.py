# -*- coding: utf-8 -*-
"""apikeys.py — Quan ly API key (tao / liet ke / thu hoi / xac thuc).

Key tho chi hien thi 1 lan luc tao; trong file chi luu SHA-256 (khong luu key tho).
Key co dang: vs_<48 ky tu hex>.
"""

import os
import json
import time
import secrets
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(BASE_DIR, "api_keys.json")


def _load():
    if not os.path.exists(STORE):
        return []
    with open(STORE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(items):
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def _hash(key):
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def create_key(name="default"):
    """Tao key moi. Tra ve (key_tho, ban_ghi). Key tho KHONG luu lai."""
    raw = "vs_" + secrets.token_hex(24)
    items = _load()
    rec = {
        "id": secrets.token_hex(4),
        "name": name,
        "hash": _hash(raw),
        "created": int(time.time()),
        "revoked": False,
    }
    items.append(rec)
    _save(items)
    return raw, rec


def list_keys():
    """Liet ke key (khong lo hash)."""
    return [{k: v for k, v in r.items() if k != "hash"} for r in _load()]


def revoke(key_id):
    items = _load()
    found = False
    for r in items:
        if r["id"] == key_id:
            r["revoked"] = True
            found = True
    _save(items)
    return found


def verify(key):
    """Tra ve ban ghi neu key hop le va chua thu hoi, nguoc lai None."""
    if not key:
        return None
    h = _hash(key)
    for r in _load():
        if r["hash"] == h and not r.get("revoked"):
            return r
    return None


def ensure_one_key():
    """Neu chua co key nao, tao 1 key mac dinh. Tra ve key tho moi tao (hoac None)."""
    if any(not r.get("revoked") for r in _load()):
        return None
    raw, _ = create_key("auto-first")
    return raw

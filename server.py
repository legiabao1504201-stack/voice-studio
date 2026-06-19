# -*- coding: utf-8 -*-
"""server.py — Voice Studio Server (FastAPI).

Cung cap:
  - Giao dien web tai  /            (thanh truot giong ElevenLabs)
  - REST API co API key cho cac ung dung khac goi vao:
        POST /v1/tts            sinh giong (tra ve audio)
        POST /v1/voices         tai len giong mau, tra ve voice_id
        GET  /v1/voices         liet ke giong
        DELETE /v1/voices/{id}  xoa giong
        GET  /v1/languages      danh sach ngon ngu
        GET  /health            trang thai

Xac thuc: header  Authorization: Bearer <api_key>   (hoac  X-API-Key: <api_key>)
Engine chay tren GPU may ban (xem engine.py). Cac request sinh giong duoc
xep hang (1 GPU) bang mot khoa toan cuc.
"""

import os
import json
import time
import shutil
import secrets
import threading
import subprocess

from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import engine
import apikeys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOICES_DIR = os.path.join(BASE_DIR, "voices")
VOICES_DB = os.path.join(BASE_DIR, "voices.json")
WEB_DIR = os.path.join(BASE_DIR, "web")
os.makedirs(VOICES_DIR, exist_ok=True)

ENGINE = engine.VoiceEngine(log=lambda m: print("[engine]", m))
INFER_LOCK = threading.Lock()   # GPU don -> xep hang request

app = FastAPI(title="Voice Studio API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ---------------- Kho giong ----------------
def _voices_load():
    if not os.path.exists(VOICES_DB):
        return []
    with open(VOICES_DB, "r", encoding="utf-8") as f:
        return json.load(f)


def _voices_save(items):
    with open(VOICES_DB, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def _voice_path(voice_id):
    for v in _voices_load():
        if v["voice_id"] == voice_id:
            return v
    return None


# ---------------- Xac thuc ----------------
def require_key(authorization: str = Header(None), x_api_key: str = Header(None)):
    key = None
    if authorization and authorization.lower().startswith("bearer "):
        key = authorization[7:].strip()
    elif x_api_key:
        key = x_api_key.strip()
    rec = apikeys.verify(key)
    if not rec:
        raise HTTPException(status_code=401, detail="API key khong hop le hoac thieu.")
    return rec


# ---------------- Models ----------------
class TTSRequest(BaseModel):
    text: str
    voice_id: str
    language: str = "vi"
    speed: float = 1.0           # 0.70..1.20
    stability: float = 50        # 0..100 (%)
    similarity: float = 85       # 0..100 (%)
    style: float = 0             # 0..100 (%)
    format: str = "mp3_44100_128"   # hoac "wav"


# ---------------- Tien ich ----------------
def _to_wav(src_path, dst_path):
    """Chuyen file am thanh upload ve WAV (neu can) bang ffmpeg."""
    if src_path.lower().endswith(".wav"):
        shutil.copyfile(src_path, dst_path)
        return
    ff = shutil.which("ffmpeg")
    if not ff:
        # khong co ffmpeg -> giu nguyen, hy vong torchaudio doc duoc
        shutil.copyfile(src_path, dst_path)
        return
    subprocess.run([ff, "-y", "-i", src_path, "-ar", "22050", "-ac", "1", dst_path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------- Endpoints ----------------
@app.get("/", response_class=HTMLResponse)
def index():
    path = os.path.join(WEB_DIR, "index.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>Voice Studio API</h1><p>Thieu web/index.html</p>")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": ENGINE.model is not None,
        "device": ENGINE.device,
    }


@app.get("/v1/languages")
def languages():
    return {"languages": [{"name": k, "code": v} for k, v in engine.SUPPORTED_LANGUAGES.items()]}


@app.get("/v1/voices")
def list_voices(_=Depends(require_key)):
    return {"voices": [{"voice_id": v["voice_id"], "name": v["name"], "created": v["created"]}
                       for v in _voices_load()]}


@app.post("/v1/voices")
def add_voice(name: str = Form(...), file: UploadFile = File(...), _=Depends(require_key)):
    voice_id = "vc_" + secrets.token_hex(8)
    raw_tmp = os.path.join(VOICES_DIR, voice_id + "_raw" + os.path.splitext(file.filename or "")[1])
    wav_path = os.path.join(VOICES_DIR, voice_id + ".wav")
    with open(raw_tmp, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        _to_wav(raw_tmp, wav_path)
    finally:
        if os.path.exists(raw_tmp) and raw_tmp != wav_path:
            os.remove(raw_tmp)
    items = _voices_load()
    items.append({"voice_id": voice_id, "name": name, "file": wav_path, "created": int(time.time())})
    _voices_save(items)
    return {"voice_id": voice_id, "name": name}


@app.delete("/v1/voices/{voice_id}")
def delete_voice(voice_id: str, _=Depends(require_key)):
    items = _voices_load()
    keep, removed = [], None
    for v in items:
        if v["voice_id"] == voice_id:
            removed = v
        else:
            keep.append(v)
    if not removed:
        raise HTTPException(404, "Khong tim thay voice_id.")
    _voices_save(keep)
    try:
        if os.path.exists(removed["file"]):
            os.remove(removed["file"])
    except OSError:
        pass
    return {"deleted": voice_id}


@app.post("/v1/tts")
def tts(req: TTSRequest, _=Depends(require_key)):
    if not req.text.strip():
        raise HTTPException(400, "Thieu 'text'.")
    voice = _voice_path(req.voice_id)
    if not voice:
        raise HTTPException(400, "voice_id khong ton tai. Hay tao giong qua POST /v1/voices truoc.")
    if req.language not in engine.SUPPORTED_LANGUAGES.values():
        raise HTTPException(400, f"Ngon ngu '{req.language}' khong ho tro.")

    # phan tram 0..100 -> 0..1; speed giu nguyen gia tri thuc
    sliders = {
        "speed": float(req.speed),
        "stability": float(req.stability) / 100.0,
        "similarity": float(req.similarity) / 100.0,
        "style": float(req.style) / 100.0,
    }
    out_name = f"api_{int(time.time())}_{secrets.token_hex(3)}.wav"
    out_path = os.path.join(engine.OUTPUT_DIR, out_name)

    with INFER_LOCK:
        wav_path = ENGINE.synthesize(req.text, voice["file"], req.language, sliders, out_path=out_path)
        final = engine.convert_format(wav_path, req.format)

    media = "audio/mpeg" if final.lower().endswith(".mp3") else "audio/wav"
    return FileResponse(final, media_type=media, filename=os.path.basename(final))


@app.on_event("startup")
def _startup():
    raw = apikeys.ensure_one_key()
    if raw:
        print("\n" + "=" * 60)
        print(" CHUA CO API KEY -> da tao key dau tien cho ban:")
        print("   " + raw)
        print(" (Luu lai. Tao them: python manage_keys.py create)")
        print("=" * 60 + "\n")

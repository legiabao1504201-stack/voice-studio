# -*- coding: utf-8 -*-
"""
engine.py — Lop boc (wrapper) cho mo hinh giong noi offline viXTTS / XTTS-v2.

Y tuong: cac thanh truot trong giao dien (giong ElevenLabs) duoc anh xa sang
tham so that cua mo hinh XTTS. Anh xa nay duoc ghi ro rang trong ham
`map_sliders_to_params` ben duoi de ban co the tinh chinh.

Mo hinh dung: viXTTS (capleaf/viXTTS) — ban fine-tune cua XTTS-v2 ho tro tieng Viet
cong them 16 ngon ngu khac. Co the clone giong tu 1 file mau 6-30 giay.
"""

import os
import sys
import time
import wave
import threading

# Thu muc luu model va dau ra
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models", "viXTTS")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Repo HuggingFace chua model tieng Viet
HF_REPO_ID = "capleaf/viXTTS"

# Cac ngon ngu XTTS-v2 ho tro (viXTTS them 'vi')
SUPPORTED_LANGUAGES = {
    "Tiếng Việt": "vi",
    "English": "en",
    "Español": "es",
    "Français": "fr",
    "Deutsch": "de",
    "Italiano": "it",
    "Português": "pt",
    "Polski": "pl",
    "Türkçe": "tr",
    "Русский": "ru",
    "Nederlands": "nl",
    "Čeština": "cs",
    "العربية": "ar",
    "中文": "zh-cn",
    "日本語": "ja",
    "한국어": "ko",
    "हिन्दी": "hi",
}


import re
import textwrap


def _hard_wrap(s, limit):
    """Cat 1 cau qua dai theo tu (khong cat giua tu)."""
    return textwrap.wrap(s, width=limit, break_long_words=False,
                         break_on_hyphens=False) or [s]


def _split_text(text, limit=230):
    """Tach van ban thanh cac doan <= `limit` ky tu theo cau.

    Tu lam viec nay de KHONG phai dung spaCy (XTTS doi spaCy khi text dai).
    Tach theo dau cau . ! ? ; xuong dong, roi gom cac cau ngan lai.
    """
    text = text.strip()
    if len(text) <= limit:
        return [text] if text else []

    parts = re.split(r"(?<=[\.\!\?\;\n…:])\s+", text)
    chunks, cur = [], ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        pieces = [p] if len(p) <= limit else _hard_wrap(p, limit)
        for piece in pieces:
            if not cur:
                cur = piece
            elif len(cur) + 1 + len(piece) <= limit:
                cur = cur + " " + piece
            else:
                chunks.append(cur)
                cur = piece
    if cur:
        chunks.append(cur)
    return chunks


def _vi_clean(txt):
    """Lam sach toi thieu cho tieng Viet (giu nguyen dau).

    Bo tokenizer goc cua XTTS khong ho tro 'vi' (se raise NotImplementedError
    va thieu trong char_limits). Ta chi lam sach nhe, du de model viXTTS doc.
    """
    txt = txt.replace('"', "")
    txt = txt.lower()
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _patch_tokenizer_for_vi(model):
    """Vá tokenizer da nap de ho tro tieng Viet ('vi')."""
    tok = getattr(model, "tokenizer", None)
    if tok is None:
        return
    # 1) Them gioi han ky tu cho 'vi' (tranh KeyError o split_sentence)
    if hasattr(tok, "char_limits") and "vi" not in tok.char_limits:
        tok.char_limits["vi"] = 250
    # 2) Vá preprocess_text de 'vi' khong roi vao nhanh NotImplementedError
    if getattr(tok, "_vi_patched", False):
        return
    _orig_pre = tok.preprocess_text

    def _patched_pre(txt, lang, _orig=_orig_pre):
        if lang == "vi":
            return _vi_clean(txt)
        return _orig(txt, lang)

    tok.preprocess_text = _patched_pre
    tok._vi_patched = True


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _lerp(a, b, t):
    """Noi suy tuyen tinh giua a va b theo t (0..1)."""
    return a + (b - a) * _clamp(t, 0.0, 1.0)


def map_sliders_to_params(speed, stability, similarity, style):
    """
    Chuyen gia tri 4 thanh truot (moi cai 0.0..1.0) thanh tham so XTTS.

    speed       : gia tri toc do thuc 0.70..1.20 (giong ElevenLabs)
    stability   : 0 = bien thien nhieu, 1 = on dinh hon
    similarity  : 0 = thap, 1 = cao (giong file mau hon)
    style       : 0 = khong nhan, 1 = phong dai bieu cam

    Tra ve dict tham so truyen vao model.inference().
    """
    # Speed da la gia tri thuc, chi can kep trong gioi han ElevenLabs
    xtts_speed = _clamp(speed, 0.70, 1.20)

    # Stability cao  -> temperature thap (it ngau nhien) + repetition_penalty cao
    # Style cao       -> temperature cao + top_p cao (bieu cam hon)
    # Hai yeu to nay tac dong nguoc nhau len temperature; ta tron lai:
    base_temp = _lerp(0.75, 0.30, stability)        # on dinh keo temp xuong
    temp = base_temp + _lerp(0.0, 0.45, style)      # style keo temp len
    temp = _clamp(temp, 0.20, 1.10)

    repetition_penalty = _lerp(2.0, 7.0, stability)
    top_p = _lerp(0.80, 0.97, style)
    top_k = int(_lerp(30, 70, style))
    length_penalty = 1.0

    # Similarity -> dung nhieu giong mau hon de tao dac trung nguoi noi
    gpt_cond_len = int(_lerp(6, 30, similarity))    # giay tham chieu
    max_ref_length = 60

    return {
        "speed": round(xtts_speed, 3),
        "temperature": round(temp, 3),
        "repetition_penalty": round(repetition_penalty, 3),
        "top_p": round(top_p, 3),
        "top_k": top_k,
        "length_penalty": length_penalty,
        "gpt_cond_len": gpt_cond_len,
        "max_ref_length": max_ref_length,
        "enable_text_splitting": True,
    }


class VoiceEngine:
    """Quan ly tai model va sinh giong. Tai model lan dau co the lau (1 lan)."""

    def __init__(self, log=print):
        self.log = log
        self.model = None
        self.config = None
        self.device = "cpu"
        self._lock = threading.Lock()

    # ---------- Tai model ----------
    def ensure_model_downloaded(self):
        """Tai file model tu HuggingFace neu chua co (chi 1 lan)."""
        need = ["model.pth", "config.json", "vocab.json"]
        have_all = all(os.path.exists(os.path.join(MODEL_DIR, f)) for f in need)
        if have_all:
            self.log("Da co san model viXTTS.")
            return

        self.log("Dang tai model viXTTS tu HuggingFace (lan dau, ~1.8GB)...")
        from huggingface_hub import snapshot_download
        os.makedirs(MODEL_DIR, exist_ok=True)
        snapshot_download(
            repo_id=HF_REPO_ID,
            local_dir=MODEL_DIR,
            allow_patterns=["*.pth", "*.json", "vocab.json", "speakers_xtts.pth"],
        )
        self.log("Tai model xong.")

    def load(self):
        """Nap model vao bo nho (GPU neu co)."""
        if self.model is not None:
            return
        with self._lock:
            if self.model is not None:
                return
            self.ensure_model_downloaded()

            import torch
            from TTS.tts.configs.xtts_config import XttsConfig
            from TTS.tts.models.xtts import Xtts

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.log(f"Thiet bi: {self.device.upper()}")

            self.log("Dang nap model vao bo nho...")
            config = XttsConfig()
            config.load_json(os.path.join(MODEL_DIR, "config.json"))
            model = Xtts.init_from_config(config)
            model.load_checkpoint(
                config,
                checkpoint_dir=MODEL_DIR,
                use_deepspeed=False,
            )
            if self.device == "cuda":
                model.cuda()
            model.eval()

            _patch_tokenizer_for_vi(model)

            self.config = config
            self.model = model
            self.log("San sang.")

    # ---------- Sinh giong ----------
    def synthesize(self, text, reference_wav, language, sliders, out_path=None):
        """
        text          : noi dung can doc
        reference_wav : duong dan file giong mau (.wav) de clone
        language      : ma ngon ngu (vi, en, ...)
        sliders       : dict {speed, stability, similarity, style} moi cai 0..1
        out_path      : noi luu file .wav (mac dinh trong output/)
        """
        if not text or not text.strip():
            raise ValueError("Chua nhap noi dung can doc.")
        if not reference_wav or not os.path.exists(reference_wav):
            raise ValueError("Chua chon file giong mau (.wav).")

        self.load()
        params = map_sliders_to_params(
            sliders.get("speed", 1.0),
            sliders.get("stability", 0.5),
            sliders.get("similarity", 0.75),
            sliders.get("style", 0.0),
        )
        self.log(f"Tham so: {params}")

        import torch

        self.log("Dang phan tich giong mau...")
        gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(
            audio_path=[reference_wav],
            gpt_cond_len=params["gpt_cond_len"],
            max_ref_length=params["max_ref_length"],
        )

        import numpy as np

        # Tu tach doan (KHONG dung enable_text_splitting cua XTTS de tranh spaCy)
        chunks = _split_text(text, limit=230)
        self.log(f"Tach thanh {len(chunks)} doan. Dang sinh giong noi...")
        t0 = time.time()
        gap = np.zeros(int(24000 * 0.30), dtype=np.float32)  # 0.3s lang giua cac doan
        pieces = []
        for i, chunk in enumerate(chunks, 1):
            if len(chunks) > 1:
                self.log(f"  Doan {i}/{len(chunks)}...")
            out = self.model.inference(
                chunk,
                language,
                gpt_cond_latent,
                speaker_embedding,
                temperature=params["temperature"],
                length_penalty=params["length_penalty"],
                repetition_penalty=params["repetition_penalty"],
                top_k=params["top_k"],
                top_p=params["top_p"],
                speed=params["speed"],
                enable_text_splitting=False,
            )
            pieces.append(np.asarray(out["wav"], dtype=np.float32))
            if i < len(chunks):
                pieces.append(gap)
        wav = np.concatenate(pieces) if len(pieces) > 1 else pieces[0]
        dt = time.time() - t0

        if out_path is None:
            out_path = os.path.join(OUTPUT_DIR, f"voice_{int(time.time())}.wav")

        self._save_wav(wav, out_path, sample_rate=24000)
        self.log(f"Xong sau {dt:.1f}s -> {out_path}")
        return out_path

    @staticmethod
    def _save_wav(wav, path, sample_rate=24000):
        """Luu mang sample (float -1..1) thanh file WAV 16-bit."""
        import numpy as np

        arr = np.asarray(wav, dtype=np.float32)
        arr = np.clip(arr, -1.0, 1.0)
        pcm = (arr * 32767).astype("<i2")
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm.tobytes())


# ---------- Chuyen doi dinh dang dau ra ----------
def convert_format(wav_path, output_format):
    """
    Chuyen WAV sang dinh dang ElevenLabs-style neu co ffmpeg.
    output_format vi du: 'mp3_44100_128'. Neu khong co ffmpeg, giu nguyen WAV.
    Tra ve duong dan file cuoi cung.
    """
    import shutil
    import subprocess

    if output_format.startswith("wav"):
        return wav_path

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return wav_path  # khong co ffmpeg -> giu WAV

    try:
        _codec, rate, bitrate = output_format.split("_")  # mp3_44100_128
    except ValueError:
        return wav_path

    out_path = os.path.splitext(wav_path)[0] + ".mp3"
    cmd = [
        ffmpeg, "-y", "-i", wav_path,
        "-ar", rate,
        "-b:a", f"{bitrate}k",
        out_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path

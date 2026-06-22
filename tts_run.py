# -*- coding: utf-8 -*-
import os, sys, time
sys.stdout.reconfigure(encoding="utf-8")
import engine

SCRIPT = r"D:\AI-Agent automation video\06-19\Content\script.txt"
VOICE_DIR = r"D:\AI-Agent automation video\06-19\Voice"
os.makedirs(VOICE_DIR, exist_ok=True)
WAV = os.path.join(VOICE_DIR, "voice.wav")

text = open(SCRIPT, encoding="utf-8").read().strip()
print(f"[tts] script chars: {len(text)}", flush=True)

sliders = {"speed": 1.0, "stability": 0.6, "similarity": 0.85, "style": 0.2}
e = engine.VoiceEngine(log=lambda *a: print("[eng]", *a, flush=True))
t0 = time.time()
wav = e.synthesize(text, "ref_sample.wav", "en", sliders, out_path=WAV)
print(f"[tts] WAV done in {time.time()-t0:.0f}s -> {wav}", flush=True)
final = engine.convert_format(wav, "mp3_44100_128")
print(f"[tts] FINAL -> {final}", flush=True)
print("[tts] ALL DONE", flush=True)

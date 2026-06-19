# -*- coding: utf-8 -*-
"""
app.py — Giao dien Windows tao giong noi offline, bo cuc giong ElevenLabs.

Cac thanh truot: Speed, Stability, Similarity, Style Exaggeration.
Cong tac: Language Override.  Menu: Output Format.
Engine: viXTTS (file engine.py).
"""

import os
import threading
import traceback

import customtkinter as ctk
from tkinter import filedialog, messagebox

import engine

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class SliderRow(ctk.CTkFrame):
    """Mot hang: tieu de + o nhap so + thanh truot + 2 nhan trai/phai.

    fmt = "speed"   -> hien thi so thuc 2 chu so (vi du Speed 0.70..1.20)
    fmt = "percent" -> hien thi phan tram nguyen 0..100 (%)
    O nhap va thanh truot dong bo 2 chieu, tu kep trong [vmin, vmax].
    """

    def __init__(self, master, title, left_label, right_label,
                 vmin, vmax, default, fmt="percent"):
        super().__init__(master, fg_color="transparent")
        self.vmin, self.vmax, self.fmt = vmin, vmax, fmt
        self.columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        header.columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=15, weight="bold"),
                     anchor="w").grid(row=0, column=0, sticky="w")
        self.entry = ctk.CTkEntry(header, width=72, justify="center")
        self.entry.grid(row=0, column=1, sticky="e")
        self.entry.bind("<Return>", self._on_entry)
        self.entry.bind("<FocusOut>", self._on_entry)

        step = 0.01 if fmt == "speed" else 1.0
        steps = max(1, int(round((vmax - vmin) / step)))
        self.var = ctk.DoubleVar(value=default)
        self.slider = ctk.CTkSlider(self, from_=vmin, to=vmax, number_of_steps=steps,
                                    variable=self.var, height=16, button_corner_radius=10,
                                    command=self._on_slide)
        self.slider.grid(row=1, column=0, sticky="ew")

        labels = ctk.CTkFrame(self, fg_color="transparent")
        labels.grid(row=2, column=0, sticky="ew")
        labels.columnconfigure(0, weight=1)
        labels.columnconfigure(1, weight=1)
        ctk.CTkLabel(labels, text=left_label, text_color="gray50",
                     font=ctk.CTkFont(size=11), anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(labels, text=right_label, text_color="gray50",
                     font=ctk.CTkFont(size=11), anchor="e").grid(row=0, column=1, sticky="e")

        self._refresh_entry(default)

    def _format(self, v):
        if self.fmt == "speed":
            return f"{v:.2f}"
        return f"{int(round(v))}%"

    def _refresh_entry(self, v):
        self.entry.delete(0, "end")
        self.entry.insert(0, self._format(v))

    def _on_slide(self, v):
        self._refresh_entry(float(v))

    def _on_entry(self, _evt=None):
        raw = self.entry.get().strip().replace("%", "").replace(",", ".")
        try:
            v = float(raw)
        except ValueError:
            v = float(self.var.get())
        v = max(self.vmin, min(self.vmax, v))
        self.var.set(v)
        self._refresh_entry(v)

    def value(self):
        """Gia tri thuc tren thanh truot (vi du Speed = 0.85, hoac percent 0..100)."""
        return float(self.var.get())

    def fraction(self):
        """Quy ve 0..1 theo gioi han (dung cho stability/similarity/style)."""
        span = (self.vmax - self.vmin) or 1.0
        return (self.value() - self.vmin) / span


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Voice Studio — Tao giong noi offline")
        self.geometry("560x880")
        self.minsize(520, 760)

        self.engine = engine.VoiceEngine(log=self.log)
        self.reference_path = None
        self.last_output = None

        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = ctk.CTkScrollableFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=18, pady=14)
        root.columnconfigure(0, weight=1)

        r = 0
        ctk.CTkLabel(root, text="Voice Studio",
                     font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=r, column=0, sticky="w"); r += 1
        ctk.CTkLabel(root, text="Tao giong noi offline tren may ban (viXTTS)",
                     text_color="gray50").grid(row=r, column=0, sticky="w", pady=(0, 12)); r += 1

        # Noi dung can doc
        ctk.CTkLabel(root, text="Noi dung can doc",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     anchor="w").grid(row=r, column=0, sticky="ew"); r += 1
        self.textbox = ctk.CTkTextbox(root, height=120, wrap="word")
        self.textbox.grid(row=r, column=0, sticky="ew", pady=(2, 12))
        self.textbox.insert("1.0", "Xin chào, đây là giọng nói được tạo hoàn toàn trên máy của bạn.")
        r += 1

        # Giong mau (clone)
        ctk.CTkLabel(root, text="Giong mau (file .wav 6-30s de clone)",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     anchor="w").grid(row=r, column=0, sticky="ew"); r += 1
        ref_row = ctk.CTkFrame(root, fg_color="transparent")
        ref_row.grid(row=r, column=0, sticky="ew", pady=(2, 14))
        ref_row.columnconfigure(0, weight=1)
        self.ref_label = ctk.CTkLabel(ref_row, text="Chua chon file...",
                                      text_color="gray50", anchor="w")
        self.ref_label.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(ref_row, text="Chon file", width=90,
                      command=self.pick_reference).grid(row=0, column=1, padx=(8, 0))
        r += 1

        # 4 thanh truot (co o nhap so)
        self.s_speed = SliderRow(root, "Speed", "Slower (0.70)", "Faster (1.20)",
                                 vmin=0.70, vmax=1.20, default=1.00, fmt="speed")
        self.s_speed.grid(row=r, column=0, sticky="ew", pady=8); r += 1
        self.s_stability = SliderRow(root, "Stability", "More variable", "More stable",
                                     vmin=0, vmax=100, default=50, fmt="percent")
        self.s_stability.grid(row=r, column=0, sticky="ew", pady=8); r += 1
        self.s_similarity = SliderRow(root, "Similarity", "Low", "High",
                                      vmin=0, vmax=100, default=85, fmt="percent")
        self.s_similarity.grid(row=r, column=0, sticky="ew", pady=8); r += 1
        self.s_style = SliderRow(root, "Style Exaggeration", "None", "Exaggerated",
                                 vmin=0, vmax=100, default=0, fmt="percent")
        self.s_style.grid(row=r, column=0, sticky="ew", pady=8); r += 1

        # Ngon ngu doc (luon bat, chon truc tiep)
        ctk.CTkLabel(root, text="Ngôn ngữ đọc (Language)",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     anchor="w").grid(row=r, column=0, sticky="ew"); r += 1
        self.lang_menu = ctk.CTkOptionMenu(root, values=list(engine.SUPPORTED_LANGUAGES.keys()))
        self.lang_menu.set("Tiếng Việt")
        self.lang_menu.grid(row=r, column=0, sticky="ew", pady=(2, 6)); r += 1
        ctk.CTkLabel(root, text="Mẹo: đổi sang English (hoặc 15 ngôn ngữ khác) để đọc văn bản ngôn ngữ đó.",
                     text_color="gray50", font=ctk.CTkFont(size=11),
                     anchor="w", wraplength=460, justify="left").grid(
            row=r, column=0, sticky="ew", pady=(0, 12)); r += 1

        # Output Format
        ctk.CTkLabel(root, text="Output Format",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     anchor="w").grid(row=r, column=0, sticky="ew"); r += 1
        self.fmt_menu = ctk.CTkOptionMenu(root, values=[
            "MP3 44.1 kHz (128kbps)",
            "MP3 44.1 kHz (192kbps)",
            "WAV 24 kHz (goc)",
        ])
        self.fmt_menu.set("MP3 44.1 kHz (128kbps)")
        self.fmt_menu.grid(row=r, column=0, sticky="ew", pady=(2, 16)); r += 1

        # Nut tao
        self.gen_btn = ctk.CTkButton(root, text="🎙  Tao giong noi", height=44,
                                     font=ctk.CTkFont(size=16, weight="bold"),
                                     command=self.on_generate)
        self.gen_btn.grid(row=r, column=0, sticky="ew"); r += 1

        self.open_btn = ctk.CTkButton(root, text="📂 Mo file vua tao", height=36,
                                      fg_color="gray70", text_color="black",
                                      hover_color="gray60", command=self.open_output,
                                      state="disabled")
        self.open_btn.grid(row=r, column=0, sticky="ew", pady=(8, 8)); r += 1

        # Log
        self.status = ctk.CTkTextbox(root, height=120, wrap="word",
                                     font=ctk.CTkFont(size=11))
        self.status.grid(row=r, column=0, sticky="ew", pady=(4, 0)); r += 1
        self.status.configure(state="disabled")
        self.log("San sang. Lan tao dau tien se tai model (~1.8GB) — chi 1 lan.")

    # ---------------- Hanh dong ----------------
    def pick_reference(self):
        path = filedialog.askopenfilename(
            title="Chon file giong mau",
            filetypes=[("Audio", "*.wav *.mp3 *.flac *.m4a"), ("Tat ca", "*.*")])
        if path:
            self.reference_path = path
            self.ref_label.configure(text=os.path.basename(path), text_color="black")

    def log(self, msg):
        def _append():
            self.status.configure(state="normal")
            self.status.insert("end", str(msg) + "\n")
            self.status.see("end")
            self.status.configure(state="disabled")
        try:
            self.after(0, _append)
        except Exception:
            print(msg)

    def _format_code(self):
        sel = self.fmt_menu.get()
        if sel.startswith("WAV"):
            return "wav"
        if "192" in sel:
            return "mp3_44100_192"
        return "mp3_44100_128"

    def on_generate(self):
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Thieu noi dung", "Hay nhap noi dung can doc.")
            return
        if not self.reference_path:
            messagebox.showwarning("Thieu giong mau", "Hay chon 1 file giong mau (.wav).")
            return

        language = engine.SUPPORTED_LANGUAGES[self.lang_menu.get()]

        sliders = {
            "speed": self.s_speed.value(),          # gia tri thuc 0.70..1.20
            "stability": self.s_stability.fraction(),  # 0..1 tu phan tram
            "similarity": self.s_similarity.fraction(),
            "style": self.s_style.fraction(),
        }
        fmt = self._format_code()

        self.gen_btn.configure(state="disabled", text="Dang xu ly...")
        self.open_btn.configure(state="disabled")
        threading.Thread(target=self._worker,
                         args=(text, self.reference_path, language, sliders, fmt),
                         daemon=True).start()

    def _worker(self, text, ref, language, sliders, fmt):
        try:
            wav_path = self.engine.synthesize(text, ref, language, sliders)
            final = engine.convert_format(wav_path, fmt)
            if final.endswith(".wav") and fmt.startswith("mp3"):
                self.log("(!) Khong tim thay ffmpeg — giu file WAV. Xem README de cai ffmpeg.")
            self.last_output = final
            self.log(f"HOAN TAT: {final}")
            self.after(0, lambda: self.open_btn.configure(state="normal"))
        except Exception as e:
            self.log("LOI: " + str(e))
            self.log(traceback.format_exc())
            self.after(0, lambda: messagebox.showerror("Loi", str(e)))
        finally:
            self.after(0, lambda: self.gen_btn.configure(state="normal", text="🎙  Tao giong noi"))

    def open_output(self):
        if self.last_output and os.path.exists(self.last_output):
            os.startfile(os.path.dirname(self.last_output))


if __name__ == "__main__":
    App().mainloop()

"""Native desktop UI (CustomTkinter): first-run setup + settings windows.

A single hidden Tk root runs its own mainloop on a dedicated thread. All Tk
work is marshalled onto that thread with ``root.after`` so it stays
thread-safe while the tray icon owns the main thread. Background work (model
downloads) runs on worker threads and pushes updates back via ``after``.
"""
from __future__ import annotations

import logging
import threading
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk

log = logging.getLogger(__name__)

# Cute pastel palette.
PINK = "#ff8fb1"
PINK_DK = "#ef6d95"
PURPLE = "#b39ddb"
PURPLE_DK = "#9a82c9"
BG = "#fff5f9"
CARD = "#ffffff"
INK = "#5a5468"
MUTED = "#9a8fb0"


class UIManager:
    def __init__(self, controller):
        self.c = controller
        self._root: Optional[ctk.CTk] = None
        self._ready = threading.Event()
        self._setup_win: Optional[ctk.CTkToplevel] = None
        self._settings_win: Optional[ctk.CTkToplevel] = None

    # -- lifecycle ----------------------------------------------------------
    def start(self) -> None:
        threading.Thread(target=self._run, name="ui-tk", daemon=True).start()
        self._ready.wait(timeout=8)

    def _run(self) -> None:
        try:
            ctk.set_appearance_mode("light")
            ctk.set_default_color_theme("blue")
            root = ctk.CTk()
            root.withdraw()  # keep the hidden controller root off-screen
            root.configure(fg_color=BG)
            self._root = root
            self._ready.set()
            root.mainloop()
        except Exception:
            log.exception("Tk UI thread crashed")
            self._ready.set()

    def show_setup(self) -> None:
        if self._root:
            self._root.after(0, self._open_setup)

    def show_settings(self) -> None:
        if self._root:
            self._root.after(0, self._open_settings)

    # -- shared helpers -----------------------------------------------------
    def _focus(self, win: ctk.CTkToplevel) -> None:
        win.configure(fg_color=BG)
        win.lift()
        win.attributes("-topmost", True)
        win.after(200, lambda: win.attributes("-topmost", False))
        win.focus_force()

    def _header(self, parent, title: str, subtitle: str) -> None:
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", padx=24, pady=(20, 6))
        ctk.CTkLabel(bar, text="🐱", font=("Segoe UI Emoji", 40)).pack(side="left", padx=(0, 12))
        col = ctk.CTkFrame(bar, fg_color="transparent")
        col.pack(side="left", anchor="w")
        ctk.CTkLabel(col, text=title, font=("Segoe UI", 22, "bold"), text_color=INK).pack(anchor="w")
        ctk.CTkLabel(col, text=subtitle, font=("Segoe UI", 12), text_color=MUTED).pack(anchor="w")

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=18)
        card.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 15, "bold"),
                     text_color=INK).pack(anchor="w", padx=18, pady=(14, 6))
        return card

    def _toast(self, win, text: str) -> None:
        lbl = ctk.CTkLabel(win, text=text, fg_color=INK, text_color="#fff",
                           corner_radius=999, font=("Segoe UI", 12))
        lbl.place(relx=0.5, rely=0.96, anchor="s")
        win.after(2400, lbl.destroy)

    def _pink_button(self, parent, text, command, big=False):
        return ctk.CTkButton(
            parent, text=text, command=command,
            fg_color=PINK, hover_color=PINK_DK, text_color="#fff",
            corner_radius=999, font=("Segoe UI", 14, "bold"),
            height=44 if big else 34,
        )

    def _language_picker(self, parent, var):
        """Radio buttons for each language with a download badge."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=18, pady=(0, 10))
        status = self.c.get_status()
        for lang in status["languages"]:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkRadioButton(
                row, text=lang["label"], variable=var, value=lang["code"],
                fg_color=PINK, hover_color=PINK_DK, text_color=INK,
                font=("Segoe UI", 13),
            ).pack(side="left")
            badge = "✅ DL済み" if lang["downloaded"] else "⬇ 未DL"
            ctk.CTkLabel(row, text=badge, text_color=(MUTED if lang["downloaded"] else PINK_DK),
                         font=("Segoe UI", 11)).pack(side="right", padx=8)
        return frame

    def _browse_into(self, entry: ctk.CTkEntry) -> None:
        path = filedialog.askdirectory(title="モデルの保存先を選択")
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def _start_download(self, language, model_dir, prog_bar, prog_lbl, on_done) -> None:
        prog_bar.set(0)
        prog_bar.pack(fill="x", padx=18, pady=(6, 2))
        prog_lbl.pack(anchor="w", padx=18, pady=(0, 10))
        prog_lbl.configure(text="準備中…")

        def progress(done: int, total: int) -> None:
            def upd():
                if total > 0:
                    prog_bar.set(min(1.0, done / total))
                    prog_lbl.configure(
                        text=f"ダウンロード中… {int(done/total*100)}% "
                             f"({done/1e6:.1f}MB / {total/1e6:.1f}MB)")
                else:
                    prog_lbl.configure(text=f"ダウンロード中… {done/1e6:.1f}MB")
            if self._root:
                self._root.after(0, upd)

        def worker():
            try:
                if model_dir:
                    self.c.apply_settings({"model_dir": model_dir})
                self.c.download_model(language, progress)
                self.c.ocr.reload()
                self._root.after(0, lambda: (prog_bar.set(1.0),
                                             prog_lbl.configure(text="完了！🎉"),
                                             on_done(True, None)))
            except Exception as e:
                msg = str(e)
                log.exception("model download failed")
                self._root.after(0, lambda: (prog_lbl.configure(text=f"エラー: {msg}"),
                                             on_done(False, msg)))

        threading.Thread(target=worker, name="model-dl", daemon=True).start()

    # -- setup window -------------------------------------------------------
    def _open_setup(self) -> None:
        if self._setup_win is not None and self._setup_win.winfo_exists():
            self._focus(self._setup_win)
            return
        win = ctk.CTkToplevel(self._root)
        self._setup_win = win
        win.title("はじめての設定 ・ OCR ツール")
        win.geometry("480x560")
        self._header(win, "はじめまして！", "まずは言語を選んでね🌸")

        status = self.c.get_status()
        lang_var = ctk.StringVar(value=status["config"].get("language", "japan"))

        c1 = self._card(win, "① 認識する言語")
        self._language_picker(c1, lang_var)

        c2 = self._card(win, "② モデルの保存先（空欄で既定）")
        row = ctk.CTkFrame(c2, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 12))
        dir_entry = ctk.CTkEntry(row, height=34, corner_radius=10)
        dir_entry.insert(0, status["model_dir"])
        dir_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="参照", width=60, fg_color=PURPLE, hover_color=PURPLE_DK,
                      command=lambda: self._browse_into(dir_entry)).pack(side="left", padx=(8, 0))

        c3 = self._card(win, "③ ダウンロードして開始")
        prog = ctk.CTkProgressBar(c3, progress_color=PINK)
        prog_lbl = ctk.CTkLabel(c3, text="", text_color=MUTED, font=("Segoe UI", 11))
        btn = self._pink_button(c3, "ダウンロードして始める ✨", None, big=True)
        btn.pack(fill="x", padx=18, pady=(4, 16))

        def on_done(ok, err):
            if ok:
                self.c.complete_setup(lang_var.get(), dir_entry.get().strip())
                self._toast(win, "セットアップ完了！🎉")
                win.after(900, win.destroy)
            else:
                btn.configure(state="normal")

        btn.configure(command=lambda: (btn.configure(state="disabled"),
                                       self._start_download(lang_var.get(),
                                                            dir_entry.get().strip(),
                                                            prog, prog_lbl, on_done)))
        win.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, "_setup_win", None), win.destroy()))
        self._focus(win)

    # -- settings window ----------------------------------------------------
    def _open_settings(self) -> None:
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._focus(self._settings_win)
            return
        win = ctk.CTkToplevel(self._root)
        self._settings_win = win
        win.title("設定 ・ OCR ツール")
        win.geometry("520x640")
        self._header(win, "設定", "カスタマイズしてね🛠️")

        status = self.c.get_status()
        cfg = status["config"]
        body = ctk.CTkScrollableFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=4)

        # --- quick actions ---
        qa = self._card(body, "クイック操作")
        qrow = ctk.CTkFrame(qa, fg_color="transparent")
        qrow.pack(fill="x", padx=18, pady=(0, 14))
        actions = [("📋 画像をOCR", self.c.manual_ocr_from_clipboard),
                   ("🔊 読み上げ", self.c.speak_last),
                   ("🌐 翻訳", self.c.translate_last)]
        for txt, fn in actions:
            ctk.CTkButton(qrow, text=txt, command=fn, fg_color=PURPLE,
                          hover_color=PURPLE_DK, corner_radius=999,
                          font=("Segoe UI", 12)).pack(side="left", expand=True, fill="x", padx=3)

        # --- language & model ---
        cl = self._card(body, "言語とモデル")
        lang_var = ctk.StringVar(value=cfg.get("language", "japan"))
        self._language_picker(cl, lang_var)
        mrow = ctk.CTkFrame(cl, fg_color="transparent")
        mrow.pack(fill="x", padx=18, pady=(0, 8))
        dir_entry = ctk.CTkEntry(mrow, height=34, corner_radius=10)
        dir_entry.insert(0, status["model_dir"])
        dir_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(mrow, text="参照", width=60, fg_color=PURPLE, hover_color=PURPLE_DK,
                      command=lambda: self._browse_into(dir_entry)).pack(side="left", padx=(8, 0))
        prog = ctk.CTkProgressBar(cl, progress_color=PINK)
        prog_lbl = ctk.CTkLabel(cl, text="", text_color=MUTED, font=("Segoe UI", 11))
        ctk.CTkButton(cl, text="選択言語のモデルをDL/再取得", fg_color=PINK, hover_color=PINK_DK,
                      corner_radius=999,
                      command=lambda: self._start_download(lang_var.get(), dir_entry.get().strip(),
                                                           prog, prog_lbl, lambda ok, e: None)
                      ).pack(fill="x", padx=18, pady=(2, 14))

        # --- behaviour ---
        cb = self._card(body, "動作")
        auto_ocr = ctk.CTkSwitch(cb, text="自動OCR（クリップボード監視）", progress_color=PINK)
        copy_cb = ctk.CTkSwitch(cb, text="結果をクリップボードへコピー", progress_color=PINK)
        notif = ctk.CTkSwitch(cb, text="通知を表示", progress_color=PINK)
        for sw, val in ((auto_ocr, cfg.get("auto_ocr", True)),
                        (copy_cb, cfg.get("copy_to_clipboard", True)),
                        (notif, cfg.get("show_notifications", True))):
            sw.pack(anchor="w", padx=18, pady=4)
            sw.select() if val else sw.deselect()
        ctk.CTkLabel(cb, text="", height=4).pack()

        # --- TTS ---
        ct = self._card(body, "読み上げ (TTS)")
        speak = ctk.CTkSwitch(ct, text="OCR後に自動で読み上げ", progress_color=PINK)
        speak.pack(anchor="w", padx=18, pady=4)
        speak.select() if cfg["tts"].get("speak_on_ocr") else speak.deselect()
        voice_names = [v["name"] for v in status["voices"]] or ["(音声なし)"]
        cur_voice = next((n for n in voice_names
                          if cfg["tts"].get("voice_match", "") and cfg["tts"]["voice_match"] in n),
                         voice_names[0])
        voice_var = ctk.StringVar(value=cur_voice)
        ctk.CTkLabel(ct, text="音声", text_color=MUTED, font=("Segoe UI", 12)).pack(anchor="w", padx=18)
        ctk.CTkOptionMenu(ct, variable=voice_var, values=voice_names,
                          fg_color=PURPLE, button_color=PURPLE_DK,
                          ).pack(fill="x", padx=18, pady=(0, 8))
        rate_val = ctk.IntVar(value=cfg["tts"].get("rate", 175))
        rate_lbl = ctk.CTkLabel(ct, text=f"速度: {rate_val.get()}", text_color=MUTED, font=("Segoe UI", 12))
        rate_lbl.pack(anchor="w", padx=18)
        ctk.CTkSlider(ct, from_=80, to=320, variable=rate_val, progress_color=PINK, button_color=PINK_DK,
                      command=lambda v: rate_lbl.configure(text=f"速度: {int(float(v))}")
                      ).pack(fill="x", padx=18, pady=(0, 14))

        # --- translate ---
        ctr = self._card(body, "翻訳 (LocalLLM)")
        llm_lbl = ctk.CTkLabel(ctr, text=("接続OK ✅" if status["llm_available"] else "未接続 ⬇"),
                               text_color=(MUTED if status["llm_available"] else PINK_DK),
                               font=("Segoe UI", 12))
        llm_lbl.pack(anchor="w", padx=18)
        tr_enabled = ctk.CTkSwitch(ctr, text="OCR後に自動翻訳", progress_color=PINK)
        tr_enabled.pack(anchor="w", padx=18, pady=4)
        tr_enabled.select() if cfg["translate"].get("enabled") else tr_enabled.deselect()
        base_entry = self._labeled_entry(ctr, "エンドポイント (OpenAI互換)", cfg["translate"]["base_url"])
        model_entry = self._labeled_entry(ctr, "モデル名", cfg["translate"]["model"])
        target_entry = self._labeled_entry(ctr, "翻訳先の言語", cfg["translate"]["target_lang"])
        ctk.CTkLabel(ctr, text="", height=4).pack()

        # --- save ---
        def save():
            patch = {
                "language": lang_var.get(),
                "model_dir": dir_entry.get().strip(),
                "auto_ocr": bool(auto_ocr.get()),
                "copy_to_clipboard": bool(copy_cb.get()),
                "show_notifications": bool(notif.get()),
                "tts": {"speak_on_ocr": bool(speak.get()),
                        "voice_match": voice_var.get(),
                        "rate": int(rate_val.get())},
                "translate": {"enabled": bool(tr_enabled.get()),
                              "base_url": base_entry.get().strip(),
                              "model": model_entry.get().strip(),
                              "target_lang": target_entry.get().strip()},
            }
            self.c.apply_settings(patch)
            self._toast(win, "保存しました 💾")

        self._pink_button(win, "設定を保存 💾", save, big=True).pack(fill="x", padx=20, pady=(4, 14))
        win.protocol("WM_DELETE_WINDOW",
                     lambda: (setattr(self, "_settings_win", None), win.destroy()))
        self._focus(win)

    def _labeled_entry(self, parent, label, value) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, text_color=MUTED, font=("Segoe UI", 12)).pack(anchor="w", padx=18)
        e = ctk.CTkEntry(parent, height=34, corner_radius=10)
        e.insert(0, value or "")
        e.pack(fill="x", padx=18, pady=(0, 8))
        return e

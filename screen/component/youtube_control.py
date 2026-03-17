import os
# ===== X11 SAFE ENV =====
os.environ["XLIB_SKIP_ARGB_VISUALS"] = "1"
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"

import tkinter as tk
import threading
import time
import webbrowser
import speech_recognition as sr


class YouTubeControl:
    def __init__(self, app):
        self.app = app

        # Status UI
        self.status_frame = None
        self.status_text = None

        # Log control
        self.last_log_time = 0.0
        self.log_interval = 0.1  # 100ms

    # ==================================================
    # OPEN YOUTUBE MODE
    # ==================================================
    def open_youtube_mode(self):
        self._clear_root()

        tk.Button(
            self.app.root,
            text="Tim kiem YouTube bang giong noi",
            width=35,
            height=2,
            command=self.ask_youtube_question_thread
        ).pack(pady=10)

        tk.Button(
            self.app.root,
            text="Quay lai man hinh chinh",
            width=35,
            height=2,
            command=self.exit_youtube_mode
        ).pack(pady=10)

        self._create_status_box()
        self.log_message("Da vao che do YouTube")

    # ==================================================
    # STATUS BOX (SAFE FONT)
    # ==================================================
    def _create_status_box(self):
        self.status_frame = tk.LabelFrame(
            self.app.root,
            text="Trang thai he thong"
        )
        self.status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.status_text = tk.Text(
            self.status_frame,
            height=8,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("DejaVu Sans Mono", 10)
        )
        self.status_text.pack(fill=tk.BOTH, expand=True)

    # ==================================================
    # VOICE THREAD
    # ==================================================
    def ask_youtube_question_thread(self):
        threading.Thread(
            target=self.ask_youtube_question,
            daemon=True
        ).start()

    def ask_youtube_question(self):
        recognizer = sr.Recognizer()

        try:
            self.log_message("Khoi dong microphone")

            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self.log_message("Dang lang nghe")
                audio = recognizer.listen(
                    source,
                    timeout=5,
                    phrase_time_limit=5
                )

            self.log_message("Dang nhan dang giong noi")
            query = recognizer.recognize_google(audio, language="vi-VN")
            self.log_message("Noi: " + query)

            self._open_youtube(query)

        except sr.WaitTimeoutError:
            self.log_message("Khong nghe thay giong noi", "WARN")
        except sr.UnknownValueError:
            self.log_message("Khong nhan dang duoc giong noi", "WARN")
        except sr.RequestError as e:
            self.log_message("Loi Google Speech: " + str(e), "ERROR")
        except Exception as e:
            self.log_message("Loi he thong: " + str(e), "ERROR")

    # ==================================================
    # OPEN YOUTUBE
    # ==================================================
    def _open_youtube(self, query):
        try:
            url = "https://www.youtube.com/results?search_query=" + query.replace(" ", "+")
            webbrowser.open(url)
            self.log_message("Da mo YouTube voi tu khoa: " + query)
        except Exception as e:
            self.log_message("Loi mo YouTube: " + str(e), "ERROR")

    # ==================================================
    # EXIT MODE
    # ==================================================
    def exit_youtube_mode(self):
        self._clear_root()
        self.app.create_main_widgets()

    # ==================================================
    # SAFE LOGGER (ANTI X11 CRASH)
    # ==================================================
    def log_message(self, message, level="INFO"):
        now = time.time()
        if now - self.last_log_time < self.log_interval:
            return
        self.last_log_time = now

        if not self.status_text:
            return

        def _log():
            if not self.status_text.winfo_exists():
                return

            self.status_text.config(state=tk.NORMAL)

            if level == "ERROR":
                prefix = "[ERROR] "
            elif level == "WARN":
                prefix = "[WARN ] "
            else:
                prefix = "[INFO ] "

            self.status_text.insert(tk.END, prefix + message + "\n")
            self.status_text.see(tk.END)
            self.status_text.config(state=tk.DISABLED)

        self.app.root.after(0, _log)

    # ==================================================
    # CLEAR ROOT (NO pack_forget)
    # ==================================================
    def _clear_root(self):
        for w in self.app.root.winfo_children():
            w.destroy()


import threading
import speech_recognition as sr
import requests
import os
import time
from datetime import datetime
import tkinter as tk

# Giảm log rác VLC
os.environ.setdefault("VLC_VERBOSE", "-1")
import vlc

from unidecode import unidecode
from openai import OpenAI

# ==============================
# OPENAI KEY
# ==============================
client = OpenAI(
    api_key=""
)


class VoiceAssistant:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.running = False
        self.recognizer = sr.Recognizer()

        # Wake word (chưa dùng)
        self.wake_word = "robot"

        # Giảm nhiễu nền
        self.noise_reduce = True

        # Chống double-listen
        self.last_text = ""
        self.last_text_time = 0.0

        # 🔒 CỜ CHỐNG TỰ NÓI – TỰ NGHE
        self.is_speaking = False

        # Câu trả lời offline
        self.custom_responses = {
            "ban la ai": "Tôi là robot hình người được chế tạo bởi trường trung học phổ thông b nguyễn khuyến",
            "chao ban": "Xin chào, bạn cần tôi giúp gì?",
            "toi muon biet thong tin ve truong trung hoc pho thong b nguyen khuyen": " trường phổ thông b nguyễn khuyến được thành lập năm 1976",
            "hom nay la ngay gi": "hôm nay là ngaỳ diễn ra cuộc thi khoa học kĩ thuật tỉnh ninh bình",
            "ban dang o dau": "tôi đang ở đại học hoa lư tỉnh ninh bình",
            "hom nay la ngay bao nhieu": "hôm nay là ngày mùng 6 tháng 1 năm 2026",
            "bay gio la may gio": f"Bây giờ là {datetime.now().strftime('%H:%M:%S')}",
        }

        self.thread = None

    # ==============================
    # GIAO DIỆN
    # ==============================
    def show_voice_assistant_ui(self):
        for w in self.root.winfo_children():
            w.pack_forget()

        tk.Button(
            self.root,
            text="Bắt đầu trợ lý (Voice)",
            command=self.start_assistant,
            width=40,
            height=2,
            font=("Helvetica", 16, "bold"),
        ).pack(pady=10)

        tk.Button(
            self.root,
            text="Dừng trợ lý",
            command=self.stop_assistant,
            width=40,
            height=2,
            font=("Helvetica", 16, "bold"),
        ).pack(pady=10)

        frame = tk.Frame(self.root)
        frame.pack(pady=10)

        tk.Label(frame, text="Nhập câu hỏi:", font=("Helvetica", 12)).pack(
            side=tk.LEFT, padx=5
        )

        self.text_input = tk.Entry(frame, width=45, font=("Helvetica", 12))
        self.text_input.pack(side=tk.LEFT, padx=5)

        tk.Button(
            frame,
            text="Gửi",
            width=10,
            font=("Helvetica", 12, "bold"),
            command=self.on_text_submit,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            self.root,
            text="Quay lại menu",
            command=self.app.show_mode_selection,
            width=40,
            height=2,
            font=("Helvetica", 16),
        ).pack(pady=10)

        self.text_display = tk.Text(
            self.root, height=17, width=90, state="disabled", font=("Helvetica", 12)
        )
        self.text_display.pack(pady=20)

    def log(self, msg: str):
        print("[LOG]", msg)
        try:
            self.text_display.config(state="normal")
            self.text_display.insert(tk.END, msg + "\n")
            self.text_display.see(tk.END)
            self.text_display.config(state="disabled")
        except:
            pass

    # ==============================
    # GỬI CÂU HỎI BẰNG TEXT
    # ==============================
    def on_text_submit(self):
        question = self.text_input.get().strip()
        if not question:
            return

        self.log("Bạn (gõ): " + question)
        answer = self.ask_ai(question)
        self.speak(answer)
        self.text_input.delete(0, tk.END)

    # ==============================
    # NHẬN GIỌNG NÓI (ĐÃ FIX)
    # ==============================
    def listen(self):
        # 🔒 KHÔNG NGHE KHI ĐANG NÓI
        if self.is_speaking:
            time.sleep(0.2)
            return None

        try:
            with sr.Microphone() as source:
                if self.noise_reduce:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.6)

                audio = self.recognizer.listen(source, phrase_time_limit=6)

            text = self.recognizer.recognize_google(audio, language="vi-VN")
            if not text:
                return None

            text = text.strip()
            now = time.time()

            if text == self.last_text and (now - self.last_text_time) < 1.5:
                return None

            self.last_text = text
            self.last_text_time = now

            self.log("Bạn nói: " + text)
            return text

        except Exception as e:
            return None

    # ==============================
    # ASK OPENAI
    # ==============================
    def ask_ai(self, question):
        normalized = unidecode(question.lower())

        for k, v in self.custom_responses.items():
            if k in normalized:
                return v

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý ảo UNETI, trả lời ngắn gọn bằng tiếng Việt."},
                    {"role": "user", "content": question},
                ],
            )
            return response.choices[0].message.content

        except Exception as e:
            return "Xin lỗi, tôi gặp lỗi khi xử lý."

    # ==============================
    # TTS FPT (ĐÃ FIX)
    # ==============================
    def speak(self, text):
        self.is_speaking = True  # 🔒 KHÓA MICRO
        self.log("Trợ lý: " + text)

        api_key = "t4YGHw5diznulzMAlJ32M3lWjshwNY35"
        if not api_key:
            self.is_speaking = False
            return

        try:
            url = "https://api.fpt.ai/hmi/tts/v5"
            headers = {
                "api-key": api_key,
                "voice": "leminh",
            }

            r = requests.post(url, data=text.encode("utf-8"), headers=headers)
            if r.status_code != 200:
                self.is_speaking = False
                return

            data = r.json()
            audio_url = data.get("async", "")
            if not audio_url:
                self.is_speaking = False
                return

            for _ in range(20):
                resp = requests.get(audio_url)
                if resp.status_code == 200:
                    break
                time.sleep(0.5)
            else:
                self.is_speaking = False
                return

            player = vlc.MediaPlayer(audio_url)
            player.play()

            time.sleep(0.5)
            while player.is_playing():
                time.sleep(0.1)

            player.stop()

        except Exception as e:
            pass

        self.is_speaking = False  # 🔓 MỞ MICRO

    # ==============================
    # BẬT / TẮT TRỢ LÝ
    # ==============================
    def start_assistant(self):
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        self.log("Trợ lý Voice đã bật.")

    def stop_assistant(self):
        self.running = False
        self.log("Đã dừng trợ lý Voice.")

    def loop(self):
        while self.running:
            text = self.listen()
            if not text:
                continue

            answer = self.ask_ai(text)
            self.speak(answer)


import tkinter as tk
import sounddevice as sd
import speech_recognition as sr
from scipy.io.wavfile import write
import threading
import time
import difflib
import unicodedata


class VoiceControl:
    def __init__(self, main_app, serial_conn, return_to_main):
        self.main_app = main_app
        self.serial_conn = serial_conn
        self.is_listening = False
        self.command_to_send = None
        self.sending_command = False
        self.return_to_main = return_to_main

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def activate(self):
        self.main_app.root.withdraw()
        self.voice_control_window = tk.Toplevel()
        self.voice_control_window.title("Voice Control Panel")
        self.voice_control_window.geometry("1000x1000")
        self.voice_control_window.protocol("WM_DELETE_WINDOW", self.close_and_return)

        frame = tk.Frame(self.voice_control_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Lệnh nhận được", font=("Helvetica", 12, "bold")).grid(row=0, column=0, padx=10, pady=5)
        self.command_log = tk.Text(frame, height=15, width=45, state='disabled', font=("Helvetica", 10))
        self.command_log.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        tk.Label(frame, text="Tín hiệu gửi đi", font=("Helvetica", 12, "bold")).grid(row=0, column=1, padx=10, pady=5)
        self.signal_log = tk.Text(frame, height=15, width=45, state='disabled', font=("Helvetica", 10))
        self.signal_log.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")

        button_frame = tk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)

        self.listen_button = tk.Button(
            button_frame, text="Bắt đầu lắng nghe",
            command=self.start_listening, width=20, height=2, font=("Helvetica", 12)
        )
        self.listen_button.grid(row=0, column=0, padx=10, pady=5)

        self.stop_button = tk.Button(
            button_frame, text="Dừng lắng nghe",
            command=self.stop_listening, width=20, height=2, font=("Helvetica", 12)
        )
        self.stop_button.grid(row=0, column=1, padx=10, pady=5)

        self.back_button = tk.Button(
            button_frame, text="Quay lại",
            command=self.close_and_return, width=20, height=2, font=("Helvetica", 12)
        )
        self.back_button.grid(row=1, column=0, columnspan=2, pady=10)

        threading.Thread(target=self.send_uart_continuous, daemon=True).start()

    def close_and_return(self):
        self.log_signal("Thoát Voice Control (UART vẫn hoạt động).")
        self.voice_control_window.destroy()
        self.main_app.root.deiconify()

    def start_listening(self):
        self.is_listening = True
        self.log_command("Voice Control: Bắt đầu lắng nghe...")
        threading.Thread(target=self.listen_for_command, daemon=True).start()

    def stop_listening(self):
        self.is_listening = False
        self.log_command("Voice Control: Dừng lắng nghe.")

    def record_audio(self, filename='output.wav', duration=5, fs=44100):
        self.log_command("Voice Control: Bắt đầu ghi âm...")
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        write(filename, fs, recording)
        self.log_command("Voice Control: Ghi âm hoàn tất.")
        return filename

    def recognize_speech(self):
        self.log_command("Voice Control: Đang nhận diện giọng nói...")
        try:
            with sr.AudioFile('output.wav') as source:
                audio = self.recognizer.record(source)
            command = self.recognizer.recognize_google(audio, language="vi-VN")
            self.log_command(f"Nhận diện lệnh: {command}")
            return command.lower()
        except sr.UnknownValueError:
            self.log_command("Không thể nhận diện giọng nói.")
        except sr.RequestError as e:
            self.log_command(f"Lỗi kết nối với Google API: {e}")
        return None

    # ================== CHỈ SỬA PHẦN NÀY ==================
    def send_uart_continuous(self):
        while True:
            if self.sending_command and self.serial_conn and self.serial_conn.is_open and self.command_to_send:
                try:
                    self.serial_conn.write(self.command_to_send.encode())
                    self.log_signal(f"Đã gửi lệnh qua UART (1 lần): {self.command_to_send}")

                    # 👉 QUAN TRỌNG: gửi xong thì dừng
                    self.sending_command = False

                except Exception as e:
                    self.log_signal(f"Lỗi khi gửi dữ liệu qua UART: {e}")
                    self.sending_command = False
            time.sleep(0.05)
    # =====================================================

    def listen_for_command(self):
        while self.is_listening:
            self.record_audio()
            command = self.recognize_speech()
            if command:
                self.process_command(command)
            time.sleep(0.1)

    def remove_tone(self, text):
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )

    def process_command(self, command):
        command_map = {
            'chào': "B4",
            'múa': "B1",
            'bắt tay': "B6",
            'lấy vật': "B2",
            'cầm vật': "B2",
            'con vật': "B2",
            'tạm biệt': "B1",
            'quay trái': "B6",
            'nhìn thẳng': "B7"
        }
        command_no_tone = self.remove_tone(command)
        best_match = None
        best_score = 0

        for key in command_map:
            key_no_tone = self.remove_tone(key)
            score = difflib.SequenceMatcher(None, key_no_tone, command_no_tone).ratio()
            if score > best_score:
                best_score = score
                best_match = key

        if best_match and best_score >= 0.7:
            self.command_to_send = command_map[best_match]
            self.sending_command = True
            self.log_command(
                f"Lệnh gần đúng: {best_match} (score: {best_score:.2f}) → gửi {self.command_to_send}"
            )
        else:
            self.log_command(f"Lệnh không hợp lệ hoặc không đủ giống: {command}")

    def log_command(self, message):
        self.command_log.config(state='normal')
        self.command_log.insert(tk.END, message + "\n")
        self.command_log.see(tk.END)
        self.command_log.config(state='disabled')

    def log_signal(self, message):
        self.signal_log.config(state='normal')
        self.signal_log.insert(tk.END, message + "\n")
        self.signal_log.see(tk.END)
        self.signal_log.config(state='disabled')


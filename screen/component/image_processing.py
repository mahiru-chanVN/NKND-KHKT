import cv2
import face_recognition
import threading
import time
import os
import pickle
import numpy as np
import requests
import vlc
import tkinter as tk


class ImageProcessing:
    def __init__(self, app, serial_conn=None):
        self.app = app
        self.serial_conn = serial_conn

        # ===== FLAGS =====
        self.face_recognition_running = False
        self.testing_camera = False
        self.is_speaking = False
        self.greet_enabled = True

        # ===== GREETING CONTROL =====
        self.last_greet_time = {}
        self.greet_interval = 10
        self.audio_lock = threading.Lock()

        # ===== FPT TTS =====
        self.api_key = "t4YGHw5diznulzMAlJ32M3lWjshwNY35"
        self.cache_dir = "/tmp/fpt_tts_cache"
        os.makedirs(self.cache_dir, exist_ok=True)

        # ===== FACE DB =====
        self.db_path = os.path.join(os.path.dirname(__file__), "face_db.pkl")
        self.known_encodings = []
        self.known_names = []
        self.load_face_db()

        # ===== PRELOAD TTS =====
        self.preload_tts(["Đức Lương", "Đình Kiên", "Ngọc Anh"])


    # ==================================================
    # LOAD FACE DATABASE
    # ==================================================
    def load_face_db(self):
        if not os.path.exists(self.db_path):
            print("⚠ Không tìm thấy face_db.pkl")
            return

        with open(self.db_path, "rb") as f:
            data = pickle.load(f)

        self.known_encodings = data.get("encodings", [])
        self.known_names = data.get("names", [])

        print(f"✅ Đã load {len(self.known_names)} khuôn mặt.")


    # ==================================================
    # IMAGE PROCESSING MODE
    # ==================================================
    def image_processing_mode(self):
        if self.testing_camera:
            print("⚠ Đang test camera, vui lòng tắt trước.")
            return

        if not self.face_recognition_running:
            self.face_recognition_running = True
            threading.Thread(target=self.process_video, daemon=True).start()

        for widget in self.app.root.winfo_children():
            widget.pack_forget()

        tk.Button(self.app.root, text="Thoát chế độ xử lý ảnh",
                  command=self.stop_image_processing_mode,
                  width=25).pack(pady=10)

        tk.Button(self.app.root, text="Quay lại màn hình chính",
                  command=self.hide_image_processing_ui,
                  width=25).pack(pady=10)

        tk.Button(self.app.root, text="Tắt chế độ chào hỏi",
                  command=self.disable_greeting_mode,
                  width=25).pack(pady=10)

        tk.Button(self.app.root, text="Bật chế độ chào hỏi",
                  command=self.enable_greeting_mode,
                  width=25).pack(pady=10)


    def stop_image_processing_mode(self):
        self.face_recognition_running = False
        if hasattr(self.app, "show_mode_selection"):
            self.app.show_mode_selection()


    def hide_image_processing_ui(self):
        self.face_recognition_running = False
        for widget in self.app.root.winfo_children():
            widget.pack_forget()
        if hasattr(self.app, "show_mode_selection"):
            self.app.show_mode_selection()


    def disable_greeting_mode(self):
        self.greet_enabled = False
        print("Đã tắt chế độ chào hỏi.")


    def enable_greeting_mode(self):
        self.greet_enabled = True
        print("Đã bật chế độ chào hỏi.")


    # ==================================================
    # FACE RECOGNITION PROCESS
    # ==================================================
    def process_video(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("⚠ Không mở được camera")
            return

        while self.face_recognition_running:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)

            # 🔥 Resize 1/4 để tăng tốc
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            # Detect + Encode
            boxes = face_recognition.face_locations(rgb_small, model="hog")
            encodings = face_recognition.face_encodings(rgb_small, boxes)

            now = time.time()

            for (top, right, bottom, left), encoding in zip(boxes, encodings):

                name = self.recognize_face(encoding)

                # Scale lại box
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)

                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.putText(frame, name, (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

                # Greeting
                if name != "Unknown" and not self.is_speaking and self.greet_enabled:
                    last = self.last_greet_time.get(name, 0)
                    if now - last >= self.greet_interval:
                        self.last_greet_time[name] = now
                        threading.Thread(
                            target=self.speak,
                            args=(f"Xin chào {name}",),
                            daemon=True
                        ).start()

            cv2.imshow("Face Recognition", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()
        self.face_recognition_running = False


    # ==================================================
    # RECOGNIZE
    # ==================================================
    def recognize_face(self, encoding, threshold=0.5):
        if not self.known_encodings:
            return "Unknown"

        distances = face_recognition.face_distance(
            self.known_encodings,
            encoding
        )

        min_dist = np.min(distances)
        idx = np.argmin(distances)

        if min_dist < threshold:
            return self.known_names[idx]
        else:
            return "Unknown"


    # ==================================================
    # TTS
    # ==================================================
    def _cache_file(self, text):
        return os.path.join(self.cache_dir, f"{abs(hash(text))}.mp3")


    def speak(self, text):
        with self.audio_lock:
            self.is_speaking = True
            try:
                cache_file = self._cache_file(text)

                if not os.path.exists(cache_file):
                    self.download_tts(text, cache_file)

                if os.path.exists(cache_file):
                    player = vlc.MediaPlayer(cache_file)
                    player.play()
                    while player.get_state() not in (
                            vlc.State.Ended,
                            vlc.State.Error):
                        time.sleep(0.05)

            finally:
                self.is_speaking = False


    def download_tts(self, text, cache_file):
        try:
            url = "https://api.fpt.ai/hmi/tts/v5"
            headers = {
                "api-key": self.api_key,
                "voice": "leminh",
                "speed": "-1",
                "format": "mp3"
            }
            r = requests.post(url, data=text.encode("utf-8"), headers=headers, timeout=10)
            js = r.json()
            audio_url = js.get("async") or js.get("data", {}).get("url")

            if audio_url:
                os.system(f"wget -q -O {cache_file} '{audio_url}'")
        except Exception as e:
            print("TTS lỗi:", e)


    def preload_tts(self, names):
        for name in names:
            text = f"Xin chào {name}"
            cache_file = self._cache_file(text)
            if not os.path.exists(cache_file):
                self.download_tts(text, cache_file)


    # ==================================================
    # TEST CAMERA
    # ==================================================
    def test_camera(self):
        if self.testing_camera:
            return
        self.testing_camera = True
        threading.Thread(target=self._run_test_camera, daemon=True).start()


    def stop_test_camera(self):
        self.testing_camera = False


    def _run_test_camera(self):
        cap = cv2.VideoCapture(0)
        while self.testing_camera:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            cv2.imshow("Test Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        cap.release()
        cv2.destroyAllWindows()
        self.testing_camera = False

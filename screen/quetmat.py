import cv2
import mediapipe as mp
import os
import pickle
import numpy as np
import tkinter as tk
from tkinter import simpledialog, ttk, messagebox
from PIL import Image, ImageTk
import face_recognition

DB_PATH = "face_db.pkl"
TOTAL_SAMPLES = 50


# ================= IMAGE PROCESSING =================
class ImageProcessing:
    def __init__(self):
        self.db_path = DB_PATH
        self.known_encodings = []
        self.known_names = []
        self.load_face_db()

        self.face_detector = mp.solutions.face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.6
        )

    def load_face_db(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "rb") as f:
                data = pickle.load(f)
                self.known_encodings = data.get("encodings", [])
                self.known_names = data.get("names", [])
        else:
            self.known_encodings = []
            self.known_names = []

    def save_db(self):
        with open(self.db_path, "wb") as f:
            pickle.dump({
                "encodings": self.known_encodings,
                "names": self.known_names
            }, f)

    def encode_face(self, frame, box):
        x, y, w, h = box
        h_img, w_img, _ = frame.shape

        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(w_img, x + w), min(h_img, y + h)

        face = frame[y1:y2, x1:x2]
        if face.size == 0:
            return None

        rgb_face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb_face)

        if len(encodings) > 0:
            return encodings[0]
        return None

    def delete_person(self, name):
        if name not in self.known_names:
            return False

        new_encodings = []
        new_names = []

        for enc, n in zip(self.known_encodings, self.known_names):
            if n != name:
                new_encodings.append(enc)
                new_names.append(n)

        self.known_encodings = new_encodings
        self.known_names = new_names
        self.save_db()
        return True


# ================= GUI =================
class FaceEnrollmentGUI:
    def __init__(self, iproc: ImageProcessing):
        self.iproc = iproc
        self.collecting = False
        self.person_name = ""
        self.samples = []

        self.cap = cv2.VideoCapture(0)

        self.root = tk.Tk()
        self.root.title("Face Enrollment + Manager")
        self.root.geometry("950x500")
        self.root.resizable(False, False)

        FONT = ("Arial", 11)

        # ===== LEFT: CAMERA =====
        left_frame = tk.Frame(self.root)
        left_frame.pack(side="left", padx=10)

        self.camera_frame = tk.Label(left_frame, width=640, height=360, bg="black")
        self.camera_frame.pack(pady=5)

        status_frame = tk.Frame(left_frame)
        status_frame.pack(pady=2)

        self.name_label = tk.Label(status_frame, text="Tên: ---", font=FONT)
        self.name_label.pack(side="left", padx=6)

        self.count_label = tk.Label(status_frame, text="Mẫu: 0/50", font=FONT)
        self.count_label.pack(side="left", padx=6)

        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Start", width=9, command=self.start_collect).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Stop", width=9, command=self.stop_collect).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Exit", width=9, command=self.exit_app).pack(side="left", padx=3)

        # ===== RIGHT: DATABASE MANAGER =====
        right_frame = tk.Frame(self.root)
        right_frame.pack(side="right", padx=10, fill="y")

        tk.Label(right_frame, text="Danh sách người đã lưu", font=("Arial", 12, "bold")).pack(pady=5)

        self.listbox = tk.Listbox(right_frame, width=30, height=20)
        self.listbox.pack()

        self.count_people_label = tk.Label(right_frame, text="Tổng số: 0")
        self.count_people_label.pack(pady=5)

        ttk.Button(right_frame, text="Xóa người được chọn", command=self.delete_selected).pack(pady=5)

        self.refresh_listbox()

        self.update_gui()
        self.root.mainloop()

    # ================= ENROLL =================
    def start_collect(self):
        name = simpledialog.askstring("Tên", "Nhập tên người:")
        if not name:
            return

        self.person_name = name.strip()
        self.samples = []
        self.collecting = True
        self.update_status()

    def stop_collect(self):
        if not self.collecting:
            return

        if self.person_name and len(self.samples) > 0:
            avg = np.mean(self.samples, axis=0)
            self.iproc.known_encodings.append(avg)
            self.iproc.known_names.append(self.person_name)
            self.iproc.save_db()
            print(f"💾 Đã lưu dữ liệu cho {self.person_name}")

        self.collecting = False
        self.samples = []
        self.refresh_listbox()
        self.update_status()

    # ================= DATABASE MANAGER =================
    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        unique_names = sorted(set(self.iproc.known_names))

        for name in unique_names:
            self.listbox.insert(tk.END, name)

        self.count_people_label.config(text=f"Tổng số: {len(unique_names)}")

    def delete_selected(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("Chọn người", "Hãy chọn một người để xóa")
            return

        name = self.listbox.get(selected[0])

        confirm = messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa {name}?")
        if confirm:
            self.iproc.delete_person(name)
            self.refresh_listbox()

    # ================= UI =================
    def exit_app(self):
        self.cap.release()
        self.root.destroy()

    def update_status(self):
        count = len(self.samples) if self.collecting else 0
        self.name_label.config(text=f"Tên: {self.person_name or '---'}")
        self.count_label.config(text=f"Mẫu: {count}/{TOTAL_SAMPLES}")

    # ================= CAMERA LOOP =================
    def update_gui(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            detect_results = self.iproc.face_detector.process(rgb)

            if detect_results.detections:
                for det in detect_results.detections:
                    box = det.location_data.relative_bounding_box
                    x = int(box.xmin * w)
                    y = int(box.ymin * h)
                    bw = int(box.width * w)
                    bh = int(box.height * h)

                    cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)

                    if self.collecting and len(self.samples) < TOTAL_SAMPLES:
                        vec = self.iproc.encode_face(frame, (x, y, bw, bh))
                        if vec is not None:
                            self.samples.append(vec)
                            self.update_status()

                    if self.collecting and len(self.samples) >= TOTAL_SAMPLES:
                        self.stop_collect()

            frame = cv2.resize(frame, (640, 360))
            img = ImageTk.PhotoImage(Image.fromarray(frame))
            self.camera_frame.imgtk = img
            self.camera_frame.configure(image=img)

        self.root.after(15, self.update_gui)


# ================= MAIN =================
if __name__ == "__main__":
    iproc = ImageProcessing()
    FaceEnrollmentGUI(iproc)

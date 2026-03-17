import os
import sys
import glob
import json
import threading
import time
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import serial
import traceback  # <-- THÊM DÒNG NÀY

# Thử import SpeechRecognition cho chức năng test mic
try:
    import speech_recognition as sr
except ImportError:
    sr = None
5
# Thư mục gốc của project (thư mục chứa main.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)  # Đảm bảo import được các module cùng thư mục

from voice_assistant import VoiceAssistant
from music_control import MusicControl
from youtube_control import YouTubeControl
from image_processing import ImageProcessing
from voice_control import VoiceControl


class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Assistant Control Panel")

        # MÀN HÌNH 7 INCH → thường 1024x600
        # Có thể đổi thành "800x480" nếu LCD của anh độ phân giải khác
        self.root.geometry("1024x600")
        self.root.minsize(800, 480)

        self.show_image_processing_mode_button = True

        # UART hiện tại
        
        self.serial_conn = None      # UART cho Image
        self.serial_conn1 = None     # UART cho Music + Voice
        self.image_port_name = None
        self.music_port_name = None

        # nơi lưu config
        self.uart_config_path = os.path.join(BASE_DIR, "uart_config.json")

        # background
        self.background_label = None
        self.background_image = None
        self.add_background_image()

        # text log chính (giảm chiều cao cho vừa 600px)
        self.text_display = tk.Text(
            self.root,
            height=9,
            width=120,
            state='disabled',
            font=("Helvetica", 11)
        )
        self.text_display.pack(pady=5, padx=10, fill="x")

        # Module KHÔNG dùng UART → tạo luôn
        self.voice_assistant = VoiceAssistant(self)
        self.youtube_control = YouTubeControl(self)

        # Module có dùng UART → tạo sau khi chọn cổng
        self.music_control = None
        self.image_processing = None
        self.voice_control = None

        # Theo dõi danh sách cổng hiện có
        self.current_ports = self.scan_ports()
        threading.Thread(target=self.usb_watcher, daemon=True).start()

        # Khởi tạo UART + UI
        self.init_uart_and_ui()

    # ================== KHỞI TẠO UART ==================
    def init_uart_and_ui(self):
        """Lần đầu: hỏi chọn UART. Lần sau: tự load config nếu hợp lệ."""
        ports = self.scan_ports()
        cfg = self.load_uart_config()

        if cfg:
            img = cfg.get("image_port")
            mus = cfg.get("music_port")
            # Nếu 2 cổng này vẫn tồn tại → dùng luôn
            if img in ports and mus in ports:
                self.image_port_name = img
                self.music_port_name = mus

                self.serial_conn = self.setup_serial(img, 'image_processing')
                self.serial_conn1 = self.setup_serial(mus, 'music/voice')

                self.create_modules_after_uart_choice(self.serial_conn,
                                                      self.serial_conn1)
                self.create_main_widgets()
                self.log_message(f"Đã load cấu hình UART từ file: image={img}, music/voice={mus}")
                return

        # Nếu chưa có config hoặc cổng không còn tồn tại → yêu cầu chọn lại
        self.choose_uart_ports()

    # ================== LƯU / LOAD CẤU HÌNH UART ====================
    def load_uart_config(self):
        if not os.path.exists(self.uart_config_path):
            return None
        try:
            with open(self.uart_config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.log_message(f"Lỗi đọc uart_config.json: {e}")
            return None

    def save_uart_config(self, image_port, music_port):
        data = {
            "image_port": image_port,
            "music_port": music_port
        }
        try:
            with open(self.uart_config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.log_message(f"Đã lưu cấu hình UART: image={image_port}, music/voice={music_port}")
        except Exception as e:
            self.log_message(f"Lỗi ghi uart_config.json: {e}")

    # ================== QUÉT & THEO DÕI CỔNG USB ====================
    def scan_ports(self):
        """Trả về danh sách cổng serial hiện có."""
        if sys.platform.startswith("linux"):
            ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        elif sys.platform.startswith("win"):
            ports = [f"COM{i}" for i in range(1, 21)]
        else:
            ports = []
        return sorted(ports)

    def usb_watcher(self):
        """Luôn chạy nền để phát hiện cắm/rút USB UART."""
        while True:
            ports = self.scan_ports()
            if ports != self.current_ports:
                added = [p for p in ports if p not in self.current_ports]
                removed = [p for p in self.current_ports if p not in ports]

                if added:
                    self.log_message(f"Phát hiện UART mới: {', '.join(added)}")
                if removed:
                    self.log_message(f"UART bị rút: {', '.join(removed)}")

                self.current_ports = ports
            time.sleep(2)

    # ================== UI CHỌN / CẤU HÌNH UART =====================
    def choose_uart_ports(self):
        """Cửa sổ chọn UART (dùng được cả lúc khởi động, cả lúc cấu hình lại)."""
        ports = self.scan_ports()

        if not ports:
            messagebox.showwarning(
                "UART",
                "Không tìm thấy cổng UART nào! Các chức năng dùng UART sẽ không hoạt động."
            )
            self.create_modules_after_uart_choice(None, None)
            self.create_main_widgets()
            return

        self.uart_window = tk.Toplevel(self.root)
        self.uart_window.title("Cấu hình UART")
        self.uart_window.geometry("480x320")
        self.uart_window.grab_set()

        tk.Label(self.uart_window, text="UART cho XỬ LÝ ẢNH:",
                 font=("Helvetica", 12)).pack(pady=5)
        self.image_uart_var = tk.StringVar()

        # gợi ý mặc định
        default_img = self.image_port_name if self.image_port_name in ports else ports[0]
        self.image_uart_var.set(default_img)
        tk.OptionMenu(self.uart_window, self.image_uart_var, *ports).pack(pady=5)

        tk.Label(self.uart_window, text="UART cho NHẠC + GIỌNG NÓI:",
                 font=("Helvetica", 12)).pack(pady=5)
        self.music_uart_var = tk.StringVar()
        if self.music_port_name in ports:
            default_mus = self.music_port_name
        else:
            default_mus = ports[1] if len(ports) > 1 else ports[0]
        self.music_uart_var.set(default_mus)
        tk.OptionMenu(self.uart_window, self.music_uart_var, *ports).pack(pady=5)

        # Nút test UART
        frame_btn = tk.Frame(self.uart_window)
        frame_btn.pack(pady=10)

        tk.Button(frame_btn, text="Test UART Xử lý ảnh",
                  command=lambda: self.test_uart(self.image_uart_var.get()),
                  width=18).grid(row=0, column=0, padx=5)

        tk.Button(frame_btn, text="Test UART Nhạc/Voice",
                  command=lambda: self.test_uart(self.music_uart_var.get()),
                  width=18).grid(row=0, column=1, padx=5)

        tk.Button(self.uart_window, text="Lưu & Áp dụng",
                  command=self.apply_uart_choice, width=20).pack(pady=10)

    def apply_uart_choice(self):
        image_port = self.image_uart_var.get()
    ort = self.music_uart_var.get()
        # Đóng cổng cũ nếu có
        if self.serial_conn and self.serial_copen:
            self.serial_conn.close()
        if self.serial_conn1 and self.serial_conn1.is_open:
            self.serial_conn1.close()

        # Kết nối cổng mới
        self.serial_conn = self.setup_serial(image_port, 'image_processing') if image_port else None
        self.serial_conn1 = self.setup_serial(music_port, 'music/voice') if music_port else None

        self.image_port_name = image_port
        self.music_port_name = music_port

        # Lưu config
        self.save_uart_config(image_port, music_port)

        # Tạo/ cập nhật các module phụ thuộc UART
        self.create_modules_after_uart_choice(self.serial_conn, self.serial_conn1)

        self.uart_window.destroy()
        self.create_main_widgets()

    def test_uart(self, port):
        """Gửi chuỗi TEST qua cổng được chọn để kiểm tra."""
        if not port:
            messagebox.showinfo("Test UART", "Chưa chọn cổng UART.")
            return
        try:
            self.log_message(f"[UART-TEST] Đang test UART trên {port}...")
            ser = serial.Serial(port=port, baudrate=115200, timeout=0.5)
            self.log_message(f"[UART-TEST] Đã mở {port} (baud=115200, timeout=0.5)")
            sent = ser.write(b"TEST\n")
            ser.flush()
            self.log_message(f"[UART-TEST] Đã gửi {sent} byte: b'TEST\\n'")
            time.sleep(0.1)
            data = ser.read(64)
            ser.close()
            self.log_message(f"[UART-TEST] Đã đóng {port}")
            if data:
                self.log_message(f"[UART-TEST] UART {port} trả về: {data!r}")
            else:
                self.log_message(f"[UART-TEST] Đã gửi TEST trên {port} (không nhận được phản hồi).")
        except Exception as e:
            self.log_message(f"[UART-TEST] Lỗi test UART {port}: {e}")

    def open_uart_config_from_menu(self):
        """Mở lại cửa sổ cấu hình UART từ menu chính."""
        self.choose_uart_ports()

    # ================== TẠO MODULE PHỤ THUỘC UART ===================
    def create_modules_after_uart_choice(self, serial_image, serial_music_voice):
        """Tạo / cập nhật các module dùng UART."""
        self.image_processing = ImageProcessing(self, serial_image)
        self.music_control = MusicControl(self, serial_music_voice)
        self.voice_control = VoiceControl(self, serial_music_voice, self.show_mode_selection)

    # ================== SERIAL HELPER ===============================
    def setup_serial(self, port, purpose):
        try:
            serial_conn = serial.Serial(port=port, baudrate=115200, timeout=1)
            self.log_message(f"[UART-SETUP] Kết nối {port} OK cho {purpose}")
            return serial_conn
        except serial.SerialException as e:
            self.log_message(f"[UART-SETUP] Lỗi kết nối UART ({purpose}) {port}: {e}")
            return None

    # ================== UI MENU CHÍNH ===============================
    def add_background_image(self):
        try:
            image_path = os.path.join(BASE_DIR, "anh", "background.jpg")
            image = Image.open(image_path)

            # Lấy kích thước cửa sổ hiện tại để scale cho hợp màn 7 inch
            try:
                w = self.root.winfo_screenwidth()
                h = self.root.winfo_screenheight()
                if w < 400 or h < 300:  # trường hợp tk chưa init xong
                    w, h = 1024, 600
            except Exception:
                w, h = 1024, 600

            image = image.resize((w, h), Image.Resampling.LANCZOS)
            self.background_image = ImageTk.PhotoImage(image)

            if self.background_label is None:
                self.background_label = tk.Label(self.root, image=self.background_image)
                self.background_label.place(x=0, y=0, relwidth=1, relheight=1)
            else:
                self.background_label.configure(image=self.background_image)
        except Exception as e:
            # Không in log ở đây nếu text_display chưa tạo
            print(f"Error loading background image: {e}")

    def create_main_widgets(self):
        self.show_mode_selection()

    def show_mode_selection(self):
        """
        Màn hình chính: bố trí nút theo GRID 2 CỘT,
        phù hợp màn hình 7 inch (cảm ứng, nút to).
        """
        # Xoá mọi widget trừ background_label
        for widget in self.root.winfo_children():
            if widget is not self.background_label:
                widget.destroy()

        # Đặt lại background
        self.add_background_image()

        # Thêm lại text_display phía trên cùng
        self.text_display = tk.Text(
            self.root,
            height=9,
            width=120,
            state='disabled',
            font=("Helvetica", 11)
        )
        self.text_display.pack(pady=5, padx=10, fill="x")

        # Frame chứa các nút chức năng
        btn_frame = tk.Frame(self.root, bg="#000000")
        btn_frame.pack(pady=5, padx=10, fill="both", expand=True)

        # Danh sách các nút (text, command)
        buttons = []

        buttons.append(("Cấu hình UART / Test UART", self.open_uart_config_from_menu))
        buttons.append(("Test Mic", self.test_mic))
        buttons.append(("Chế Độ Trợ Lý Giọng Nói", self.voice_assistant.show_voice_assistant_ui))

        if self.music_control:
            buttons.append(("Chế Độ Phát Nhạc", self.music_control.show_music_mode))

        buttons.append(("Chế Độ Mở YouTube", self.youtube_control.open_youtube_mode))

        if self.image_processing:
            buttons.append(("Chế Độ Xử Lý Ảnh", self.activate_image_processing_mode))
            buttons.append(("Test Camera (không AI)", self.image_processing.test_camera))
            buttons.append(("Tắt Test Camera", self.image_processing.stop_test_camera))

        if self.voice_control:
            buttons.append(("Chế Độ Điều Khiển Giọng Nói", self.voice_control.activate))

        buttons.append(("Thoát", self.quit_application))

        # Tạo lưới nút 2 cột
        self.create_button_grid(btn_frame, buttons, columns=2)

    def create_button_grid(self, parent, buttons, columns=2):
        """
        Sắp xếp các nút trên parent theo dạng lưới, phù hợp màn hình 7".
        """
        for idx, (text, cmd) in enumerate(buttons):
            row = idx // columns
            col = idx % columns
            btn = tk.Button(
                parent,
                text=text,
                command=cmd,
                width=20,          # rộng, nhưng không quá dài
                height=3,          # cao hơn để dễ bấm
                font=("Helvetica", 12, "bold"),
                relief="raised",
                bd=3
            )
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        # Cho cột và hàng co giãn đều
        total_rows = (len(buttons) + columns - 1) // columns
        for c in range(columns):
            parent.grid_columnconfigure(c, weight=1)
        for r in range(total_rows):
            parent.grid_rowconfigure(r, weight=1)

    def activate_image_processing_mode(self):
        self.show_image_processing_mode_button = False
        if self.image_processing:
            self.image_processing.image_processing_mode()

    def log_message(self, message):
        """
        Ghi log ra cả Text UI và terminal.
        """
        # In ra terminal để anh xem log + lỗi UART
        print(message)

        try:
            self.text_display.config(state='normal')
            self.text_display.insert(tk.END, message + "\n")
            self.text_display.see(tk.END)
            self.text_display.config(state='disabled')
        except Exception:
            # Trường hợp text_display chưa sẵn sàng thì bỏ qua
            pass

    # ================== TEST MIC (KHÔNG DÙNG TK WINDOW MỚI) =========
    def test_mic(self):
        """Test mic bằng SpeechRecognition, log kết quả vào text_display."""
        if sr is None:
            self.log_message("Chưa cài thư viện SpeechRecognition. Hãy chạy: pip install SpeechRecognition")
            return

        def _run():
            try:
                r = sr.Recognizer()
                try:
                    devices = sr.Microphone.list_microphone_names()
                except Exception as e:
                    self.log_message(f"Lỗi liệt kê thiết bị mic: {e}")
                    return

                if not devices:
                    self.log_message("Không tìm thấy thiết bị mic nào.")
                    return

                self.log_message("Danh sách thiết bị mic:")
                for i, name in enumerate(devices):
                    self.log_message(f"  {i}: {name}")

                # Chọn ưu tiên USB, nếu không có thì dùng index 0
                index = None
                for i, name in enumerate(devices):
                    if "USB" in name:
                        index = i
                        break
                if index is None:
                    index = 0

                self.log_message(f"Sử dụng mic index = {index} ({devices[index]})")
                self.log_message("Hãy nói trong khoảng 3 giây...")

                with sr.Microphone(device_index=index) as source:
                    r.adjust_for_ambient_noise(source, duration=1)
                    audio = r.listen(source, timeout=5, phrase_time_limit=3)

                self.log_message("Đã ghi xong. Thử nhận dạng (nếu có mạng + flac)...")

                try:
                    text = r.recognize_google(audio, language="vi-VN")
                    self.log_message(f"Mic OK. Nghe được: {text}")
                except Exception as e:
                    # Trường hợp thiếu flac hoặc không nhận dạng được
                    self.log_message(f"Mic có tín hiệu nhưng không nhận dạng được: {e}")

            except Exception as e:
                self.log_message(f"Lỗi trong quá trình test mic: {e}")

        threading.Thread(target=_run, daemon=True).start()

    # ================== THOÁT ỨNG DỤNG ==============================
    def quit_application(self):
        # Tắt luôn test camera / xử lý ảnh cho chắc
        if self.image_processing:
            self.image_processing.stop_test_camera()
            self.image_processing.face_recognition_running = False

        if self.serial_conn:
            self.serial_conn.close()
            self.log_message("Đã đóng UART cho image_processing.")
        if self.serial_conn1:
            self.serial_conn1.close()
            self.log_message("Đã đóng UART cho music/voice.")
        self.log_message("Đã thoát chương trình.")
        self.root.quit()


def launch_main_app():
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        launch_main_app()
    except Exception:
        print("==== LỖI CHƯƠNG TRÌNH CHÍNH ====")
        traceback.print_exc()


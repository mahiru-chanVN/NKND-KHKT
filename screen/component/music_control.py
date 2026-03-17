import os
import pygame
import tkinter as tk
import threading
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class MusicControl:
    def __init__(self, app, serial_conn=None):
        self.app = app
        self.serial_conn = serial_conn
        self.is_playing = False
        self.stop_sending = False
        self.current_song = None
        self.current_thread = None
        pygame.mixer.init()

        self.music_files = [
            os.path.join(BASE_DIR, "music", "song1.mp3"),
            os.path.join(BASE_DIR, "music", "song2.mp3"),
            os.path.join(BASE_DIR, "music", "song3.mp3"),
            os.path.join(BASE_DIR, "music", "song4.mp3"),
            os.path.join(BASE_DIR, "music", "song5.mp3"),
            os.path.join(BASE_DIR, "music", "song6.mp3"),
            os.path.join(BASE_DIR, "music", "song7.mp3"),
            os.path.join(BASE_DIR, "music", "song8.mp3"),
        ]

        # Số lần lặp lại cho mỗi bài hát, -1 là lặp vô hạn
        self.loop_counts = [1, 1, 1, 1, 1, 1, 1, 2]

        self.data_display = tk.Text(self.app.root, height=10, width=50)
        self.data_display.pack(pady=10)
        pygame.mixer.music.set_endevent(pygame.USEREVENT)

    def show_music_mode(self):
        for widget in self.app.root.winfo_children():
            widget.pack_forget()
        
        for i, song in enumerate(self.music_files):
            tk.Button(self.app.root, text=f"Bài hát {i + 1}",
                      command=lambda i=i: self.play_song(i), width=15).pack(pady=5)
        
        tk.Button(self.app.root, text="Thoát chế độ nhạc",
                  command=self.exit_music_mode, width=15).pack(pady=5)
        self.data_display.pack(pady=10)

    def play_song(self, song_index):
        try:
            if self.is_playing:
                pygame.mixer.music.stop()
                self.stop_sending = True
                if self.current_thread and self.current_thread.is_alive():
                    self.current_thread.join()

            self.current_song = song_index
            loop_count = self.loop_counts[song_index]

            if loop_count == 0:
                self.data_display.insert(tk.END, f"Bài hát {song_index + 1} không được phát (loop_count=0).\n")
                self.data_display.see(tk.END)
                return

            pygame.mixer.music.load(self.music_files[song_index])
            pygame.mixer.music.play(loop_count - 1 if loop_count > 0 else -1)
            self.is_playing = True

            self.stop_sending = False
            self.current_thread = threading.Thread(target=self.continuous_serial_send, args=(song_index + 1,))
            self.current_thread.start()

        except Exception as e:
            self.data_display.insert(tk.END, f"Error playing song: {e}\n")
            self.data_display.see(tk.END)

    def continuous_serial_send(self, song_number):
        while self.is_playing and not self.stop_sending:
            if self.serial_conn and self.serial_conn.is_open:
                command = f"B{song_number}".ljust(2)
                try:
                    self.serial_conn.write(command.encode())
                    self.data_display.insert(tk.END, f"Đã gửi tín hiệu: '{command.strip()}'\n")
                    self.data_display.see(tk.END)
                except Exception as e:
                    self.data_display.insert(tk.END, f"Lỗi khi gửi tín hiệu serial: {e}\n")
                    self.data_display.see(tk.END)
            time.sleep(0.1)

    def exit_music_mode(self):
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.stop_sending = True
            if self.current_thread and self.current_thread.is_alive():
                self.current_thread.join()
        self.app.show_mode_selection()
        def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.USEREVENT:
                self.play_song(self.current_song)


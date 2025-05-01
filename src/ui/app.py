# RJ Auto Metadata
# Copyright (C) 2025 Riiicil
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# src/ui/app.py
import os
import sys
import threading
import time
import queue
import random
import json
import platform
import re  # Import regex module
import sys # Needed for sys.exit
import uuid
import webbrowser
import tkinter as tk
import tkinter.messagebox # Added for checks below
import customtkinter as ctk
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from src.utils.logging import log_message
from src.utils.file_utils import read_api_keys, is_writable_directory
from src.utils.analytics import send_analytics_event
from src.config.config import MEASUREMENT_ID, API_SECRET, ANALYTICS_URL
from src.processing.batch_processing import batch_process_files
# from src.metadata.exif_writer import check_exiftool_exists # Moved check inside __init__
from src.ui.widgets import ToolTip
from src.ui.dialogs import CompletionMessageManager
# Import system checks
from src.utils.system_checks import (
    check_ghostscript, check_ffmpeg, check_gtk_dependencies,
    set_console_visibility # Import the new function
)
from src.metadata.exif_writer import check_exiftool_exists # Keep this import for the check

# Konstanta aplikasi
APP_VERSION = "2.0.1"
CONFIG_FILE = "config.json"

class MetadataApp(ctk.CTk):
    """
    Kelas utama aplikasi RJ Auto Metadata.
    """
    def __init__(self):
        super().__init__()
        
        # Inisialisasi font
        self.default_font_family = "Aptos_display"
        from src.utils.logging import set_log_handler
        set_log_handler(self._log)
        # Cek apakah font ada
        def font_exists(font_name):
            try:
                test_label = tk.Label(text="Test", font=(font_name, 12))
                exists = test_label.cget("font").split()[0] == font_name
                test_label.destroy()
                return exists
            except Exception:
                return False
                
        if not font_exists(self.default_font_family):
            self._log(f"Font '{self.default_font_family}' tidak ditemukan, menggunakan font default sistem", "warning")
            self.default_font_family = "Arial"
        
        # Setup font
        self.font_small = ctk.CTkFont(family=self.default_font_family, size=10)
        self.font_normal = ctk.CTkFont(family=self.default_font_family, size=12)
        self.font_medium = ctk.CTkFont(family=self.default_font_family, size=13)
        self.font_large = ctk.CTkFont(family=self.default_font_family, size=15, weight="bold")
        self.font_title = ctk.CTkFont(family=self.default_font_family, size=18, weight="bold")

        # Setup state untuk processing (Initialize log_queue earlier)
        self.start_time = None
        self.processing_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue() # Initialize log_queue HERE
        self._log_queue_after_id = None
        self._stop_request_time = None
        self._in_summary_block = False # Flag for summary block

        # --- Dependency Checks ---
        self._perform_startup_checks() # Call the new check method

        # Setup warna dasar
        self.configure(fg_color=("#f0f0f5", "#2d2d30"))

        # Variable untuk tracking analitik
        self.analytics_enabled_var = tk.BooleanVar(value=True)
        self.installation_id = tk.StringVar(value="")
        
        # Setup UI dasar
        self.title("Auto Metadata")

        # --- Debug Execution Mode ---
        log_message(f"--- Debug Info ---", "info")
        log_message(f"sys.frozen: {getattr(sys, 'frozen', 'Not Set')}", "info")
        log_message(f"sys.executable: {sys.executable}", "info")
        try:
            log_message(f"__file__ (app.py): {__file__}", "info")
        except NameError:
            log_message(f"__file__ (app.py): Not Defined", "info")
        log_message(f"os.getcwd(): {os.getcwd()}", "info")
        # --- End Debug Info ---

        # Determine base directory using the centralized function
        # Import _get_base_dir from system_checks
        from src.utils.system_checks import _get_base_dir
        base_dir = _get_base_dir() # Use the function from system_checks

        # Load icon aplikasi using the determined base_dir
        try:
            self.iconbitmap_path = os.path.join(base_dir, 'assets', 'icon1.ico')
            log_message(f"Attempting to load icon from: {self.iconbitmap_path}", "info") # Log path being tried
            if os.path.exists(self.iconbitmap_path):
                self.iconbitmap(self.iconbitmap_path)
                log_message(f"Icon aplikasi dimuat dari: {self.iconbitmap_path}", "info") # Add log
            else:
                log_message(f"Warning: File icon tidak ditemukan di path relatif: {self.iconbitmap_path}", "warning") # Use log
                self.iconbitmap_path = None
        except Exception as e:
            log_message(f"Error saat mengatur icon aplikasi: {e}", "error") # Use log
            self.iconbitmap_path = None
        
        # Setup ukuran window
        self.geometry("600x800")
        self.minsize(600, 800)
        
        # Variables
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.rename_files_var = tk.BooleanVar(value=False)
        self.delay_var = tk.StringVar(value="10")
        self.workers_var = tk.StringVar(value="1")
        self._actual_api_keys = [] # Store the real keys internally
        self.show_api_keys_var = tk.BooleanVar(value=False) # Variable for the toggle checkbox
        self.console_visible_var = tk.BooleanVar(value=True) # Variable for console visibility toggle
        self.progress_text_var = tk.StringVar(value="Proses: Siap memulai")

        # Counters
        self.processed_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.stopped_count = 0
        
        # Setup tema
        self.theme_folder = os.path.join(os.path.dirname(__file__), "themes")
        self.available_themes = ["dark", "light", "system"]
        
        # Load tema kustom jika ada
        if os.path.exists(self.theme_folder):
            import glob
            custom_themes = glob.glob(os.path.join(self.theme_folder, "*.json"))
            for theme_path in custom_themes:
                theme_name = os.path.splitext(os.path.basename(theme_path))[0]
                self.available_themes.append(theme_name)

        # Load konfigurasi
        self.config_path = self._get_config_path()
        self.processed_cache = {}
        self.cache_file = os.path.join(os.path.dirname(self.config_path), "processed_cache.json")
        
        # Auto kategori dan foldering
        self.auto_kategori_var = tk.BooleanVar(value=False)
        self.auto_foldering_var = tk.BooleanVar(value=False)
        self._needs_initial_save = False # Flag to track if initial save is needed
        
        # Inisialisasi UI
        self._create_ui()
        self._process_log_queue()
        self._load_settings()
        self._init_analytics() # This might set _needs_initial_save
        self._load_cache()
        
        # Perform initial save if needed after loading and analytics init
        if self._needs_initial_save:
            self._save_settings()
            self._needs_initial_save = False # Reset flag
            
        # Eksekusi sebelum menutup aplikasi
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Check mode eksekusi
        self.is_executable = self._is_running_as_executable()
        
        # Setup completion message
        self.completion_manager = CompletionMessageManager(
            self,
            self.config_path,
            self.font_normal,
            self.font_medium,
            self.font_large,
            self.iconbitmap_path
        )
        
        # Waktu timeout berdasarkan mode eksekusi
        if self.is_executable:
            print("Aplikasi berjalan sebagai executable.")
            self.executable_timeout = 2.0
            self.executable_max_wait = 5.0
        else:
            print("Aplikasi berjalan sebagai script Python.")
            self.executable_timeout = 3.0
            self.executable_max_wait = 10.0

    def _perform_startup_checks(self):
        """Performs checks for external dependencies at startup."""
        self._log("Memeriksa dependensi eksternal...", "info")

        # Check ExifTool (Critical)
        self._log("Memeriksa ketersediaan Exiftool...", "info")
        exiftool_ok = check_exiftool_exists()
        if not exiftool_ok:
            self._log("Exiftool tidak ditemukan.", "error")
            tkinter.messagebox.showerror("Error Kritis",
                "Exiftool tidak ditemukan atau tidak berfungsi.\n"
                "Aplikasi tidak dapat berjalan tanpa Exiftool.\n"
                "Pastikan sudah terinstal dan ada di PATH.")
            self.destroy() # Close the app window cleanly
            sys.exit(1) # Exit the process
        else:
            self._log("Exiftool ditemukan.", "success")

        # Check Ghostscript (Warn only, for AI/EPS)
        self._log("Memeriksa ketersediaan Ghostscript...", "info")
        gs_ok = check_ghostscript()
        if not gs_ok:
            self._log("Ghostscript tidak ditemukan. Pemrosesan AI/EPS akan gagal.", "warning")
            tkinter.messagebox.showwarning("Peringatan Ketergantungan",
                "Ghostscript tidak ditemukan atau tidak berfungsi.\n"
                "Pastikan sudah terinstal dan ada di PATH.\n"
                "Pemrosesan file AI/EPS akan gagal.")
        else:
            self._log("Ghostscript ditemukan.", "success")

        # Check FFmpeg (Warn only, for Video)
        self._log("Memeriksa ketersediaan FFmpeg...", "info")
        ffmpeg_ok = check_ffmpeg()
        if not ffmpeg_ok:
            self._log("FFmpeg tidak ditemukan. Pemrosesan Video akan gagal.", "warning")
            tkinter.messagebox.showwarning("Peringatan Ketergantungan",
                "FFmpeg tidak ditemukan atau tidak berfungsi.\n"
                "Pastikan sudah terinstal dan ada di PATH.\n"
                "Pemrosesan file Video (MP4/MKV) akan gagal.")
        else:
            self._log("FFmpeg ditemukan.", "success")

        # Check GTK Dependencies (Warn only, for SVG)
        self._log("Memeriksa ketersediaan dependensi GTK (cairocffi)...", "info")
        gtk_ok = check_gtk_dependencies()
        if not gtk_ok:
            self._log("Dependensi GTK (cairocffi) tidak ditemukan. Pemrosesan SVG mungkin gagal.", "warning")
            tkinter.messagebox.showwarning("Peringatan Ketergantungan",
                "Gagal mengimpor dependensi GTK (cairocffi).\n"
                "Ini mungkin disebabkan oleh GTK3 Runtime yang hilang atau salah konfigurasi.\n"
                "Pemrosesan file SVG mungkin akan gagal.")
        else:
             self._log("Dependensi GTK (cairocffi) ditemukan.", "success")

        self._log("Pemeriksaan dependensi selesai.", "info")


    def _is_running_as_executable(self):
        """Memeriksa apakah aplikasi berjalan sebagai executable."""
        if getattr(sys, 'frozen', False):
            return True
        for attr in ['__compiled__', '_MEIPASS', '_MEIPASS2']:
            if hasattr(sys, attr):
                return True
        try:
            exe_path = os.path.realpath(sys.executable).lower()
            if (exe_path.endswith('.exe') and 'python' not in exe_path) or '.exe.' in exe_path:
                return True
        except Exception:
            pass
        return False
    
    # --- UI Creation Methods ---
    def _create_ui(self):
        """Membuat UI aplikasi."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Panel utama
        main_panel = ctk.CTkFrame(self, corner_radius=10)
        main_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        main_panel.grid_columnconfigure(0, weight=1)
        main_panel.grid_rowconfigure(0, weight=0) 
        main_panel.grid_rowconfigure(1, weight=0)
        main_panel.grid_rowconfigure(2, weight=0)
        main_panel.grid_rowconfigure(3, weight=1)
        
        # Frame untuk settings, center, status
        settings_center_status_frame = ctk.CTkFrame(main_panel, fg_color="transparent")
        settings_center_status_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        settings_center_status_frame.grid_columnconfigure(0, weight=1)
        settings_center_status_frame.grid_columnconfigure(1, weight=1)
        settings_center_status_frame.grid_columnconfigure(2, weight=1)
        
        # Frame folder
        self._create_folder_frame(main_panel)
        
        # Frame API
        self._create_api_frame(main_panel)
        
        # Frame options
        self._create_options_frame(settings_center_status_frame)
        
        # Frame checkbox
        self._create_checkbox_frame(settings_center_status_frame)
        
        # Frame status
        self._create_status_frame(settings_center_status_frame)
        
        # Frame log
        self._create_log_frame(main_panel)
        
        # Watermark
        self._create_watermark(main_panel)
        
        # Setup ukuran relatif
        main_panel.grid_rowconfigure(3, weight=1)
    
    def _create_folder_frame(self, parent):
        """Membuat frame untuk input/output folder."""
        folder_frame = ctk.CTkFrame(parent, corner_radius=8)
        folder_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)
        
        older_header_tooltip = """
Pilih folder sumber (input) dan folder tujuan (output) untuk gambar.

- Input Folder: Folder yang berisi\n   gambar yang akan diproses
- Output Folder: Folder di mana gambar\n   yang sudah diproses akan disimpan

Gambar dari folder input akan diproses dengan API, kemudian disalin ke folder output dengan metadata baru.
"""
        folder_header = self._create_header_with_help(folder_frame, "Folder Input/Output", older_header_tooltip, font=ctk.CTkFont(size=15, weight="bold"))
        folder_header.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="w")
        
        ctk.CTkLabel(folder_frame, text="Input Folder:").grid(
            row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.input_entry = ctk.CTkEntry(folder_frame, textvariable=self.input_dir)
        self.input_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        self.input_button = ctk.CTkButton(folder_frame, text="Browse", command=self._select_input_folder, width=70, fg_color="#079183")
        self.input_button.grid(row=1, column=2, padx=5, pady=5)
        
        ctk.CTkLabel(folder_frame, text="Output Folder:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.output_entry = ctk.CTkEntry(folder_frame, textvariable=self.output_dir)
        self.output_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        self.output_button = ctk.CTkButton(folder_frame, text="Browse", command=self._select_output_folder, width=70, fg_color="#079183")
        self.output_button.grid(row=2, column=2, padx=5, pady=5)
        
        folder_tooltip_text = "Input dan Output harus berbeda. \nJangan menggunakan folder yang sama untuk keduanya."
        ToolTip(self.input_entry, folder_tooltip_text)
        ToolTip(self.output_entry, folder_tooltip_text)
    
    def _create_api_frame(self, parent):
        """Membuat frame untuk API keys."""
        api_frame = ctk.CTkFrame(parent, corner_radius=8)
        api_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        api_frame.grid_columnconfigure(0, weight=1)
        api_frame.grid_columnconfigure(1, weight=0)
        api_frame.grid_columnconfigure(2, weight=0)
        
        api_header_tooltip = """
Tambahkan satu atau lebih API key Gemini untuk memproses gambar.
Setiap baris adalah satu API key.

    • Anda bisa mendapatkan API key\n       dari Google AI Studio
    • Batas pemrosesan 60 gambar\n       per menit per API key
    • Rotasi otomatis beberapa API key\n       terjadi saat pemrosesan batch

Semakin banyak API key, semakin cepat proses batch.
        """
        # --- API Header Frame ---
        api_header_frame = ctk.CTkFrame(api_frame, fg_color="transparent")
        api_header_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="w")

        api_header = self._create_header_with_help(api_header_frame, "API Keys", api_header_tooltip, font=ctk.CTkFont(size=15, weight="bold"))
        api_header.pack(side=tk.LEFT, padx=(0, 10)) # Pack header to the left

        # --- Show/Hide Checkbox ---
        # --- Show/Hide Switch ---
        self.show_api_keys_switch = ctk.CTkSwitch(
            api_header_frame,
            text="", # Ensure text is empty
            variable=self.show_api_keys_var,
            command=self._toggle_api_key_visibility,
            font=self.font_small, # Font might not be needed without text, but keep for consistency
            switch_width=35, # Adjust width if needed
            switch_height=18 # Adjust height if needed
        )
        self.show_api_keys_switch.pack(side=tk.LEFT, padx=(5, 0)) # Pack switch next to header
        ToolTip(self.show_api_keys_switch, "Tampilkan/Sembunyikan API Key") # Add tooltip directly to switch

        self.api_textbox = ctk.CTkTextbox(api_frame, height=105, corner_radius=5, wrap=tk.WORD, font=self.font_normal)
        self.api_textbox.grid(row=1, column=0, padx=(10, 5), pady=(0, 10), sticky="nsew")
        # Bind key release to sync internal list when keys are visible and user types
        self.api_textbox.bind("<KeyRelease>", self._sync_actual_keys_from_textbox)
        
        api_load_save_buttons = ctk.CTkFrame(api_frame, fg_color="transparent")
        api_load_save_buttons.grid(row=1, column=1, padx=5, pady=(12, 10), sticky="ns")
        
        self.load_api_button = ctk.CTkButton(api_load_save_buttons, text="Load", width=70, command=self._load_api_keys, fg_color="#079183")
        self.load_api_button.pack(pady=5, fill=tk.X)
        
        self.save_api_button = ctk.CTkButton(api_load_save_buttons, text="Save", width=70, command=self._save_api_keys, fg_color="#079183")
        self.save_api_button.pack(pady=5, fill=tk.X)
        
        self.delete_api_button = ctk.CTkButton(api_load_save_buttons, text="Delete", width=70, command=self._delete_selected_api_key, fg_color="#079183")
        self.delete_api_button.pack(pady=5, fill=tk.X)
        
        process_buttons_frame = ctk.CTkFrame(api_frame, fg_color="transparent")
        process_buttons_frame.grid(row=1, column=2, padx=(5, 10), pady=(0, 10), sticky="ns")
        
        self.start_button = ctk.CTkButton(process_buttons_frame, text="Mulai Proses", command=self._start_processing, font=self.font_medium, height=35, fg_color="#079183")
        self.start_button.pack(pady=5, fill=tk.X)
        
        self.stop_button = ctk.CTkButton(process_buttons_frame, text="Hentikan", command=self._stop_processing, font=self.font_medium, height=35, state=tk.DISABLED, fg_color=("#bf3a3a", "#8d1f1f"))
        self.stop_button.pack(pady=5, fill=tk.X)
        
        self.clear_button = ctk.CTkButton(process_buttons_frame, text="Clear Log", command=self._clear_log, font=self.font_medium, height=35, fg_color="#079183")
        self.clear_button.pack(pady=5, fill=tk.X)
    
    def _create_options_frame(self, parent):
        """Membuat frame untuk opsi pengaturan."""
        options_frame = ctk.CTkFrame(parent, corner_radius=8)
        options_frame.grid(row=0, column=0, padx=(0, 3), pady=0, sticky="nsew")
        options_frame.grid_columnconfigure(1, weight=1)
        
        settings_header_tooltip = """
Konfigurasi perilaku aplikasi:

- Workers: Jumlah thread paralel untuk\n  memproses file (Misal: 1-10). Lebih\n  banyak worker mempercepat proses,\n  namun juga meningkatkan\n  frekuensi penggunaan API.

- Delay (s): Jeda waktu (detik) antar\n  permintaan ke API. Berguna untuk\n  mencegah pembatasan (rate limit) API.

- Rename Files: Jika aktif, nama file\n  akan diubah otomatis berdasarkan\n  metadata 'judul' dari API.

- Auto Kategori: Jika aktif, otomatis\n  mengkategorikan file sesuai metadata\n  dari API. (Hasilnya mungkin belum\n  sempurna, harap periksa kembali).

- Auto Foldering: Jika aktif, file yang\n  diproses akan otomatis dimasukkan ke\n  dalam folder berdasarkan tipenya\n  (misal: Images, Vectors, Video).
    
*NB: Pengaturan ini disimpan secara\n        otomatis untuk sesi berikutnya.
"""
        settings_header = self._create_header_with_help(options_frame, "Pengaturan", settings_header_tooltip, font=ctk.CTkFont(size=15, weight="bold"))
        settings_header.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="wns")
        
        theme_label = ctk.CTkLabel(options_frame, text="Tema:", font=self.font_normal)
        theme_label.grid(row=1, column=0, padx=10, pady=(5, 5), sticky="wns")
        
        self.theme_var = tk.StringVar(value="dark")
        self.theme_dropdown = ctk.CTkComboBox(options_frame, values=self.available_themes, variable=self.theme_var, command=self._change_theme, width=100, justify='center')
        self.theme_dropdown.grid(row=1, column=1, padx=5, pady=(5, 5), sticky="w")
        
        ctk.CTkLabel(options_frame, text="Workers:", font=self.font_normal).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.workers_entry = ctk.CTkEntry(options_frame, textvariable=self.workers_var,width=100, justify='center', font=self.font_normal)
        self.workers_entry.grid(row=2, column=1, padx=5, pady=5, sticky="wns")
        
        ctk.CTkLabel(options_frame, text="Delay (s):", font=self.font_normal).grid(row=3, column=0, padx=10, pady=5, sticky="wns")
        
        self.delay_entry = ctk.CTkEntry(options_frame, textvariable=self.delay_var,width=100, justify='center', font=self.font_normal)
        self.delay_entry.grid(row=3, column=1, padx=5, pady=5, sticky="wns")
    
    def _create_checkbox_frame(self, parent):
        """Membuat frame untuk checkbox."""
        checkbox_frame = ctk.CTkFrame(parent, corner_radius=8)
        checkbox_frame.grid(row=0, column=1, padx=3, pady=0, sticky="wes")
        checkbox_frame.grid_columnconfigure(0, weight=1)
        
        self.rename_switch = ctk.CTkSwitch(checkbox_frame, text="Rename File?", variable=self.rename_files_var, font=self.font_normal)
        self.rename_switch.grid(row=0, column=0, padx=10, pady=8, sticky="w") # Adjusted sticky to 'w'
        
        self.auto_kategori_switch = ctk.CTkSwitch(checkbox_frame, text="Auto Kategori?", variable=self.auto_kategori_var, font=self.font_normal)
        self.auto_kategori_switch.grid(row=1, column=0, padx=10, pady=8, sticky="w") # Adjusted sticky to 'w'
        
        self.auto_foldering_switch = ctk.CTkSwitch(checkbox_frame, text="Auto Foldering?", variable=self.auto_foldering_var, font=self.font_normal)
        self.auto_foldering_switch.grid(row=2, column=0, padx=10, pady=8, sticky="w") # Adjusted sticky to 'w'
    
    def _create_status_frame(self, parent):
        """Membuat frame untuk status proses."""
        status_frame_new = ctk.CTkFrame(parent, corner_radius=8)
        status_frame_new.grid(row=0, column=2, padx=(3, 0), pady=0, sticky="nw")
        status_frame_new.grid_columnconfigure(0, weight=1)
        status_frame_new.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(status_frame_new, text="Status", font=self.font_large).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        ctk.CTkLabel(status_frame_new, textvariable=self.progress_text_var, font=self.font_medium).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(status_frame_new, orientation="horizontal", height=65, width=130, corner_radius=0)
        self.progress_bar.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="w")
        self.progress_bar.set(0)
    
    def _create_log_frame(self, parent):
        """Membuat frame untuk log."""
        log_frame = ctk.CTkFrame(parent, corner_radius=8)
        log_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(log_frame, text="Log", font=self.font_large).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.log_text = ctk.CTkTextbox(log_frame, wrap=tk.WORD, height=200, font=self.font_normal)
        self.log_text.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.log_text.configure(state=tk.DISABLED)
        
        # Setup tag warna
        theme_mode = ctk.get_appearance_mode() 
        success_color = ("#21a645", "#21a645") 
        error_color = ("#ff0000", "#ff0000")
        warning_color = ("#ff9900", "#ff9900")
        info_color = ("#0088ff", "#0088ff")
        cooldown_color = ("#8800ff", "#8800ff")
        bold_font = (self.default_font_family, 11, "bold")
        
        self.log_text._textbox.tag_configure("success", foreground=success_color[1 if theme_mode == "dark" else 0])
        self.log_text._textbox.tag_configure("error", foreground=error_color[1 if theme_mode == "dark" else 0])
        self.log_text._textbox.tag_configure("warning", foreground=warning_color[1 if theme_mode == "dark" else 0])
        self.log_text._textbox.tag_configure("info", foreground=info_color[1 if theme_mode == "dark" else 0])
        self.log_text._textbox.tag_configure("cooldown", foreground=cooldown_color[1 if theme_mode == "dark" else 0])
        self.log_text._textbox.tag_configure("bold", font=bold_font)

    def _create_watermark(self, parent):
        """Membuat watermark dan console toggle di bagian bawah aplikasi."""
        bottom_frame = ctk.CTkFrame(parent, fg_color="transparent")
        bottom_frame.grid(row=4, column=0, padx=5, pady=(0, 5), sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1) # Console toggle area
        bottom_frame.grid_columnconfigure(1, weight=1) # Watermark area

        # Console Toggle Switch (only add if on Windows)
        if platform.system() == "Windows":
            self.console_toggle_switch = ctk.CTkSwitch(
                bottom_frame,
                text="", # Text removed
                variable=self.console_visible_var,
                command=self._toggle_console_visibility,
                font=self.font_small # Keep font for size consistency maybe? Or remove if not needed.
            )
            self.console_toggle_switch.grid(row=0, column=0, sticky="w", padx=(10, 5))
            ToolTip(self.console_toggle_switch, "Tampilkan/Sembunyikan Jendela Konsol") # Add tooltip
            # Remove call to update text, as it's no longer needed
            # self._update_console_toggle_text()

        # Watermark
        watermark_label = ctk.CTkLabel(bottom_frame, text="© Riiicil 2025 - Ver 2.0.1", font=ctk.CTkFont(size=10), text_color=("gray50", "gray70"))
        watermark_label.grid(row=0, column=1, sticky="e", padx=(5, 10))

    def _toggle_console_visibility(self):
        """Callback function for the console visibility switch."""
        if platform.system() == "Windows":
            show = self.console_visible_var.get()
            set_console_visibility(show)
            self._update_console_toggle_text()
            # Save the setting immediately
            self._save_settings()
        else:
             # Should not happen as switch is not created, but good practice
             log_message("Console toggle attempted on non-Windows system.", "warning")

    def _update_console_toggle_text(self):
         """Updates the text of the console toggle switch."""
         if platform.system() == "Windows" and hasattr(self, 'console_toggle_switch'):
             # Text is no longer set here, managed by initial creation and tooltip
             pass # Placeholder if needed, or simply remove the if/else block content

    def _create_header_with_help(self, parent, text, tooltip_text, font=None):
        """Membuat header dengan icon bantuan."""
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        
        if font:
            header_label = ctk.CTkLabel(header_frame, text=text, font=font)
        else:
            header_label = ctk.CTkLabel(header_frame, text=text, font=("Segoe UI", 12, "bold"))
            
        header_label.pack(side=tk.LEFT, padx=(0, 5))
        
        help_icon_size = 16
        help_icon = ctk.CTkLabel(
            header_frame, 
            text="?", 
            width=help_icon_size, 
            height=help_icon_size,
            fg_color=("#3a7ebf", "#1f538d"),
            corner_radius=8,
            text_color="white",
            font=("Segoe UI", 10, "bold")
        )
        help_icon.pack(side=tk.LEFT, padx=(0, 5))
        
        ToolTip(help_icon, tooltip_text)
        
        return header_frame
    
    # --- Analytics Methods ---
    def _init_analytics(self):
        """Generate installation ID if needed and send startup event."""
        if not self.installation_id.get():
            # Buat ID unik saat pertama kali dijalankan
            new_id = str(uuid.uuid4())
            self.installation_id.set(new_id)
            self._log(f"Membuat ID instalasi baru: {new_id}", "info")
            self._needs_initial_save = True # Mark that settings need saving

        # Kirim event startup jika diizinkan
        self._send_analytics_event("app_start")

    def _send_analytics_event(self, event_name, params={}):
        """Mengirim event analitik jika diaktifkan."""
        if not self.analytics_enabled_var.get():
            return
        
        if not MEASUREMENT_ID or not API_SECRET:
            self._log("Konfigurasi Analytics tidak lengkap, event tidak dikirim.", "warning")
            return
        
        # Tambah parameter standar
        system_params = {
            "operating_system": platform.system(),
            "os_version": platform.release(),
        }
        
        # Gabungkan parameter
        full_params = {**system_params, **params}
        
        # Kirim dalam thread terpisah
        send_analytics_event(
            self.installation_id.get(),
            event_name,
            APP_VERSION,
            full_params
        )
    
    # --- File Management Methods ---
    def _select_input_folder(self):
        """Dialog untuk memilih folder input."""
        directory = tk.filedialog.askdirectory(title="Pilih Folder Input")
        if directory:
            output_dir = self.output_dir.get().strip()
            if output_dir and os.path.normpath(directory) == os.path.normpath(output_dir):
                tk.messagebox.showwarning(
                    "Folder Sama", 
                    "Folder input tidak boleh sama dengan folder output.\nSilakan pilih folder yang berbeda."
                )
                return
            self.input_dir.set(directory)
    
    def _select_output_folder(self):
        """Dialog untuk memilih folder output."""
        directory = tk.filedialog.askdirectory(title="Pilih Folder Output")
        if directory:
            input_dir = self.input_dir.get().strip()
            if input_dir and os.path.normpath(directory) == os.path.normpath(input_dir):
                tk.messagebox.showwarning(
                    "Folder Sama", 
                    "Folder output tidak boleh sama dengan folder input.\nSilakan pilih folder yang berbeda."
                )
                return
            self.output_dir.set(directory)
    
    def _load_cache(self):
        """Memuat cache file yang telah diproses."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.processed_cache = json.load(f)
        except Exception as e:
            self._log(f"Error memuat cache: {e}", "error")
            self.processed_cache = {}
    
    def _save_cache(self):
        """Menyimpan cache file yang telah diproses."""
        try:
            if len(self.processed_cache) > 1000:
                # Simpan hanya 1000 entri terbaru
                cache_items = sorted(self.processed_cache.items(), 
                                key=lambda x: x[1].get('timestamp', 0), 
                                reverse=True)
                self.processed_cache = dict(cache_items[:1000])
                
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_cache, f, indent=4)
        except Exception as e:
            self._log(f"Error menyimpan cache: {e}", "error")
    
    # --- API Key Management Methods ---
    def _load_api_keys(self):
        """Dialog untuk memuat API key dari file."""
        filepath = tk.filedialog.askopenfilename(
            title="Pilih File API Keys (.txt)", 
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        
        if not filepath:
            return
            
        try:
            keys = read_api_keys(filepath)
            if keys:
                self._actual_api_keys = keys # Update internal list
                self._update_api_textbox() # Update display (will show placeholders or keys based on toggle)
                self._log(f"Berhasil memuat {len(keys)} API key", "success") # Add success tag
            else:
                tk.messagebox.showwarning("File Kosong",
                    f"File API keys kosong atau tidak valid.")
        except Exception as e:
            self._log(f"Error saat memuat API keys: {e}")
            tk.messagebox.showerror("Error", f"Gagal memuat API keys: {e}")
    
    def _save_api_keys(self):
        """Dialog untuk menyimpan API key ke file."""
        keys_to_save = self._get_keys_from_textbox()
        if not keys_to_save:
            tk.messagebox.showwarning("Tidak Ada Key", 
                "Tidak ada API Key untuk disimpan.")
            return
            
        filepath = tk.filedialog.asksaveasfilename(
            title="Simpan API Keys", 
            defaultextension=".txt",
            initialfile="api_keys.txt",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
            
        if not filepath:
            return
            
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("\n".join(keys_to_save))
            self._log(f"API Keys ({len(keys_to_save)}) disimpan ke file", "success") # Add success tag
        except Exception as e:
            self._log(f"Error saat menyimpan API keys: {e}")
            tk.messagebox.showerror("Error", f"Gagal menyimpan API keys: {e}")
    
    def _delete_selected_api_key(self):
        """Menghapus API key berdasarkan seleksi atau posisi kursor."""
        start_line_idx = -1
        end_line_idx = -1
        num_keys_to_delete = 0
        delete_mode = "" # "selection" or "cursor"

        try:
            # Coba dapatkan seleksi
            start_index_str = self.api_textbox._textbox.index("sel.first")
            end_index_str = self.api_textbox._textbox.index("sel.last")
            start_line_idx = int(start_index_str.split('.')[0]) - 1
            end_line_idx = int(end_index_str.split('.')[0]) - 1
            delete_mode = "selection"
            num_keys_to_delete = end_line_idx - start_line_idx + 1

        except tk.TclError:
            # Tidak ada seleksi, coba gunakan posisi kursor
            try:
                cursor_index_str = self.api_textbox.index(tk.INSERT)
                start_line_idx = int(cursor_index_str.split('.')[0]) - 1
                end_line_idx = start_line_idx # Hanya satu baris
                delete_mode = "cursor"
                num_keys_to_delete = 1
            except ValueError:
                self._log("Error mendapatkan posisi kursor.", "error")
                tk.messagebox.showerror("Error", "Tidak dapat menentukan baris target untuk dihapus.")
                return
            except Exception as e:
                 self._log(f"Error tak terduga saat mendapatkan posisi kursor: {e}", "error")
                 tk.messagebox.showerror("Error", f"Terjadi error tak terduga saat cek kursor: {e}")
                 return

        except ValueError:
            self._log("Error mengonversi indeks baris seleksi saat menghapus key.", "error")
            tk.messagebox.showerror("Error", "Terjadi kesalahan saat memproses indeks baris terpilih.")
            return

        # Validasi setelah mendapatkan indeks (baik dari seleksi maupun kursor)
        if start_line_idx < 0 or start_line_idx >= len(self._actual_api_keys):
             # Jika kursor di baris kosong setelah baris terakhir atau textbox kosong
            if delete_mode == "cursor" and start_line_idx == len(self._actual_api_keys):
                 tk.messagebox.showinfo("Tidak Ada Key", "Tidak ada API key di baris ini untuk dihapus.")
                 return
            self._log(f"Indeks baris awal ({start_line_idx}) tidak valid.", "warning")
            tk.messagebox.showwarning("Indeks Tidak Valid", "Baris target tidak valid untuk dihapus.")
            return

        if delete_mode == "selection" and (end_line_idx < 0 or end_line_idx >= len(self._actual_api_keys) or start_line_idx > end_line_idx):
            self._log(f"Indeks baris akhir seleksi ({end_line_idx}) tidak valid atau tidak konsisten.", "warning")
            tk.messagebox.showwarning("Seleksi Tidak Valid", "Seleksi baris tidak valid untuk dihapus.")
            return

        # Konfirmasi sebelum menghapus
        confirm_message = f"Anda yakin ingin menghapus {num_keys_to_delete} API key yang dipilih secara permanen?" \
                          if delete_mode == "selection" else \
                          f"Anda yakin ingin menghapus API key di baris {start_line_idx + 1} secara permanen?"

        confirm_delete = tk.messagebox.askyesno("Konfirmasi Hapus", confirm_message)
        if not confirm_delete:
            self._log("Penghapusan API key dibatalkan oleh pengguna.", "info")
            return

        # Hapus key dari daftar internal _actual_api_keys
        try:
            del self._actual_api_keys[start_line_idx : end_line_idx + 1]
            self._log(f"{num_keys_to_delete} API key dihapus dari daftar internal (baris {start_line_idx+1} - {end_line_idx+1}).", "info")
            # Perbarui tampilan textbox untuk mencerminkan perubahan
            self._update_api_textbox()
        except IndexError:
            self._log("Error: Indeks di luar jangkauan saat menghapus key dari daftar internal.", "error")
            tk.messagebox.showerror("Error", "Terjadi kesalahan indeks saat mengakses daftar API key.")
        except Exception as e:
            self._log(f"Error saat proses penghapusan dari list: {e}", "error")
            tk.messagebox.showerror("Error", f"Gagal menghapus API key dari daftar: {e}")


    def _toggle_api_key_visibility(self):
        """Toggle visibility of API keys in the textbox."""
        # Update the display based on the new checkbox state
        self._update_api_textbox()
        # No need to update switch text anymore
        # if self.show_api_keys_var.get():
        #     self.show_api_keys_switch.configure(text="Sembunyikan Key")
        # else:
        #     self.show_api_keys_switch.configure(text="Tampilkan Key")


    def _update_api_textbox(self):
        """Update text box API key display based on visibility state."""
        # Store current cursor position and selection
        cursor_pos = self.api_textbox.index(tk.INSERT)
        selection = None
        try:
            selection = self.api_textbox.tag_ranges("sel")
        except tk.TclError:
            pass # No selection

        try:
            self.api_textbox.configure(state=tk.NORMAL)
            self.api_textbox.delete("1.0", tk.END)

            if self.show_api_keys_var.get():
                # Show actual keys
                if self._actual_api_keys:
                    self.api_textbox.insert("1.0", "\n".join(self._actual_api_keys))
            else:
                # Show placeholders (ensure placeholder length is reasonable)
                if self._actual_api_keys:
                    placeholders = ["•" * 39] * len(self._actual_api_keys) # 39 bullet characters placeholder
                    self.api_textbox.insert("1.0", "\n".join(placeholders))

            self.api_textbox.configure(state=tk.NORMAL) 

            # Restore cursor position and selection
            self.api_textbox.mark_set(tk.INSERT, cursor_pos)
            if selection:
                 self.api_textbox.tag_add("sel", selection[0], selection[1])
            self.api_textbox.see(tk.INSERT) # Ensure cursor is visible

        except tk.TclError:
            pass # Ignore Tcl errors which might happen during rapid updates
        except Exception as e:
             self._log(f"Error updating API textbox display: {e}", "error")

    def _get_keys_from_textbox(self):
        """Gets the actual API keys from the internal list."""
        # Always return the actual keys, regardless of display state
        # Sync first in case user typed while keys were visible
        self._sync_actual_keys_from_textbox() 
        return self._actual_api_keys

    def _sync_actual_keys_from_textbox(self, event=None):
        """Update the internal list when user types in the visible textbox."""
        # This should only run if keys are currently visible to avoid overwriting
        # the actual keys with '****' if the user types while hidden.
        if self.show_api_keys_var.get(): 
            try:
                # Get text directly from the widget
                keys_text = self.api_textbox.get("1.0", "end-1c") 
                # Update the internal list
                self._actual_api_keys = [line.strip() for line in keys_text.splitlines() if line.strip()]
            except tk.TclError:
                 self._actual_api_keys = [] # Handle potential Tcl errors
            except Exception as e:
                 # Log error but try to preserve existing keys if possible
                 self._log(f"Error syncing keys from textbox: {e}", "error")
                 # Avoid clearing keys on error, maybe log previous state?
                 # self._actual_api_keys = [] 

    # --- Settings Methods ---
    def _get_config_path(self):
        """Mendapatkan path file konfigurasi."""
        try:
            keys_text = self.api_textbox.get("1.0", "end-1c")
            return [line.strip() for line in keys_text.splitlines() if line.strip()]
        except tk.TclError:
            return []
    
    # --- Settings Methods ---
    def _get_config_path(self):
        """Mendapatkan path file konfigurasi."""
        if os.name == 'nt':
            documents_path = os.path.join(os.environ.get('USERPROFILE', ''), 'Documents')
            if os.path.exists(documents_path):
                config_dir = os.path.join(documents_path, "RJAutoMetadata")
                os.makedirs(config_dir, exist_ok=True)
                return os.path.join(config_dir, CONFIG_FILE)
        
        try:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(base_dir, CONFIG_FILE)
        except Exception as e:
            print(f"Error getting config path: {e}")
            return CONFIG_FILE
    
    def _load_settings(self):
        """Memuat pengaturan dari file konfigurasi."""
        try:
            self._log(f"Mencoba memuat pengaturan...", "info")
            
            if os.path.exists(self.config_path):
                self.analytics_enabled_var.set(True) # Default True untuk instalasi baru
                self.installation_id.set("")
                
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        config_content = f.read()
                        settings = json.loads(config_content)
                        
                        self.input_dir.set(settings.get("input_dir", ""))
                        self.output_dir.set(settings.get("output_dir", ""))
                        self.delay_var.set(str(settings.get("delay", "10")))
                        self.workers_var.set(str(settings.get("workers", "3")))
                        self.rename_files_var.set(settings.get("rename", False))
                        self.auto_kategori_var.set(settings.get("auto_kategori", True))
                        self.auto_foldering_var.set(settings.get("auto_foldering", False))
                        # Load keys into the internal list first
                        self._actual_api_keys = settings.get("api_keys", [])
                        # Load API key visibility state (default to False/hidden if not found)
                        self.show_api_keys_var.set(settings.get("show_api_keys", False))
                        # Load console visibility state (default to True/visible if not found)
                        self.console_visible_var.set(settings.get("console_visible", True))

                        # Load tema
                        loaded_theme = settings.get("theme", "dark")
                        self.theme_var.set(loaded_theme)
                        ctk.set_appearance_mode(loaded_theme)
                        
                        # Load ID instalasi
                        loaded_install_id = settings.get("installation_id")
                        if loaded_install_id:
                            self.installation_id.set(loaded_install_id)
                            self._log(f"ID Instalasi ditemukan: {loaded_install_id[:8]}...", "info")
                        else:
                              self._log("ID Instalasi belum ada di config.", "info")
                        
                        # Update the textbox display after loading internal keys
                        self._update_api_textbox()
                        self._log("Pengaturan lain berhasil dimuat dari konfigurasi", "info")

                        # Set initial console visibility (Windows only)
                        if platform.system() == "Windows":
                             initial_console_state = self.console_visible_var.get()
                             log_message(f"Setting initial console visibility to: {initial_console_state}", "info")
                             set_console_visibility(initial_console_state)
                             # Update switch text after setting initial state
                             self.after(50, self._update_console_toggle_text) # Use 'after' to ensure switch exists

                except Exception as inner_e:
                    self._log(f"Error saat membaca file config: {inner_e}", "error")
            else:
                self._log(f"File config tidak ditemukan", "warning")
                self.analytics_enabled_var.set(True) # Default True untuk instalasi baru
                self.installation_id.set("")
                self._needs_initial_save = True # Mark that settings need saving because config was missing
                self._log("File config baru akan dibuat setelah inisialisasi", "info")
        except Exception as e:
            self._log(f"Error memuat pengaturan: {e}", "error")
            import traceback
            self._log(traceback.format_exc(), "error")
            self.analytics_enabled_var.set(True) # Fallback
            self.installation_id.set("")
    
    def _save_settings(self):
        """Menyimpan pengaturan ke file konfigurasi."""
        # Ensure we save the actual keys from the internal list
        self._sync_actual_keys_from_textbox() # Sync just in case keys were visible and edited
        
        settings = {
            "config_version": "1.0",
            "input_dir": self.input_dir.get(),
            "output_dir": self.output_dir.get(),
            "delay": self.delay_var.get(),
            "workers": self.workers_var.get(),
            "rename": self.rename_files_var.get(),
            "auto_kategori": self.auto_kategori_var.get(),
            "auto_foldering": self.auto_foldering_var.get(),
            "api_keys": self._actual_api_keys, # Save the internal list
            "show_api_keys": self.show_api_keys_var.get(), # Save API key visibility state
            "console_visible": self.console_visible_var.get(), # Save console visibility state
            "theme": self.theme_var.get(),
            "last_saved": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "analytics_enabled": self.analytics_enabled_var.get(),
            "installation_id": self.installation_id.get(),
        }
        
        try:
            config_dir = os.path.dirname(self.config_path)
            if config_dir and not os.path.exists(config_dir):
                self._log(f"Membuat direktori config: {config_dir}", "info")
                os.makedirs(config_dir, exist_ok=True)
                
            if not os.access(config_dir, os.W_OK):
                self._log(f"Warning: Direktori config tidak dapat ditulis: {config_dir}", "warning")
                if os.name == 'nt': 
                    self.config_path = os.path.join(os.environ.get('USERPROFILE', ''), "RJAutoMetadata_config.json")
                    self._log(f"Mencoba fallback ke home dir: {self.config_path}", "info")
                    
            self._log(f"Menyimpan pengaturan...", "info")
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json_data = json.dumps(settings, indent=4)
                f.write(json_data)
                self._log(f"Pengaturan berhasil disimpan ({len(json_data)} bytes)", "info")
        except PermissionError as pe:
            self._log(f"Error izin: {pe}", "error")
            alt_path = os.path.join(os.getcwd(), "rjmetadata_config.json")
            self._log(f"Mencoba menulis ke lokasi alternatif: {alt_path}", "warning")
            
            try:
                with open(alt_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=4)
                self.config_path = alt_path 
                self._log(f"Pengaturan berhasil disimpan ke lokasi alternatif", "info")
            except Exception as alt_e:
                self._log(f"Gagal menulis ke lokasi alternatif: {alt_e}", "error")
        except Exception as e:
            self._log(f"Error menyimpan pengaturan: {e}", "error")
            import traceback
            self._log(traceback.format_exc(), "error")
    
    def _change_theme(self, selected_theme):
        """Mengganti tema aplikasi."""
        try:
            if selected_theme in ["dark", "light", "system"]:
                ctk.set_appearance_mode(selected_theme)
            else:
                theme_file = os.path.join(self.theme_folder, f"{selected_theme}.json")
                if os.path.exists(theme_file):
                    ctk.set_default_color_theme(theme_file)
                else:
                    self._log(f"Tema '{selected_theme}' tidak ditemukan.", "error")
                    return
                    
            self._log(f"Tema diubah ke: {selected_theme}", "info")
            self._update_log_colors()
            self._save_settings()
        except Exception as e:
            self._log(f"Error mengganti tema: {e}", "error")
    
    def _update_log_colors(self):
        """Update warna tag dalam log berdasarkan tema."""
        theme_mode = ctk.get_appearance_mode()
        success_color = ("#21a645")
        error_color = ("#aa0000")
        warning_color = ("#aa5500")
        info_color = ("#000077",)
        cooldown_color = ("#550055")
        
        self.log_text._textbox.tag_configure("success", foreground=success_color)
        self.log_text._textbox.tag_configure("error", foreground=error_color)
        self.log_text._textbox.tag_configure("warning", foreground=warning_color)
        self.log_text._textbox.tag_configure("info", foreground=info_color[0])
        self.log_text._textbox.tag_configure("cooldown", foreground=cooldown_color)
    
    # --- Process Control Methods ---
    def _validate_folders(self):
        """Validasi folder input dan output."""
        input_dir = self.input_dir.get().strip()
        output_dir = self.output_dir.get().strip()
        
        if input_dir and output_dir and os.path.normpath(input_dir) == os.path.normpath(output_dir):
            self.input_entry.configure(border_color=("red", "#aa0000"))
            self.output_entry.configure(border_color=("red", "#aa0000"))
            self.start_button.configure(state=tk.DISABLED)
            return False
        else:
            self.input_entry.configure(border_color=None) 
            self.output_entry.configure(border_color=None)
            
            if self.start_button['state'] == tk.DISABLED and not self.processing_thread:
                self.start_button.configure(state=tk.NORMAL)
                
            return True
    
    def _validate_path_permissions(self, path, check_write=True):
        """Memeriksa izin akses path."""
        try:
            if not os.path.exists(path):
                self._log(f"Path tidak ada: {path}", "info")
                return False
                
            if os.path.isdir(path):
                if check_write:
                    return is_writable_directory(path)
                return True
            elif os.path.isfile(path):
                can_read = os.access(path, os.R_OK)
                can_write = os.access(path, os.W_OK) if check_write else True
                self._log(f"File {path}: bisa dibaca = {can_read}, bisa ditulis = {can_write}", "info")
                return can_read and can_write
                
            return False
        except Exception as e:
            self._log(f"Error validasi path: {e}", "error")
            return False
    
    def _start_processing(self):
        """Memulai proses batch."""
        input_dir = self.input_dir.get().strip()
        output_dir = self.output_dir.get().strip()
        
        # Disable UI
        self._disable_ui_during_processing()
        
        # Validasi input/output
        if not input_dir or not output_dir:
            self._reset_ui_after_processing()
            tk.messagebox.showwarning("Input Kurang", 
                "Harap pilih folder input dan output.")
            return
            
        if os.path.normpath(input_dir) == os.path.normpath(output_dir):
            self._reset_ui_after_processing()
            tk.messagebox.showwarning("Folder Sama", 
                "Folder input dan output tidak boleh sama.\nSilakan pilih folder yang berbeda.")
            return
            
        if not os.path.isdir(input_dir):
            self._reset_ui_after_processing()
            tk.messagebox.showerror("Error", 
                f"Folder input tidak valid:\n{input_dir}")
            return
                
        if not os.path.isdir(output_dir):
            if tk.messagebox.askyesno("Buat Folder?", 
                f"Folder output '{os.path.basename(output_dir)}' tidak ditemukan.\n\nBuat folder?"):
                try:
                    os.makedirs(output_dir)
                except Exception as e:
                    self._reset_ui_after_processing()
                    tk.messagebox.showerror("Error", 
                        f"Gagal membuat folder output:\n{e}")
                    return
            else:
                self._reset_ui_after_processing()
                return
        
        # Validasi API key
        current_api_keys = self._get_keys_from_textbox()
        if not current_api_keys:
            self._reset_ui_after_processing()
            tk.messagebox.showwarning("Input Kurang", 
                "Harap masukkan setidaknya satu API Key.")
            return
        
        # Validasi parameter lain
        try:
            delay_sec = int(self.delay_var.get().strip() or "0")
            if delay_sec < 0:
                delay_sec = 0
            elif delay_sec > 300:
                delay_sec = 300
            self.delay_var.set(str(delay_sec))
        except ValueError:
            self.delay_var.set("10")
            delay_sec = 10
        
        # Validasi jumlah worker
        num_api_keys = len(current_api_keys)
        max_workers = 10
        try:
            num_workers = int(self.workers_var.get().strip() or "3")
            if num_workers <= 0:
                num_workers = 1
            elif num_workers > num_api_keys:
                num_workers = num_api_keys
            elif num_workers > max_workers:
                num_workers = max_workers
            self.workers_var.set(str(num_workers))
        except ValueError:
            self.workers_var.set("3")
            num_workers = 3
        
        # Reset counter dan timer
        self.processed_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.stopped_count = 0
        
        # Siapkan flag untuk pengaturan
        rename_enabled = self.rename_files_var.get()
        auto_kategori_enabled = self.auto_kategori_var.get()
        auto_foldering_enabled = self.auto_foldering_var.get()
        
        # Siapkan dan mulai proses
        self.stop_event.clear()
        self.start_time = time.monotonic()
        self.start_button.configure(state=tk.DISABLED, text="Memproses....")
        self.stop_button.configure(state=tk.NORMAL)
        self.progress_text_var.set(f"Proses: Memulai....")
        
        # Log begin
        self._log("Kompresi otomatis aktif untuk file besar", "warning")
        
        # Kirim analytics jika diaktifkan
        if self.analytics_enabled_var.get():
            self._send_analytics_event("process_started", {
                "input_files_count": -1,  # Akan diupdate nanti
                "workers": num_workers,
                "delay": delay_sec,
                "rename_enabled": rename_enabled,
                "auto_kategori": auto_kategori_enabled,
                "auto_foldering": auto_foldering_enabled
            })
        
        # Mulai thread processing
        self.processing_thread = threading.Thread(
            target=self._run_processing,
            args=(input_dir, output_dir, current_api_keys,
                  rename_enabled, delay_sec, num_workers,
                  auto_kategori_enabled, auto_foldering_enabled),
            daemon=True
        )
        self.processing_thread.start()
    
    def _disable_ui_during_processing(self):
        """Menonaktifkan UI selama pemrosesan berjalan."""
        self.start_button.configure(state=tk.DISABLED)
        self.clear_button.configure(state=tk.DISABLED)
        self.rename_switch.configure(state=tk.DISABLED)
        self.auto_kategori_switch.configure(state=tk.DISABLED)
        self.auto_foldering_switch.configure(state=tk.DISABLED)
        self.api_textbox.configure(state=tk.DISABLED)
        self.theme_dropdown.configure(state=tk.DISABLED)
        self.workers_entry.configure(state=tk.DISABLED)
        self.delay_entry.configure(state=tk.DISABLED)
        self.input_entry.configure(state=tk.DISABLED)
        self.output_entry.configure(state=tk.DISABLED)
        self.load_api_button.configure(state=tk.DISABLED)
        self.save_api_button.configure(state=tk.DISABLED)
        self.delete_api_button.configure(state=tk.DISABLED)
        self.input_button.configure(state=tk.DISABLED)
        self.output_button.configure(state=tk.DISABLED)
    
    def _run_processing(self, input_dir, output_dir, api_keys, rename_enabled, delay_seconds, num_workers, auto_kategori_enabled, auto_foldering_enabled):
        """Thread worker untuk pemrosesan batch."""
        # Import path yang ditemukan saat thread dimulai
        from src.utils.system_checks import GHOSTSCRIPT_PATH as gs_path_found
        log_message(f"Ghostscript path passed to worker thread: {gs_path_found}", "info")

        try:
            # Lakukan pemrosesan batch, teruskan path GS
            result = batch_process_files(
                input_dir=input_dir,
                output_dir=output_dir,
                api_keys=api_keys,
                ghostscript_path=gs_path_found, # Teruskan path GS
                rename_enabled=rename_enabled,
                delay_seconds=delay_seconds,
                num_workers=num_workers,
                auto_kategori_enabled=auto_kategori_enabled,
                auto_foldering_enabled=auto_foldering_enabled,
                progress_callback=self._update_progress,
                stop_event=self.stop_event
            )
            
            # Update counter dari hasil
            self.processed_count = result.get("processed_count", 0)
            self.failed_count = result.get("failed_count", 0)
            self.skipped_count = result.get("skipped_count", 0)
            self.stopped_count = result.get("stopped_count", 0)
            
            # Kirim analytics jika diaktifkan
            if self.analytics_enabled_var.get():
                total_files = result.get("total_files", 0)
                self._send_analytics_event("process_completed", {
                    "total_files": total_files,
                    "processed_count": self.processed_count,
                    "failed_count": self.failed_count,
                    "skipped_count": self.skipped_count,
                    "stopped_count": self.stopped_count,
                    "success_rate": (self.processed_count / total_files) * 100 if total_files > 0 else 0
                })
            
            # Menentukan pesan akhir berdasarkan hasil
            final_message = "Terjadi error tidak dikenal." # Default message

            if result.get("status") == "no_files":
                final_message = "Tidak ada file yang dapat diproses ditemukan di folder input."
                self.progress_text_var.set("Proses: Tidak ada file")
                # Tampilkan messagebox juga untuk kejelasan
                self.after(100, lambda msg=final_message: tk.messagebox.showinfo("Info Proses", msg))
                # Tidak perlu tampilkan completion manager jika tidak ada file
                self.after(200, self._reset_ui_after_processing)
            elif self.stop_event.is_set():
                final_message = "Pemrosesan dihentikan oleh pengguna."
                self.progress_text_var.set("Proses: Dihentikan")
                # Tampilkan completion manager meskipun dihentikan
                self.after(100, lambda: self.completion_manager.show_completion_message())
                self.after(200, self._reset_ui_after_processing)
            else: # Proses selesai secara normal (meskipun mungkin 0 file berhasil)
                final_message = "Pemrosesan selesai!"
                final_completed = self.processed_count + self.failed_count + self.skipped_count + self.stopped_count
                total_files = result.get("total_files", final_completed) # Ambil total dari hasil
                self.progress_text_var.set(f"Proses: {final_completed}/{total_files} file selesai.")
                # Tampilkan completion manager
                self.after(100, lambda: self.completion_manager.show_completion_message())
                self.after(200, self._reset_ui_after_processing)

            # Catatan: Logika pesan akhir bisa disesuaikan lagi jika perlu
            
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            self._log(f"Error fatal dalam processing thread: {e}\nTraceback:\n{tb_str}", "error")
            self.after(0, self._reset_ui_after_processing)
    
    def _update_progress(self, current, total):
        """Update progress bar dan teks status."""
        progress_value = 0 if total == 0 else current / total
        self.progress_bar.set(progress_value)
        
        # Update status text
        progress_percent = (current / total) * 100 if total > 0 else 0
        self.progress_text_var.set(f"Proses: {current}/{total} ({progress_percent:.0f}%)")
        
        # Hitung dan update waktu tersisa
        if self.start_time and current > 0 and current < total:
            elapsed_time = time.monotonic() - self.start_time
            time_per_file = elapsed_time / current
            remaining_files = total - current
            time_left = time_per_file * remaining_files
            
            # elapsed_str = self._format_time(elapsed_time)
            # left_str = self._format_time(time_left)
            # self._log(f"Progres: {current}/{total} - sisa waktu: {left_str}", "info")
        
        self.update_idletasks()
    
    def _format_time(self, seconds):
        """Format waktu dari detik menjadi format jam:menit:detik."""
        if seconds is None or not isinstance(seconds, (int, float)) or seconds < 0:
            return "00:00:00"
            
        hours = int(seconds) // 3600
        minutes = (int(seconds) % 3600) // 60
        secs = int(seconds) % 60
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _stop_processing(self):
        """Menghentikan proses yang sedang berjalan."""
        if self.processing_thread and self.processing_thread.is_alive():
            if tk.messagebox.askyesno("Hentikan Proses", "Hentikan proses? Tugas berjalan akan diberi sinyal stop."):
                self._log("Menerima permintaan berhenti...", "warning")
                self.stop_event.set()
                
                # Set global flag
                from src.api.gemini_api import set_force_stop
                set_force_stop()
                
                self.stop_button.configure(state=tk.DISABLED, text="Menghentikan...")
                self._stop_request_time = time.monotonic()
                self.update_idletasks()
                self.update()
                
                try:
                    if self.is_executable:
                        self._log("Mode executable terdeteksi, menggunakan interrupt force...", "warning")
                    else:
                        self._log("Menghentikan semua proses aktif...", "warning")
                except Exception as e:
                    self._log(f"Error saat mencoba force interrupt: {e}", "error")
                
                self._check_thread_ended() 
        else:
            self.stop_button.configure(state=tk.DISABLED)
            self._reset_ui_after_processing()
    
    def _check_thread_ended(self):
        """Cek apakah thread pemrosesan telah berakhir."""
        self.update_idletasks()
        thread_ended = not self.processing_thread or not self.processing_thread.is_alive()
        force_reset = False
        
        if hasattr(self, '_stop_request_time') and self._stop_request_time is not None:
            elapsed_since_stop = time.monotonic() - self._stop_request_time
            timeout_threshold = 1.5 if self.is_executable else 2.5 
            
            if elapsed_since_stop > timeout_threshold:
                self._log(f"Thread tidak merespons setelah {elapsed_since_stop:.1f} detik, melakukan force reset UI...", "warning")
                force_reset = True
                
                if self.is_executable and self.processing_thread and self.processing_thread.is_alive():
                    self._log("Melakukan hard reset pada thread worker...", "warning")
                    from src.api.gemini_api import set_force_stop
                    set_force_stop()
        
        if thread_ended or force_reset:
            self.after(10, self._reset_ui_after_processing)
        else:
            self.after(50, self._check_thread_ended)
    
    def _reset_ui_after_processing(self):
        """Reset UI ke kondisi awal setelah pemrosesan selesai."""
        try:
            self._stop_request_time = None
            
            # Reset flag
            from src.api.gemini_api import reset_force_stop
            reset_force_stop()
            
            # Reset UI
            self.progress_text_var.set("Proses: Siap memulai")
            self.start_button.configure(state=tk.NORMAL, text="Mulai Proses")
            self.stop_button.configure(state=tk.DISABLED, text="Hentikan")
            self.progress_bar.set(0)
            
            # Reset state
            self.processing_thread = None
            self.start_time = None
            self.stop_event.clear()
            
            # Update
            self.update_idletasks()
            
            # Simpan state
            self._save_cache()
            self._save_settings()
            
            # Re-enable UI
            self.start_button.configure(state=tk.NORMAL)
            self.clear_button.configure(state=tk.NORMAL)
            self.rename_switch.configure(state=tk.NORMAL)
            self.auto_kategori_switch.configure(state=tk.NORMAL)
            self.auto_foldering_switch.configure(state=tk.NORMAL)
            self.workers_entry.configure(state=tk.NORMAL)
            self.theme_dropdown.configure(state=tk.NORMAL)
            self.delay_entry.configure(state=tk.NORMAL)
            self.input_entry.configure(state=tk.NORMAL)
            self.output_entry.configure(state=tk.NORMAL)
            self.load_api_button.configure(state=tk.NORMAL)
            self.save_api_button.configure(state=tk.NORMAL)
            self.delete_api_button.configure(state=tk.NORMAL)
            self.input_button.configure(state=tk.NORMAL)
            self.output_button.configure(state=tk.NORMAL)
        except Exception as e:
            print(f"Error saat reset UI: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                self.start_button.configure(state=tk.NORMAL, text="Mulai Proses")
                self.stop_button.configure(state=tk.DISABLED, text="Hentikan")
                self.update_idletasks()
            except:
                pass
    
    # --- Log Methods ---
    def _log(self, message, tag=None):
        """Menambahkan pesan ke antrian log."""
        self.log_queue.put((message, tag))
    
    def _process_log_queue(self):
        """Memproses antrian log dan menampilkan pesan."""
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple) and len(item) == 2:
                    message, tag = item
                    self._write_to_log(message, tag)
                else:
                    self._write_to_log(item)
        except queue.Empty:
            pass
        finally:
            if self.winfo_exists():
                self._log_queue_after_id = self.after(100, self._process_log_queue)
    
    def _should_display_in_gui(self, message):
        """Memeriksa apakah pesan harus ditampilkan di GUI log."""
        # Pola regex untuk pesan yang diizinkan
        allowed_patterns = [
            r"^Kompresi otomatis aktif untuk file besar$",
            r"^Memulai proses \(\d+ worker, delay \d+s, rotasi API aktif\)$",
            r"^Ditemukan \d+ file untuk diproses$",
            r"^Output CSV akan disimpan di subfolder: metadata_csv$",
            r"^ → Memproses .+\.\w+\.\.\.$",
            r"^Batch \d+: Menunggu hasil \d+ file\.\.\.$",
            r"^✓ .+\.\w+ → .+\.\w+$", # Matches success WITH rename
            r"^✓ .+\.\w+$",          # Matches success WITHOUT rename
            r"^✗ .+\.\w+ \(.*\)$",   # Matches failure messages like ✗ filename (reason)
            r"^✗ .+\.\w+$",
            #r"^⨯ .+$",               # Matches failure messages starting with ⨯
            r"^Cool-down \d+ detik dulu ngabbbb\.\.\.$", # Match the actual message format
            # r"^Menyimpan pengaturan\.\.\.$", # Commented out as it might be too verbose
            # API Key Load/Save messages
            r"^Berhasil memuat \d+ API key$",
            r"^API Keys \(\d+\) disimpan ke file$",
            # Stop/Cancel messages
            r"^Menerima permintaan berhenti\.\.\.$",
            r"^Mode executable terdeteksi, menggunakan interrupt force\.\.\.$",
            r"^Menghentikan semua proses aktif\.\.\.$",
            r"^Thread tidak merespons setelah \d+\.\d+ detik, melakukan force reset UI\.\.\.$",
            r"^Proses dihentikan sebelum mulai \(deteksi awal\)$",
            r"^Stop terdeteksi setelah memproses hasil batch\.$",
            r"^Proses dihentikan oleh pengguna \(deteksi cooldown\)$",
            r"^Membatalkan pekerjaan yang tersisa\.\.\.$",
            # Analytics/Initialization messages
            r"^Membuat ID instalasi baru: .+$",
            r"^ID Instalasi ditemukan: .+\.\.\.$",
            r"^ID Instalasi belum ada di config\.$",
            r"^Mencoba memuat pengaturan\.\.\.$",
            r"^Pengaturan lain berhasil dimuat dari konfigurasi$",
            r"^File config tidak ditemukan$",
            r"^File config baru telah dibuat$",
            # Patterns for summary block lines
            r"^============= Ringkasan Proses =============",
            r"^Total file: \d+$",
            r"^Berhasil diproses: \d+$",
            r"^Gagal: \d+$",
            r"^Dilewati: \d+$",
            r"^Dihentikan: \d+$",
            r"^=========================================$"
        ]

        # Check if message matches any allowed pattern
        for pattern in allowed_patterns:
            if re.match(pattern, message):
                # Handle summary block state
                if message == "============= Ringkasan Proses =============":
                    self._in_summary_block = True
                elif message == "=========================================":
                    self._in_summary_block = False
                return True
        
        # Allow any message if we are inside the summary block
        if self._in_summary_block:
             # Check if this line marks the end of the summary
            if re.match(r"^=========================================$", message):
                self._in_summary_block = False # Reset flag after matching end marker
            return True

        return False

    def _write_to_log(self, message, tag=None):
        """Menulis pesan ke log text box, setelah difilter."""
        # Filter pesan sebelum menulis ke GUI
        if not self._should_display_in_gui(message):
            # Reset summary flag if message is outside summary block logic but flag is true
            # This handles cases where the end marker might be missed or processing stops mid-summary
            if self._in_summary_block and not message.startswith("="): 
                 self._in_summary_block = False
            return # Jangan tampilkan pesan ini di GUI

        try:
            self.log_text.configure(state=tk.NORMAL)
            
            # Auto-detect tag based on message content (only for displayed messages)
            if tag is None:
                if message.startswith("✓"):
                    tag = "success"
                elif message.startswith("✗"):
                    tag = "error"
                elif message.startswith("⋯"):
                    tag = "info"
                elif "Error" in message or "Gagal" in message:
                    tag = "error"
                elif "Warning" in message:
                    tag = "warning"
                elif "Cool-down" in message:
                    tag = "cooldown"
                elif "===" in message:
                    tag = "bold"
            
            # Add timestamp for normal messages
            if not message.startswith((" ✓", " ⋯", " ✗", " ⊘")) or message.startswith("==="):
                timestamp = time.strftime("%H:%M:%S")
                self.log_text._textbox.insert(tk.END, f"[{timestamp}] ", "")
                self.log_text._textbox.insert(tk.END, f"{message}\n", tag if tag else "")
            else:
                self.log_text._textbox.insert(tk.END, f"{message}\n", tag if tag else "")
            
            # Auto scroll to end
            self.log_text._textbox.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
        except tk.TclError:
            pass
    
    def _clear_log(self):
        """Membersihkan isi log text box."""
        try:
            self.log_text.configure(state=tk.NORMAL)
            self.log_text._textbox.delete("1.0", tk.END)
            self.log_text.configure(state=tk.DISABLED)
        except tk.TclError:
            pass
    
    def on_closing(self):
        """Callback saat window ditutup."""
        try:
            self._save_settings()
            self._save_cache()
            
            if self.processing_thread and self.processing_thread.is_alive():
                if tk.messagebox.askyesno("Keluar", 
                        "Proses sedang berjalan. Yakin ingin keluar?\nProses akan dihentikan."):
                    self.stop_event.set()
                    
                    # Set global flag
                    from src.api.gemini_api import set_force_stop
                    set_force_stop()
                    
                    self.after(300, self._force_close)
                return
                
            self._force_close()
        except Exception as e:
            print(f"Error saat menutup aplikasi: {e}")
            self.destroy()
    
    def _force_close(self):
        """Tutup aplikasi secara paksa."""
        if hasattr(self, '_log_queue_after_id') and self._log_queue_after_id:
            try:
                self.after_cancel(self._log_queue_after_id)
            except tk.TclError:
                pass
        self.destroy()

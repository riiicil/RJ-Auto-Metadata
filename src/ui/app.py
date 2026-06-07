# RJ Auto Metadata
# Copyright (C) 2026 Riiicil
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
import re
import sys
import uuid
import webbrowser
import tkinter as tk
import tkinter.messagebox
import customtkinter as ctk
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from src.utils.logging import log_message
from src.utils.file_utils import read_api_keys, is_writable_directory
from src.utils.analytics import send_analytics_event
from src.config.config import MEASUREMENT_ID, API_SECRET, ANALYTICS_URL
from src.processing.batch_processing import batch_process_files
from src.api import provider_manager
from src.ui.widgets import ToolTip
from src.ui.CTkScrollableDropdown import CTkScrollableDropdown
from src.ui.dialogs import CompletionMessageManager
from src.utils.system_checks import (check_ghostscript, check_ffmpeg, check_gtk_dependencies,set_console_visibility)
from src.metadata.exif_writer import check_exiftool_exists
from src.api.api_key_checker import check_api_keys_status

APP_VERSION = "3.12.3"
CONFIG_FILE = "config.json"

class MetadataApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.default_font_family = "Aptos_display"
        from src.utils.logging import set_log_handler
        set_log_handler(self._log)
        def font_exists(font_name):
            try:
                test_label = tk.Label(text="Test", font=(font_name, 12))
                exists = test_label.cget("font").split()[0] == font_name
                test_label.destroy()
                return exists
            except Exception:
                return False

        if not font_exists(self.default_font_family):
            self._log(f"Font '{self.default_font_family}' not found, using default system font", "warning")
            self.default_font_family = "Arial"

        self.font_small = ctk.CTkFont(family=self.default_font_family, size=10)
        self.font_normal = ctk.CTkFont(family=self.default_font_family, size=12)
        self.font_medium = ctk.CTkFont(family=self.default_font_family, size=13)
        self.font_large = ctk.CTkFont(family=self.default_font_family, size=15, weight="bold")
        self.font_title = ctk.CTkFont(family=self.default_font_family, size=18, weight="bold")

        self.start_time = None
        self.processing_thread = None
        self.selected_provider = provider_manager.get_default_provider()
        self.available_providers = provider_manager.list_providers()
        if not self.available_providers:
            self.available_providers = [self.selected_provider]
        if self.selected_provider not in self.available_providers:
            self.selected_provider = self.available_providers[0]
        from src.api import provider_manager as _pm
        if _pm.PROVIDER_CUSTOM not in self.available_providers:
            self.available_providers.append(_pm.PROVIDER_CUSTOM)
        self.api_keys_by_provider = {name: [] for name in self.available_providers}
        self._models_by_provider: dict[str, list] = {
            name: [] for name in self.available_providers
        }
        self._selected_model_by_provider: dict[str, str] = {}
        self.provider_var = tk.StringVar(value=self.selected_provider)
        self._actual_api_keys = list(self.api_keys_by_provider.get(self.selected_provider, []))
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self._log_queue_after_id = None
        self._stop_request_time = None
        self._in_summary_block = False

        self._perform_startup_checks()

        self.configure(fg_color=("#f0f0f5", "#2d2d30"))

        self.analytics_enabled_var = tk.BooleanVar(value=True)
        self.installation_id = tk.StringVar(value="")

        self.title("Auto Metadata")

        from src.utils.system_checks import _get_base_dir
        base_dir = _get_base_dir()

        try:
            self.iconbitmap_path = os.path.join(base_dir, 'assets', 'icon1.ico')
            if os.path.exists(self.iconbitmap_path):
                self.iconbitmap(self.iconbitmap_path)
            else:
                self.iconbitmap_path = None
        except Exception as e:
            self.iconbitmap_path = None

        self.geometry("600x700")
        self.minsize(600, 700)

        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.rename_files_var = tk.BooleanVar(value=False)
        self.delay_var = tk.StringVar(value="10")
        self.workers_var = tk.StringVar(value="1")
        self.extra_settings_var = tk.BooleanVar(value=False) 
        self.console_visible_var = tk.BooleanVar(value=True)

        self.processed_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.stopped_count = 0

        self.theme_folder = os.path.join(os.path.dirname(__file__), "themes")
        self.available_themes = ["dark", "light", "system"]

        if os.path.exists(self.theme_folder):
            import glob
            custom_themes = glob.glob(os.path.join(self.theme_folder, "*.json"))
            for theme_path in custom_themes:
                theme_name = os.path.splitext(os.path.basename(theme_path))[0]
                self.available_themes.append(theme_name)

        self.config_path = self._get_config_path()
        self.processed_cache = {}
        self.cache_file = os.path.join(os.path.dirname(self.config_path), "processed_cache.json")

        self.auto_kategori_var = tk.BooleanVar(value=False)
        self.auto_foldering_var = tk.BooleanVar(value=False)
        self.auto_retry_var = tk.BooleanVar(value=True)
        self._needs_initial_save = False

        self.available_models = provider_manager.get_model_choices(self.selected_provider)
        default_model = provider_manager.get_default_model(self.selected_provider)
        if default_model not in self.available_models and self.available_models:
            default_model = self.available_models[0]
        self.model_var = tk.StringVar(value=default_model)
        self.keyword_count_var = tk.StringVar(value="49")
        self.priority_var = tk.StringVar(value="Detailed")
        self.priority_var.trace_add("write", lambda *_: self._on_quality_change())
        
        self.embedding_var = tk.StringVar(value="Enable")
        self.available_embedding = ["Enable", "Disable"]
        self.available_priorities = ["Detailed", "Balanced", "Less", "Custom"]

        # Advanced tab variables
        self.hint_var = tk.StringVar(value="")
        self.custom_instruction_var = tk.StringVar(value="")
        self.inject_keywords_var = tk.StringVar(value="")
        self.title_min_words_var = tk.StringVar(value="6")
        self.title_max_chars_var = tk.StringVar(value="180")
        self.desc_min_words_var = tk.StringVar(value="6")
        self.desc_max_chars_var = tk.StringVar(value="180")

        # Shadow vars: hold user-edited Custom limits separately from displayed values
        self._custom_title_min = "6"
        self._custom_title_max = "180"
        self._custom_desc_min = "6"
        self._custom_desc_max = "180"
        self._last_quality = "Detailed"  # track previous quality to know when to save shadow

        self._create_ui()
        self._process_log_queue()
        self._load_settings()
        self._init_analytics()
        self._load_cache()

        if self._needs_initial_save:
            self._save_settings()
            self._needs_initial_save = False

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Auto-fetch models on startup if API keys exist for the active provider
        self.after(500, self._auto_fetch_models)

        self.is_executable = self._is_running_as_executable()

        self.completion_manager = CompletionMessageManager(
            self,
            self.config_path,
            self.font_normal,
            self.font_medium,
            self.font_large,
            self.iconbitmap_path
        )

        if self.is_executable:
            print("Application is running as executable.")
            self.executable_timeout = 2.0
            self.executable_max_wait = 5.0
        else:
            print("Application is running as script Python.")
            self.executable_timeout = 3.0
            self.executable_max_wait = 10.0

    def _perform_startup_checks(self):
        self._log("Checking external dependencies...", "info")

        self._log("Checking availability of Exiftool...", "info")
        exiftool_ok = check_exiftool_exists()
        if not exiftool_ok:
            self._log("Exiftool not found.", "error")
            tkinter.messagebox.showerror("Critical Error",
                "Exiftool not found or not working.\n"
                "Application cannot run without Exiftool.\n"
                "Please make sure it is installed and in PATH.")
            self.destroy()
            sys.exit(1)
        else:
            self._log("Exiftool found.", "success")

        self._log("Checking availability of Ghostscript...", "info")
        gs_ok = check_ghostscript()
        if not gs_ok:
            self._log("Ghostscript not found. Processing AI/EPS will fail.", "warning")
            tkinter.messagebox.showwarning("Warning",
                "Ghostscript not found or not working.\n"
                "Please make sure it is installed and in PATH.\n"
                "Processing AI/EPS will fail.")
        else:
            self._log("Ghostscript found.", "success")

        self._log("Checking availability of FFmpeg...", "info")
        ffmpeg_ok = check_ffmpeg()
        if not ffmpeg_ok:
            self._log("FFmpeg not found. Processing Video will fail.", "warning")
            tkinter.messagebox.showwarning("Warning",
                "FFmpeg not found or not working.\n"
                "Please make sure it is installed and in PATH.\n"
                "Processing Video (MP4/MKV) will fail.")
        else:
            self._log("FFmpeg ditemukan.", "success")

        self._log("Checking availability of GTK dependencies (cairocffi)...", "info")
        gtk_ok = check_gtk_dependencies()
        if not gtk_ok:
            self._log("GTK dependencies (cairocffi) not found. Processing SVG might fail.", "warning")
            tkinter.messagebox.showwarning("Warning",
                "Failed to import GTK dependencies (cairocffi).\n"
                "This might be due to missing GTK3 Runtime or incorrect configuration.\n"
                "Processing SVG might fail.")
        else:
             self._log("GTK dependencies (cairocffi) found.", "success")

        self._log("Dependency checks completed.", "info")


    def _is_running_as_executable(self):
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

    def _create_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_panel = ctk.CTkFrame(self, corner_radius=10)
        main_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        main_panel.grid_columnconfigure(0, weight=1)
        main_panel.grid_rowconfigure(0, weight=0)
        main_panel.grid_rowconfigure(1, weight=0)
        main_panel.grid_rowconfigure(2, weight=0)
        main_panel.grid_rowconfigure(3, weight=1)

        settings_center_status_frame = ctk.CTkFrame(main_panel, fg_color="transparent")
        settings_center_status_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        settings_center_status_frame.grid_columnconfigure(0, weight=1)

        self._create_folder_frame(main_panel)
        self._create_combined_api_settings_frame(settings_center_status_frame)
        self._create_log_frame(main_panel)
        self._create_watermark(main_panel)
        self._create_footer(main_panel)

        main_panel.grid_rowconfigure(3, weight=1)

    def _create_folder_frame(self, parent):
        folder_frame = ctk.CTkFrame(parent, corner_radius=8)
        folder_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(folder_frame, text="Input Folder:").grid( row=1, column=0, padx=10, pady=5, sticky="w")
        self.input_entry = ctk.CTkEntry(folder_frame, textvariable=self.input_dir)
        self.input_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.input_button = ctk.CTkButton(folder_frame, text="Browse", command=self._select_input_folder, width=70, fg_color="#079183")
        self.input_button.grid(row=1, column=2, padx=5, pady=5)

        ctk.CTkLabel(folder_frame, text="Output Folder:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.output_entry = ctk.CTkEntry(folder_frame, textvariable=self.output_dir)
        self.output_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.output_button = ctk.CTkButton(folder_frame, text="Browse", command=self._select_output_folder, width=70, fg_color="#079183")
        self.output_button.grid(row=2, column=2, padx=5, pady=5)

        folder_tooltip_text = "Input and Output must be different.\nDo not use the same folder for both."
        ToolTip(self.input_entry, folder_tooltip_text)
        ToolTip(self.output_entry, folder_tooltip_text)

    

    def _cek_api_keys(self):
        api_keys = self._get_keys_from_textbox()
        if not api_keys:
            self._log("No API key to check.", "warning")
            return
        self.cek_api_button.configure(state=tk.DISABLED)
        self._log("Checking status of all API keys...", "info")
        try:
            provider_name = self.provider_var.get() if hasattr(self, "provider_var") else self.selected_provider
            base_url_for_check = None
            if provider_name == provider_manager.PROVIDER_CUSTOM and hasattr(self, "_custom_base_url_var"):
                base_url_for_check = self._custom_base_url_var.get().strip() or None
                if not base_url_for_check:
                    self._log("Custom provider requires a Base URL before checking keys.", "warning")
                    self.cek_api_button.configure(state=tk.NORMAL)
                    return
            results = check_api_keys_status(
                api_keys,
                model=self.model_var.get(),
                provider=provider_name,
                base_url_override=base_url_for_check,
            )
            ok_keys = [k for k, (s, msg) in results.items() if s == 200]
            err_keys = [(k, s, msg) for k, (s, msg) in results.items() if s != 200]
            if len(ok_keys) == len(api_keys):
                self._log(f"All API keys OK ({len(ok_keys)}/{len(api_keys)})", "success")
            else:
                self._log(f"{len(ok_keys)} API keys OK, {len(err_keys)} API key errors:", "warning")
                for k, s, msg in err_keys:
                    self._log(f"  - ...{k[-5:]}: {s} - {msg}", "error")
        except Exception as e:
            self._log(f"Error checking API key: {e}", "error")
        self.cek_api_button.configure(state=tk.NORMAL)

    def _create_combined_api_settings_frame(self, parent):
        """Combined API Keys + Settings frame with auto-hide API keys"""
        combined_frame = ctk.CTkFrame(parent, corner_radius=6)
        combined_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        combined_frame.grid_columnconfigure(0, weight=1)
        
        # API Keys Section
        api_section = ctk.CTkFrame(combined_frame, corner_radius=6)
        api_section.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        api_section.grid_columnconfigure(0, weight=1)  # api textbox / url field
        api_section.grid_columnconfigure(1, weight=0)  # check / provider / model (left half)
        api_section.grid_columnconfigure(2, weight=0)  # fetch / provider / model (right half)
        api_section.grid_columnconfigure(3, weight=0)  # action buttons

        # Row 1 (a) col 0: API Textbox — spans rows 1 and 2
        self.api_textbox = ctk.CTkTextbox(
            api_section, height=90, corner_radius=5, wrap=tk.WORD, font=self.font_normal
        )
        self.api_textbox.grid(row=1, column=0, rowspan=2, padx=7, pady=(10, 0), sticky="new")
        self.api_textbox.bind("<KeyRelease>", self._sync_actual_keys_from_textbox_with_autohide)
        self.api_textbox.bind("<FocusOut>", self._sync_actual_keys_from_textbox_with_autohide)

        # Row 1 (a) col 1: Check button
        self.cek_api_button = ctk.CTkButton(
            api_section, text="Check", width=70,
            command=self._cek_api_keys, fg_color="#079183", height=35
        )
        self.cek_api_button.grid(row=1, column=1, padx=(7, 3), pady=10, sticky="ew")

        # Row 1 (a) col 2: Fetch button
        self.save_api_button = ctk.CTkButton(
            api_section, text="Fetch", width=70,
            command=self._fetch_models, fg_color="#079183", height=35
        )
        self.save_api_button.grid(row=1, column=2, padx=(3, 7), pady=10, sticky="ew")

        # Row 2 (b) col 1+2: Provider dropdown (spans 2 columns)
        self.provider_dropdown = ctk.CTkComboBox(
            api_section,
            values=self.available_providers,
            variable=self.provider_var,
            command=self._on_provider_change,
            justify='center',
            state='readonly'
        )
        self.provider_dropdown.grid(row=2, column=1, columnspan=2, padx=7, pady=(0, 10), sticky="ewn")
        self.provider_dropdown.set(self.provider_var.get())
        self._provider_scrollable = CTkScrollableDropdown(self.provider_dropdown, values=self.available_providers, justify='center', button_color='transparent', frame_corner_radius=8, width=125, height=120, command=self._on_provider_change)

        # Row 3 (c) col 0: URL entry field — always visible, read-only for built-in providers
        self._custom_base_url_var = tk.StringVar(value="")
        self._base_url_entry = ctk.CTkEntry(
            api_section,
            textvariable=self._custom_base_url_var,
            placeholder_text="https://your-endpoint/v1",
            font=self.font_normal,
        )
        self._base_url_entry.grid(row=3, column=0, padx=7, pady=(0, 10), sticky="ewn")

        # Row 3 (c) col 1+2: Model dropdown (spans 2 columns)
        self.model_dropdown = ctk.CTkComboBox(
            api_section,
            values=self.available_models,
            variable=self.model_var,
            width=120,
            justify='center',
            state='readonly'
        )
        self.model_dropdown.grid(row=3, column=1, columnspan=2, padx=7, pady=(0, 5), sticky="ewn")
        self._model_scrollable = CTkScrollableDropdown(self.model_dropdown, values=self.available_models, justify='left', button_color='transparent', frame_corner_radius=8, width=300)

        # Col 3 rows 1-3: Action buttons frame
        process_buttons = ctk.CTkFrame(api_section, fg_color="transparent")
        process_buttons.grid(row=1, column=3, rowspan=3, padx=7, pady=10, sticky="nsew")

        self.start_button = ctk.CTkButton(
            process_buttons, text="Start Processing",
            command=self._start_processing, font=self.font_medium, height=35, fg_color="#079183"
        )
        self.start_button.pack(pady=5, fill=tk.X)

        self.stop_button = ctk.CTkButton(
            process_buttons, text="Stop Processing",
            command=self._stop_processing, font=self.font_medium, height=35,
            state=tk.DISABLED, fg_color=("#bf3a3a", "#8d1f1f")
        )
        self.stop_button.pack(pady=5, fill=tk.BOTH)

        self.clear_button = ctk.CTkButton(
            process_buttons, text="Clear Log",
            command=self._clear_log, font=self.font_medium, height=35, fg_color="#079183"
        )
        self.clear_button.pack(pady=5, fill=tk.BOTH)

        # Set initial URL field state and value
        self._update_base_url_field()
        
        
        # Settings Tabview
        self.settings_tabview = ctk.CTkTabview(
            combined_frame,
            fg_color="transparent",
            segmented_button_fg_color=("gray85", "gray25"),
            segmented_button_selected_color="#079183",
            segmented_button_selected_hover_color="#057a6e",
            segmented_button_unselected_color=("gray85", "gray25"),
            segmented_button_unselected_hover_color=("gray75", "gray35"),
            border_width=0,
            corner_radius=6,
            height=130,
        )
        self.settings_tabview.grid(row=1, column=0, padx=5, pady=(0, 0), sticky="ew")
        self.settings_tabview.add("Settings")
        self.settings_tabview.add("Advanced")

        settings_tab = self.settings_tabview.tab("Settings")
        settings_tab.grid_columnconfigure(0, weight=1)
        settings_tab.grid_columnconfigure(1, weight=1)
        settings_tab.grid_columnconfigure(2, weight=1)
        
        # Settings Column 1 - Basic Settings
        settings_col1 = ctk.CTkFrame(settings_tab, fg_color="transparent")
        settings_col1.grid(row=0, column=0, padx=(0, 3), pady=0, sticky="nsew")
        settings_col1.grid_columnconfigure(1, weight=1)
        
# #         settings_header_tooltip = """
# # Configuration of application behavior:

# # • Keywords: Number of keywords/tags taken from API results (min 8, max 49)
# # • Workers: Number of parallel threads for processing files (e.g. 1-10)
# # • Delay (s): Time delay (seconds) between API requests

# # *NB: This setting is automatically saved for the next session.
# # """
#         settings_header = self._create_header_with_help(settings_col1, "Settings", settings_header_tooltip, font=ctk.CTkFont(size=15, weight="bold"))
#         settings_header.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="wns")
        
        ctk.CTkLabel(settings_col1, text="Keywords:", font=self.font_normal).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.keyword_entry = ctk.CTkEntry(settings_col1, textvariable=self.keyword_count_var, width=100, justify='center', font=self.font_normal)
        self.keyword_entry.grid(row=1, column=1, padx=5, pady=5, sticky="wns")
        
        ctk.CTkLabel(settings_col1, text="Workers:", font=self.font_normal).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.workers_entry = ctk.CTkEntry(settings_col1, textvariable=self.workers_var, width=100, justify='center', font=self.font_normal)
        self.workers_entry.grid(row=2, column=1, padx=5, pady=5, sticky="wns")
        
        ctk.CTkLabel(settings_col1, text="Delay (s):", font=self.font_normal).grid(row=3, column=0, padx=10, pady=5, sticky="wns")
        self.delay_entry = ctk.CTkEntry(settings_col1, textvariable=self.delay_var, width=100, justify='center', font=self.font_normal)
        self.delay_entry.grid(row=3, column=1, padx=5, pady=5, sticky="wns")
        
        # Settings Column 2 - Model & Quality
        settings_col2 = ctk.CTkFrame(settings_tab, fg_color="transparent")
        settings_col2.grid(row=0, column=1, padx=3, pady=0, sticky="nsew")
        settings_col2.grid_columnconfigure(1, weight=1)
        
        # model_header = ctk.CTkLabel(settings_col2, text="Model & Quality", font=ctk.CTkFont(size=15, weight="bold"))
        # model_header.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="wns")
        
        ctk.CTkLabel(settings_col2, text="Theme:", font=self.font_normal).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.theme_var = tk.StringVar(value="dark")
        self.theme_dropdown = ctk.CTkComboBox(settings_col2, values=self.available_themes, variable=self.theme_var, command=self._change_theme, width=120, justify='center', state='readonly')
        self.theme_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="ns")
        CTkScrollableDropdown(self.theme_dropdown, values=self.available_themes, justify='center', button_color='transparent', frame_corner_radius=8, width=100, height=95, command=self._change_theme)
        
        ctk.CTkLabel(settings_col2, text="Quality:", font=self.font_normal).grid(row=2, column=0, padx=10, pady=5, sticky="wns")
        self.priority_dropdown = ctk.CTkComboBox(settings_col2, values=self.available_priorities, variable=self.priority_var, width=120, justify='center', state='readonly')
        self.priority_dropdown.grid(row=2, column=1, padx=5, pady=5, sticky="ns")
        CTkScrollableDropdown(self.priority_dropdown, values=self.available_priorities, justify='center', button_color='transparent', frame_corner_radius=8, width=100, height=95)
        
        ctk.CTkLabel(settings_col2, text="Embed:", font=self.font_normal).grid(row=3, column=0, padx=10, pady=5, sticky="wns")
        self.embedding_dropdown = ctk.CTkComboBox(settings_col2, values=self.available_embedding, variable=self.embedding_var, width=120, justify='center', state='readonly')
        self.embedding_dropdown.grid(row=3, column=1, padx=5, pady=5, sticky="ns")
        CTkScrollableDropdown(self.embedding_dropdown, values=self.available_embedding, justify='center', button_color='transparent', frame_corner_radius=8, width=100, height=70)
        
        # Settings Column 3 - Switches
        settings_col3 = ctk.CTkFrame(settings_tab, fg_color="transparent")
        settings_col3.grid(row=0, column=2, padx=(3, 0), pady=0, sticky="nesw")
        settings_col3.grid_columnconfigure(0, weight=1)
        
        # switches_header = ctk.CTkLabel(settings_col3, text="Options", font=ctk.CTkFont(size=15, weight="bold"))
        # switches_header.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.rename_switch = ctk.CTkSwitch(settings_col3, text="Rename File?", variable=self.rename_files_var, font=self.font_normal)
        self.rename_switch.grid(row=1, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.auto_kategori_switch = ctk.CTkSwitch(settings_col3, text="Auto Category?", variable=self.auto_kategori_var, font=self.font_normal)
        self.auto_kategori_switch.grid(row=2, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.auto_foldering_switch = ctk.CTkSwitch(settings_col3, text="Auto Foldering?", variable=self.auto_foldering_var, font=self.font_normal)
        self.auto_foldering_switch.grid(row=3, column=0, padx=10, pady=(10, 5), sticky="w")

        # Advanced tab — prompt customization controls (3 sub-frames in 1 row)
        adv_tab = self.settings_tabview.tab("Advanced")
        adv_tab.grid_columnconfigure(0, weight=1)
        adv_tab.grid_columnconfigure(1, weight=0)
        adv_tab.grid_columnconfigure(2, weight=0)
        adv_tab.grid_rowconfigure(0, weight=1)

        # Col 0 — Instructions label + textarea
        adv_col0 = ctk.CTkFrame(adv_tab, fg_color="transparent")
        adv_col0.grid(row=0, column=0, padx=(0, 3), pady=0, sticky="nsew")
        adv_col0.grid_columnconfigure(0, weight=1)
        adv_col0.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            adv_col0, text="Instructions:", font=self.font_normal, anchor="w"
        ).grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.instruction_textbox = ctk.CTkTextbox(
            adv_col0, font=self.font_normal, wrap="word",
            height=72, corner_radius=5,
        )
        self.instruction_textbox.grid(
            row=1, column=0, padx=10, pady=(2, 5), sticky="nsew"
        )

        def _on_instruction_change(event=None):
            self.custom_instruction_var.set(
                self.instruction_textbox.get("1.0", "end-1c")
            )
        self.instruction_textbox.bind("<KeyRelease>", _on_instruction_change)
        self.instruction_textbox.bind("<FocusOut>", _on_instruction_change)

        # Col 1 — Hint label + textarea (mirrors Instructions)
        adv_col1 = ctk.CTkFrame(adv_tab, fg_color="transparent")
        adv_col1.grid(row=0, column=1, padx=3, pady=0, sticky="nsew")
        adv_col1.grid_columnconfigure(0, weight=1)
        adv_col1.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            adv_col1, text="Hint:", font=self.font_normal, anchor="w"
        ).grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.hint_textbox = ctk.CTkTextbox(
            adv_col1, font=self.font_normal, wrap="word",
            height=72, width=120, corner_radius=5,
        )
        self.hint_textbox.grid(
            row=1, column=0, padx=10, pady=(2, 5), sticky="nsew"
        )

        def _on_hint_change(event=None):
            self.hint_var.set(self.hint_textbox.get("1.0", "end-1c"))
        self.hint_textbox.bind("<KeyRelease>", _on_hint_change)
        self.hint_textbox.bind("<FocusOut>", _on_hint_change)

        # Col 2 — Title/Desc limits + Inject KW
        adv_col2 = ctk.CTkFrame(adv_tab, fg_color="transparent")
        adv_col2.grid(row=0, column=2, padx=(3, 0), pady=0, sticky="nsew")
        adv_col2.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(adv_col2, text="Title:", font=self.font_normal).grid(
            row=0, column=0, padx=(10, 2), pady=5, sticky="w"
        )
        ctk.CTkLabel(adv_col2, text="\u25bc", font=self.font_small).grid(
            row=0, column=1, padx=(2, 0), pady=5, sticky="e"
        )
        self.title_min_entry = ctk.CTkEntry(
            adv_col2, textvariable=self.title_min_words_var,
            width=40, justify="center", font=self.font_normal,
        )
        self.title_min_entry.grid(row=0, column=2, padx=2, pady=5, sticky="w")
        ctk.CTkLabel(adv_col2, text="\u25b2", font=self.font_small).grid(
            row=0, column=3, padx=(2, 0), pady=5, sticky="e"
        )
        self.title_max_entry = ctk.CTkEntry(
            adv_col2, textvariable=self.title_max_chars_var,
            width=40, justify="center", font=self.font_normal,
        )
        self.title_max_entry.grid(row=0, column=4, padx=(2, 5), pady=5, sticky="w")

        ctk.CTkLabel(adv_col2, text="Desc:", font=self.font_normal).grid(
            row=1, column=0, padx=(10, 2), pady=5, sticky="w"
        )
        ctk.CTkLabel(adv_col2, text="\u25bc", font=self.font_small).grid(
            row=1, column=1, padx=(2, 0), pady=5, sticky="e"
        )
        self.desc_min_entry = ctk.CTkEntry(
            adv_col2, textvariable=self.desc_min_words_var,
            width=40, justify="center", font=self.font_normal,
        )
        self.desc_min_entry.grid(row=1, column=2, padx=2, pady=5, sticky="w")
        ctk.CTkLabel(adv_col2, text="\u25b2", font=self.font_small).grid(
            row=1, column=3, padx=(2, 0), pady=5, sticky="e"
        )
        self.desc_max_entry = ctk.CTkEntry(
            adv_col2, textvariable=self.desc_max_chars_var,
            width=40, justify="center", font=self.font_normal,
        )
        self.desc_max_entry.grid(row=1, column=4, padx=(2, 5), pady=5, sticky="w")

        ctk.CTkLabel(adv_col2, text="Inject KW:", font=self.font_normal).grid(
            row=2, column=0, padx=(10, 2), pady=5, sticky="w"
        )
        self.inject_kw_entry = ctk.CTkEntry(
            adv_col2, textvariable=self.inject_keywords_var, width=100,
            justify="left", font=self.font_normal,
            placeholder_text="e.g. nature,forest",
        )
        self.inject_kw_entry.grid(row=2, column=1, columnspan=4, padx=(2, 5), pady=5, sticky="ew")


    def _create_log_frame(self, parent):
        log_frame = ctk.CTkFrame(parent, corner_radius=8)
        log_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(log_frame, wrap=tk.WORD, height=150, font=self.font_normal)
        self.log_text.grid(row=0, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.log_text.configure(state=tk.DISABLED)

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
        bottom_frame = ctk.CTkFrame(parent, fg_color="transparent")
        bottom_frame.grid(row=4, column=0, padx=5, pady=(0, 5), sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(1, weight=1)

        if platform.system() == "Windows":
            self.console_toggle_switch = ctk.CTkSwitch(
                bottom_frame,
                text="",
                variable=self.console_visible_var,
                command=self._toggle_console_visibility,
                font=self.font_small
            )
            self.console_toggle_switch.grid(row=0, column=0, sticky="w", padx=(10, 5))
            ToolTip(self.console_toggle_switch, "Show/Hide Console Window")

        watermark_label = ctk.CTkLabel(bottom_frame, text=f"© Riiicil 2026 - Ver {APP_VERSION}", font=ctk.CTkFont(size=10), text_color=("gray50", "gray70"))
        watermark_label.grid(row=0, column=1, sticky="e", padx=(5, 10))
        
    def _create_footer(self, parent):
        footer_frame = ctk.CTkFrame(parent, fg_color="transparent")
        footer_frame.grid(row=4, padx=5, pady=(0, 5))
        footer_frame.grid_columnconfigure(0, weight=1)

        footer_text = (
            "This tool is FREE. If you paid, you were scammed.\n"
            "Official version only available at: s.id/riiicil"
        )

        footer_label = ctk.CTkLabel(
            footer_frame,
            text=footer_text,
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray70"),
            justify="center"
        )
        footer_label.grid(row=0, column=0, sticky="n", padx=10)


    def _toggle_console_visibility(self):
        if platform.system() == "Windows":
            show = self.console_visible_var.get()
            set_console_visibility(show)
            self._update_console_toggle_text()
            self._save_settings()
        else:
             log_message("Console toggle attempted on non-Windows system.", "warning")

    def _update_console_toggle_text(self):
         if platform.system() == "Windows" and hasattr(self, 'console_toggle_switch'):
             pass

    def _create_header_with_help(self, parent, text, tooltip_text, font=None):
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")

        if font:
            header_label = ctk.CTkLabel(header_frame, text=text, font=font)
        else:
            header_label = ctk.CTkLabel(header_frame, text=text, font=("Segoe UI", 12, "bold"))

        header_label.pack(side=tk.LEFT, padx=(0, 5))

        help_icon_size = 16
        help_icon = ctk.CTkLabel(header_frame, text="?", width=help_icon_size, height=help_icon_size, fg_color=("#3a7ebf", "#1f538d"), corner_radius=8, text_color="white", font=("Segoe UI", 10, "bold"))
        help_icon.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(help_icon, tooltip_text)

        return header_frame

    def _create_center_frame(self, parent):
        center_frame = ctk.CTkFrame(parent, corner_radius=8)
        center_frame.grid(row=0, column=1, padx=3, pady=0, sticky="nsew")
        center_frame.grid_columnconfigure(1, weight=1)

        self.theme_var = tk.StringVar(value="dark")
        self.theme_dropdown = ctk.CTkComboBox(center_frame, values=self.available_themes, variable=self.theme_var, command=self._change_theme, width=120, justify='center')
        ctk.CTkLabel(center_frame, text="Theme:", font=self.font_normal).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.theme_dropdown.grid(row=2, column=1, padx=5, pady=5, sticky="ns")
        self.model_dropdown = ctk.CTkComboBox(center_frame, values=self.available_models, variable=self.model_var, width=120, justify='center')
        ctk.CTkLabel(center_frame, text="Models:", font=self.font_normal).grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.model_dropdown.grid(row=3, column=1, padx=5, pady=5, sticky="ns")
        ctk.CTkLabel(center_frame, text="Quality:", font=self.font_normal).grid(row=4, column=0, padx=10, pady=5, sticky="wns")
        self.priority_dropdown = ctk.CTkComboBox(center_frame, values=self.available_priorities, variable=self.priority_var, width=120, justify='center')
        self.priority_dropdown.grid(row=4, column=1, padx=5, pady=5, sticky="ns")
        ctk.CTkLabel(center_frame, text="").grid(row=0, column=0, pady=5)

    def _init_analytics(self):
        if not self.installation_id.get():
            new_id = str(uuid.uuid4())
            self.installation_id.set(new_id)
            self._log(f"Creating new installation ID: {new_id}", "info")
            self._needs_initial_save = True

        self._send_analytics_event("app_start")

    def _send_analytics_event(self, event_name, params={}):
        if not self.analytics_enabled_var.get():
            return

        if not MEASUREMENT_ID or not API_SECRET:
            self._log("Analytics configuration is incomplete, event not sent.", "warning")
            return

        system_params = {
            "operating_system": platform.system(),
            "os_version": platform.release(),
        }

        full_params = {**system_params, **params}

        send_analytics_event(
            self.installation_id.get(),
            event_name,
            APP_VERSION,
            full_params
        )

    def _select_input_folder(self):
        directory = tk.filedialog.askdirectory(title="Select Input Folder")
        if directory:
            output_dir = self.output_dir.get().strip()
            if output_dir and os.path.normpath(directory) == os.path.normpath(output_dir):
                tk.messagebox.showwarning(
                    "Same Folder",
                    "Input folder cannot be the same as output folder.\nPlease select a different folder."
                )
                return
            self.input_dir.set(directory)

    def _select_output_folder(self):
        directory = tk.filedialog.askdirectory(title="Select Output Folder")
        if directory:
            input_dir = self.input_dir.get().strip()
            if input_dir and os.path.normpath(directory) == os.path.normpath(input_dir):
                tk.messagebox.showwarning(
                    "Same Folder",
                    "Output folder cannot be the same as input folder.\nPlease select a different folder."
                )
                return
            self.output_dir.set(directory)

    def _load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.processed_cache = json.load(f)
        except Exception as e:
            self._log(f"Error loading cache: {e}", "error")
            self.processed_cache = {}

    def _save_cache(self):
        try:
            if len(self.processed_cache) > 1000:
                cache_items = sorted(self.processed_cache.items(),
                                key=lambda x: x[1].get('timestamp', 0),
                                reverse=True)
                self.processed_cache = dict(cache_items[:1000])

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_cache, f, indent=4)
        except Exception as e:
            self._log(f"Error saving cache: {e}", "error")

    def _sync_actual_keys_from_textbox_with_autohide(self, event=None):
        """Auto-hide API keys while maintaining actual keys in memory"""
        try:
            keys_text = self.api_textbox.get("1.0", "end-1c")
            lines = keys_text.splitlines()
            
            new_actual_keys = []
            has_real_keys = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # If line is hidden (starts with *), keep existing corresponding key
                if line.startswith('*'):
                    continue
                # If line is a real API key, add it
                if len(line) > 20:  # Reasonable API key length
                    new_actual_keys.append(line)
                    has_real_keys = True
            
            # Update actual keys if we found new ones
            if new_actual_keys:
                self._actual_api_keys = new_actual_keys
                
            # Only auto-hide if we have real keys and user was typing
            if has_real_keys and event and hasattr(event, 'type'):
                # Auto-hide display after typing
                self.after(500, self._update_api_textbox_with_autohide)
            
            self._ensure_provider_entry(self.selected_provider)
            self._persist_current_provider_keys()

        except tk.TclError:
            pass
        except Exception as e:
            self._log(f"Error syncing keys: {e}", "error")
    
    def _update_api_textbox_with_autohide(self):
        """Update textbox display with auto-hidden API keys"""
        cursor_pos = self.api_textbox.index(tk.INSERT)
        
        try:
            self.api_textbox.configure(state=tk.NORMAL)
            self.api_textbox.delete("1.0", tk.END)
            
            if self._actual_api_keys:
                hidden_keys = []
                for key in self._actual_api_keys:
                    if len(key) >= 5:
                        hidden_key = '*' * (len(key) - 5) + key[-5:]
                        hidden_keys.append(hidden_key)
                    else:
                        hidden_keys.append('.' * len(key))
                
                self.api_textbox.insert("1.0", "\n".join(hidden_keys))
            
            self.api_textbox.configure(state=tk.NORMAL)
            self.api_textbox.mark_set(tk.INSERT, cursor_pos)
            
        except tk.TclError:
            pass
        except Exception as e:
            self._log(f"Error updating API textbox: {e}", "error")
    
    def _ensure_provider_entry(self, provider_name):
        if not provider_name:
            return
        if provider_name not in self.api_keys_by_provider:
            self.api_keys_by_provider[provider_name] = []

    def _persist_current_provider_keys(self):
        provider_name = self.selected_provider or (self.provider_var.get() if hasattr(self, "provider_var") else None)
        if not provider_name:
            return
        self._ensure_provider_entry(provider_name)
        self.api_keys_by_provider[provider_name] = list(self._actual_api_keys)

    def _load_provider_keys(self, provider_name):
        self._ensure_provider_entry(provider_name)
        self._actual_api_keys = list(self.api_keys_by_provider.get(provider_name, []))
        self._update_api_textbox_with_autohide()

    def _refresh_provider_models(self, provider_name):
        models = list(self._models_by_provider.get(provider_name, []))
        self.available_models = models
        if hasattr(self, "model_dropdown"):
            self.model_dropdown.configure(values=self.available_models)
        current_model = self.model_var.get() if hasattr(self, "model_var") else ""
        if current_model not in self.available_models and self.available_models:
            self.model_var.set(self.available_models[0])
            if hasattr(self, "model_dropdown"):
                self.model_dropdown.set(self.available_models[0])
        elif not self.available_models:
            self.model_var.set("")
            if hasattr(self, "model_dropdown"):
                self.model_dropdown.set("")

    def _auto_fetch_models(self):
        """Silently fetch models if the current provider has API keys.
        Unlike _fetch_models, this skips quietly when no keys are present."""
        provider = self.provider_var.get()
        keys = list(self.api_keys_by_provider.get(provider, []))
        if not keys:
            return
        self._log(f"Auto-fetching model list for {provider}...", "info")
        if hasattr(self, "save_api_button"):
            self.save_api_button.configure(state="disabled")

        def _do_auto():
            try:
                from src.api import provider_manager
                base_url = None
                if provider == provider_manager.PROVIDER_CUSTOM:
                    base_url = getattr(self, "_custom_base_url_var", tk.StringVar()).get().strip()
                    if not base_url:
                        return
                models = provider_manager.fetch_models(provider, keys[0], base_url)
                if models:
                    self.after(0, lambda m=models: self._apply_fetched_models(provider, m))
            except Exception:
                pass
            finally:
                self.after(0, lambda: (
                    self.save_api_button.configure(state="normal")
                    if hasattr(self, "save_api_button") else None
                ))

        threading.Thread(target=_do_auto, daemon=True).start()

    def _fetch_models(self):
        """Fetch available models from the selected provider via its API."""
        provider = self.provider_var.get()
        api_keys = self._get_keys_from_textbox()
        if not api_keys:
            self._log("No API key — cannot fetch models.", "warning")
            return

        self._log(f"Fetching model list for {provider}...", "info")
        if hasattr(self, "save_api_button"):
            self.save_api_button.configure(state="disabled")

        def _do_fetch():
            try:
                from src.api import provider_manager
                base_url = None
                if provider == provider_manager.PROVIDER_CUSTOM:
                    base_url = getattr(self, "_custom_base_url_var", tk.StringVar()).get().strip()
                    if not base_url:
                        self.after(0, lambda: self._log(
                            "Custom provider requires a Base URL.", "warning"))
                        return

                models = provider_manager.fetch_models(provider, api_keys[0], base_url)
                if models:
                    self.after(0, lambda m=models: self._apply_fetched_models(provider, m))
                else:
                    self.after(0, lambda: self._log(
                        f"No models returned for {provider}.", "warning"))
            except Exception as e:
                self.after(0, lambda err=e: self._log(
                    f"Error fetching models: {err}", "error"))
            finally:
                self.after(0, lambda: (
                    self.save_api_button.configure(state="normal")
                    if hasattr(self, "save_api_button") else None
                ))

        threading.Thread(target=_do_fetch, daemon=True).start()

    def _apply_fetched_models(self, provider: str, models: list):
        """Apply fetched model list to dropdown and per-provider state."""
        self._models_by_provider[provider] = list(models)
        self.available_models = list(models)
        if hasattr(self, "model_dropdown"):
            self.model_dropdown.configure(values=self.available_models)
        if hasattr(self, "_model_scrollable"):
            self._model_scrollable.configure(values=self.available_models)
        current = self.model_var.get()
        if self.available_models:
            if current not in self.available_models:
                self.model_var.set(self.available_models[0])
                if hasattr(self, "model_dropdown"):
                    self.model_dropdown.set(self.available_models[0])
        self._log(f"Fetched {len(models)} models for {provider}.", "success")

    def _update_base_url_field(self):
        """Update URL entry field: auto-fill and disable for built-in providers,
        enable and clear for Custom."""
        from src.api import provider_manager
        provider = self.provider_var.get()
        if provider == provider_manager.PROVIDER_CUSTOM:
            self._base_url_entry.configure(state="normal")
        else:
            base_url = provider_manager.PROVIDER_BASE_URLS.get(provider, "")
            self._custom_base_url_var.set(base_url)
            self._base_url_entry.configure(state="disabled")

    def _on_provider_change(self, value):
        from src.api import provider_manager
        provider = value or provider_manager.get_default_provider()
        if provider not in self.available_providers:
            provider = self.available_providers[0]
        if provider == self.selected_provider:
            return

        if hasattr(self, "model_var"):
            self._models_by_provider.setdefault(self.selected_provider, [])

        self._sync_actual_keys_from_textbox()
        self._persist_current_provider_keys()

        # Save current model selection for the old provider
        if hasattr(self, "model_var"):
            old_model = self.model_var.get()
            if old_model:
                self._selected_model_by_provider[self.selected_provider] = old_model

        self.selected_provider = provider
        self.provider_var.set(provider)
        self._load_provider_keys(provider)
        self._refresh_provider_models(provider)

        # Restore previously selected model for the new provider
        saved_model = self._selected_model_by_provider.get(provider, "")
        if saved_model and saved_model in self.available_models:
            self.model_var.set(saved_model)
            if hasattr(self, "model_dropdown"):
                self.model_dropdown.set(saved_model)

        self._update_base_url_field()
        try:
            self._save_settings()
        except Exception:
            pass

        # Auto-fetch models for the new provider if it has API keys
        self._auto_fetch_models()

    def _update_api_textbox(self):
        cursor_pos = self.api_textbox.index(tk.INSERT)
        selection = None
        try:
            selection = self.api_textbox.tag_ranges("sel")
        except tk.TclError:
            pass

        try:
            self.api_textbox.configure(state=tk.NORMAL)
            self.api_textbox.delete("1.0", tk.END)

            if self.show_api_keys_var.get():
                if self._actual_api_keys:
                    self.api_textbox.insert("1.0", "\n".join(self._actual_api_keys))
            else:
                if self._actual_api_keys:
                    placeholders = ["•" * 39] * len(self._actual_api_keys)
                    self.api_textbox.insert("1.0", "\n".join(placeholders))

            self.api_textbox.configure(state=tk.NORMAL)

            self.api_textbox.mark_set(tk.INSERT, cursor_pos)
            if selection:
                 self.api_textbox.tag_add("sel", selection[0], selection[1])
            self.api_textbox.see(tk.INSERT)

        except tk.TclError:
            pass
        except Exception as e:
             self._log(f"Error updating API textbox display: {e}", "error")

    def _get_keys_from_textbox(self):
        self._sync_actual_keys_from_textbox()
        self._persist_current_provider_keys()
        provider_name = self.selected_provider or (self.provider_var.get() if hasattr(self, "provider_var") else None)
        if not provider_name:
            return []
        return list(self.api_keys_by_provider.get(provider_name, []))

    def _sync_actual_keys_from_textbox(self, event=None):
        """Redirect to new auto-hide method for backward compatibility"""
        self._sync_actual_keys_from_textbox_with_autohide(event)

    def _get_config_path(self):
        try:
            keys_text = self.api_textbox.get("1.0", "end-1c")
            return [line.strip() for line in keys_text.splitlines() if line.strip()]
        except tk.TclError:
            return []

    def _get_config_path(self):
        if os.name == 'nt':
            documents_path = os.path.join(os.environ.get('USERPROFILE', ''), 'Documents')
            if os.path.exists(documents_path):
                config_dir = os.path.join(documents_path, "RJ Auto Metadata")
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
        try:
            self._log(f"Loading settings...", "info")

            if os.path.exists(self.config_path):
                self.analytics_enabled_var.set(True)
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
                        self.auto_retry_var.set(True)  # Always enabled — switch removed in Phase 2
                        # show_api_keys_var removed - API keys now auto-hide by default
                        self.console_visible_var.set(settings.get("console_visible", True))
                        self.extra_settings_var.set(settings.get("api_key_paid", False))

                        stored_keys_map = settings.get("api_keys_by_provider", {})
                        if isinstance(stored_keys_map, dict):
                            for provider_name, keys in stored_keys_map.items():
                                if isinstance(keys, list):
                                    self.api_keys_by_provider[provider_name] = list(keys)

                        stored_models_map = settings.get("models_by_provider", {})
                        if isinstance(stored_models_map, dict):
                            for prov, mlist in stored_models_map.items():
                                if isinstance(mlist, list):
                                    self._models_by_provider[prov] = list(mlist)

                        stored_sel_models = settings.get("selected_model_by_provider", {})
                        if isinstance(stored_sel_models, dict):
                            self._selected_model_by_provider = dict(stored_sel_models)

                        self._custom_base_url_var.set(settings.get("custom_base_url", ""))

                        for provider_name in self.available_providers:
                            self._ensure_provider_entry(provider_name)

                        loaded_provider = settings.get("provider", self.selected_provider)
                        if loaded_provider not in self.available_providers:
                            loaded_provider = self.available_providers[0]
                        self.selected_provider = loaded_provider
                        self.provider_var.set(loaded_provider)
                        if hasattr(self, "provider_dropdown"):
                            try:
                                self.provider_dropdown.set(loaded_provider)
                            except Exception:
                                pass

                        fallback_keys = settings.get("api_keys", [])
                        if isinstance(fallback_keys, list) and fallback_keys:
                            self._ensure_provider_entry(self.selected_provider)
                            if not self.api_keys_by_provider.get(self.selected_provider):
                                self.api_keys_by_provider[self.selected_provider] = list(fallback_keys)

                        self._load_provider_keys(self.selected_provider)

                        loaded_theme = settings.get("theme", "dark")
                        self.theme_var.set(loaded_theme)
                        ctk.set_appearance_mode(loaded_theme)

                        loaded_install_id = settings.get("installation_id")
                        if loaded_install_id:
                            self.installation_id.set(loaded_install_id)
                            self._log(f"Installation ID found: {loaded_install_id[:8]}...", "info")
                        else:
                              self._log("Installation ID not found in config.", "info")

                        self._log("Other settings loaded from configuration", "info")

                        if platform.system() == "Windows":
                             initial_console_state = self.console_visible_var.get()
                             log_message(f"Setting initial console visibility to: {initial_console_state}", "info")
                             set_console_visibility(initial_console_state)
                             self.after(50, self._update_console_toggle_text)

                        self.keyword_count_var.set(str(settings.get("keyword_count", "49")))
                        self.priority_var.set(settings.get("priority", "Detailed"))
                        self.embedding_var.set(settings.get("embedding", "Enable"))
                        self.available_priorities = ["Detailed", "Balanced", "Less", "Custom"]
                        self._refresh_provider_models(self.selected_provider)

                        # Restore model: prefer per-provider map, fall back to global
                        saved_model = self._selected_model_by_provider.get(
                            self.selected_provider, settings.get("model", "")
                        )
                        if saved_model:
                            self.model_var.set(saved_model)
                            if hasattr(self, "model_dropdown"):
                                self.model_dropdown.set(saved_model)

                        stored_base_url = settings.get("custom_base_url", "")
                        self._custom_base_url_var.set(stored_base_url)
                        self._update_base_url_field()

                        # Advanced tab values
                        self.hint_var.set(settings.get("hint", ""))
                        self.custom_instruction_var.set(settings.get("custom_instruction", ""))
                        self.inject_keywords_var.set(settings.get("inject_keywords", ""))
                        self.title_min_words_var.set(settings.get("title_min_words", "6"))
                        self.title_max_chars_var.set(settings.get("title_max_chars", "180"))
                        self.desc_min_words_var.set(settings.get("desc_min_words", "6"))
                        self.desc_max_chars_var.set(settings.get("desc_max_chars", "180"))

                        if hasattr(self, "instruction_textbox"):
                            self.instruction_textbox.delete("1.0", "end")
                            loaded_instr = settings.get("custom_instruction", "")
                            if loaded_instr:
                                self.instruction_textbox.insert("1.0", loaded_instr)

                        if hasattr(self, "hint_textbox"):
                            self.hint_textbox.delete("1.0", "end")
                            loaded_hint = settings.get("hint", "")
                            if loaded_hint:
                                self.hint_textbox.insert("1.0", loaded_hint)

                        # Load custom shadow vars (must be done before _on_quality_change)
                        self._custom_title_min = settings.get("custom_title_min", settings.get("title_min_words", "6"))
                        self._custom_title_max = settings.get("custom_title_max", settings.get("title_max_chars", "180"))
                        self._custom_desc_min = settings.get("custom_desc_min", settings.get("desc_min_words", "6"))
                        self._custom_desc_max = settings.get("custom_desc_max", settings.get("desc_max_chars", "180"))
                        self._last_quality = ""  # reset so _on_quality_change triggers clean

                        self._on_quality_change()

                except Exception as inner_e:
                    self._log(f"Error loading configuration file: {inner_e}", "error")
            else:
                self._log(f"Configuration file not found", "warning")
                self.analytics_enabled_var.set(True)
                self.installation_id.set("")
                self._needs_initial_save = True
                self._log("New configuration file will be created after initialization", "info")
        except Exception as e:
            self._log(f"Error loading settings: {e}", "error")
            import traceback
            self._log(traceback.format_exc(), "error")
            self.analytics_enabled_var.set(True)
            self.installation_id.set("")

    def _save_settings(self):
        self._sync_actual_keys_from_textbox()
        self._persist_current_provider_keys()
        provider_name = self.provider_var.get() if hasattr(self, "provider_var") else self.selected_provider
        self._ensure_provider_entry(provider_name)
        current_api_keys = list(self.api_keys_by_provider.get(provider_name, []))

        # Persist current model selection for the active provider
        current_model = self.model_var.get() if hasattr(self, "model_var") else ""
        if current_model:
            self._selected_model_by_provider[provider_name] = current_model

        settings = {
            "config_version": "1.0",
            "input_dir": self.input_dir.get(),
            "output_dir": self.output_dir.get(),
            "delay": self.delay_var.get(),
            "workers": self.workers_var.get(),
            "rename": self.rename_files_var.get(),
            "auto_kategori": self.auto_kategori_var.get(),
            "auto_foldering": self.auto_foldering_var.get(),
            "auto_retry": True,  # Hardcoded — switch removed in Phase 2
            "api_keys": current_api_keys,
            # "show_api_keys" removed - API keys now auto-hide by default
            "console_visible": self.console_visible_var.get(),
            "theme": self.theme_var.get(),
            "last_saved": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "analytics_enabled": self.analytics_enabled_var.get(),
            "installation_id": self.installation_id.get(),
            "model": self.model_var.get(),
            "keyword_count": self.keyword_count_var.get(),
            "priority": self.priority_var.get(),
            "embedding": self.embedding_var.get(),
            "api_key_paid": self.extra_settings_var.get(),
            "provider": self.provider_var.get() if hasattr(self, "provider_var") else self.selected_provider,
            "api_keys_by_provider": {name: list(keys) for name, keys in self.api_keys_by_provider.items()},
            "models_by_provider": {
                name: list(models)
                for name, models in self._models_by_provider.items()
            },
            "selected_model_by_provider": dict(self._selected_model_by_provider),
            "custom_base_url": self._custom_base_url_var.get(),
            "hint": self.hint_var.get(),
            "custom_instruction": self.custom_instruction_var.get(),
            "inject_keywords": self.inject_keywords_var.get(),
            "title_min_words": self.title_min_words_var.get(),
            "title_max_chars": self.title_max_chars_var.get(),
            "desc_min_words": self.desc_min_words_var.get(),
            "desc_max_chars": self.desc_max_chars_var.get(),
            # Custom Quality shadow values — persisted separately so they survive preset switches
            "custom_title_min": self._custom_title_min,
            "custom_title_max": self._custom_title_max,
            "custom_desc_min": self._custom_desc_min,
            "custom_desc_max": self._custom_desc_max,
        }

        try:
            config_dir = os.path.dirname(self.config_path)
            if config_dir and not os.path.exists(config_dir):
                self._log(f"Creating configuration directory: {config_dir}", "info")
                os.makedirs(config_dir, exist_ok=True)

            if not os.access(config_dir, os.W_OK):
                self._log(f"Warning: Configuration directory is not writable: {config_dir}", "warning")
                if os.name == 'nt':
                    self.config_path = os.path.join(os.environ.get('USERPROFILE', ''), "RJ Auto Metadata - config.json")
                    self._log(f"Trying fallback to home directory: {self.config_path}", "info")

            self._log(f"Saving settings...", "info")
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json_data = json.dumps(settings, indent=4)
                f.write(json_data)
                self._log(f"Settings saved successfully ({len(json_data)} bytes)", "info")
        except PermissionError as pe:
            self._log(f"Error permission: {pe}", "error")
            alt_path = os.path.join(os.getcwd(), "rjmetadata_config.json")
            self._log(f"Trying to write to alternative location: {alt_path}", "warning")

            try:
                with open(alt_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=4)
                self.config_path = alt_path
                self._log(f"Settings saved to alternative location", "info")
            except Exception as alt_e:
                self._log(f"Failed to write to alternative location: {alt_e}", "error")
        except Exception as e:
            self._log(f"Error saving settings: {e}", "error")
            import traceback
            self._log(traceback.format_exc(), "error")

    def _change_theme(self, selected_theme):
        try:
            self.theme_var.set(selected_theme)
            if hasattr(self, "theme_dropdown"):
                self.theme_dropdown.set(selected_theme)
            
            if selected_theme in ["dark", "light", "system"]:
                ctk.set_appearance_mode(selected_theme)
            else:
                theme_file = os.path.join(self.theme_folder, f"{selected_theme}.json")
                if os.path.exists(theme_file):
                    ctk.set_default_color_theme(theme_file)
                else:
                    self._log(f"Theme '{selected_theme}' not found.", "error")
                    return

            self._log(f"Theme changed to: {selected_theme}", "info")
            self._update_log_colors()
            self._save_settings()
        except Exception as e:
            self._log(f"Error changing theme: {e}", "error")

    def _set_limits_state(self, state):
        if hasattr(self, "title_min_entry"):
            self.title_min_entry.configure(state=state)
        if hasattr(self, "title_max_entry"):
            self.title_max_entry.configure(state=state)
        if hasattr(self, "desc_min_entry"):
            self.desc_min_entry.configure(state=state)
        if hasattr(self, "desc_max_entry"):
            self.desc_max_entry.configure(state=state)

    def _on_quality_change(self, value=None):
        # Called via trace on priority_var — always read from the var itself
        value = self.priority_var.get()
        if not value:
            return

        # If leaving Custom mode, save current field values as shadow custom values
        if getattr(self, "_last_quality", "") == "Custom" and value != "Custom":
            self._custom_title_min = self.title_min_words_var.get()
            self._custom_title_max = self.title_max_chars_var.get()
            self._custom_desc_min = self.desc_min_words_var.get()
            self._custom_desc_max = self.desc_max_chars_var.get()
        self._last_quality = value

        if value == "Custom":
            # Restore the user's saved custom values
            self._set_limits_state("normal")
            self.title_min_words_var.set(self._custom_title_min)
            self.title_max_chars_var.set(self._custom_title_max)
            self.desc_min_words_var.set(self._custom_desc_min)
            self.desc_max_chars_var.set(self._custom_desc_max)
        else:
            from src.api.prompts import _PRIORITY_PARAMS
            preset = "Fast" if value == "Less" else value
            params = _PRIORITY_PARAMS.get(preset, _PRIORITY_PARAMS["Detailed"])
            min_w = str(params["min_words"])
            max_c = str(params["max_chars"])
            # Temporarily unlock to allow writing, then lock back
            self._set_limits_state("normal")
            self.title_min_words_var.set(min_w)
            self.title_max_chars_var.set(max_c)
            self.desc_min_words_var.set(min_w)
            self.desc_max_chars_var.set(max_c)
            self._set_limits_state("disabled")

    def _update_log_colors(self):
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

    def _validate_folders(self):
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
        try:
            if not os.path.exists(path):
                self._log(f"Path not found: {path}", "info")
                return False

            if os.path.isdir(path):
                if check_write:
                    return is_writable_directory(path)
                return True
            elif os.path.isfile(path):
                can_read = os.access(path, os.R_OK)
                can_write = os.access(path, os.W_OK) if check_write else True
                self._log(f"File {path}: can read = {can_read}, can write = {can_write}", "info")
                return can_read and can_write

            return False
        except Exception as e:
            self._log(f"Error validating path: {e}", "error")
            return False

    def _start_processing(self):
        input_dir = self.input_dir.get().strip()
        output_dir = self.output_dir.get().strip()

        self._disable_ui_during_processing()

        if not input_dir or not output_dir:
            self._reset_ui_after_processing()
            tk.messagebox.showwarning("Input Less",
                "Please select input and output folders.")
            return

        if os.path.normpath(input_dir) == os.path.normpath(output_dir):
            self._reset_ui_after_processing()
            tk.messagebox.showwarning("Same Folder",
                "Input and output folders cannot be the same.\nPlease select different folders.")
            return

        if not os.path.isdir(input_dir):
            self._reset_ui_after_processing()
            tk.messagebox.showerror("Error",
                f"Invalid input folder:\n{input_dir}")
            return

        if not os.path.isdir(output_dir):
            if tk.messagebox.askyesno("Create Folder?",
                f"Output folder '{os.path.basename(output_dir)}' not found.\n\nCreate folder?"):
                try:
                    os.makedirs(output_dir)
                except Exception as e:
                    self._reset_ui_after_processing()
                    tk.messagebox.showerror("Error",
                        f"Failed to create output folder:\n{e}")
                    return
            else:
                self._reset_ui_after_processing()
                return

        current_api_keys = self._get_keys_from_textbox()
        if not current_api_keys:
            self._reset_ui_after_processing()
            tk.messagebox.showwarning("Input Less",
                "Please enter at least one API Key.")
            return

        # Custom provider must have a Base URL or the request will go nowhere.
        provider_for_validation = (
            self.provider_var.get() if hasattr(self, "provider_var") else ""
        )
        if provider_for_validation == provider_manager.PROVIDER_CUSTOM:
            custom_base_url = (
                self._custom_base_url_var.get().strip()
                if hasattr(self, "_custom_base_url_var") else ""
            )
            if not custom_base_url:
                self._reset_ui_after_processing()
                tk.messagebox.showwarning(
                    "Base URL Required",
                    "Custom provider requires a Base URL\n"
                    "(for example, https://your-endpoint/v1).\n\n"
                    "Enter a Base URL in the API panel before starting.",
                )
                return
            selected_model_for_validation = (
                self.model_var.get().strip() if hasattr(self, "model_var") else ""
            )
            if not selected_model_for_validation:
                self._reset_ui_after_processing()
                tk.messagebox.showwarning(
                    "Model Required",
                    "Custom provider requires a model selection.\n"
                    "Use Fetch Models or enter a model id manually.",
                )
                return

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

        if self.extra_settings_var.get():
            try:
                num_workers = int(self.workers_var.get().strip() or "3")
                if num_workers <= 0:
                    num_workers = 1
                elif num_workers > 100:
                    num_workers = 100
                self.workers_var.set(str(num_workers))
            except ValueError:
                self.workers_var.set("3")
                num_workers = 3
        else:
            max_workers = 100
            try:
                num_workers = int(self.workers_var.get().strip() or "3")
                if num_workers <= 0:
                    num_workers = 1
                elif num_workers > max_workers:
                    num_workers = max_workers
                self.workers_var.set(str(num_workers))
            except ValueError:
                self.workers_var.set("3")
                num_workers = 3

        self.processed_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.stopped_count = 0

        rename_enabled = self.rename_files_var.get()
        auto_kategori_enabled = self.auto_kategori_var.get()
        auto_foldering_enabled = self.auto_foldering_var.get()

        self.stop_event.clear()
        self.start_time = time.monotonic()
        self.start_button.configure(state=tk.DISABLED, text="Processing....")
        self.stop_button.configure(state=tk.NORMAL)

        self._log("Auto compression active for large files", "warning")

        if self.analytics_enabled_var.get():
            self._send_analytics_event("process_started", {
                "input_files_count": -1,
                "workers": num_workers,
                "delay": delay_sec,
                "rename_enabled": rename_enabled,
                "auto_kategori": auto_kategori_enabled,
                "auto_foldering": auto_foldering_enabled
            })

        try:
            keyword_count = int(self.keyword_count_var.get().strip() or "49")
            if keyword_count < 8:
                keyword_count = 8
            elif keyword_count > 49:
                keyword_count = 49
            self.keyword_count_var.set(str(keyword_count))
        except ValueError:
            self.keyword_count_var.set("49")
            keyword_count = 49
        priority = self.priority_var.get() if hasattr(self, 'priority_var') else "Kualitas"
        self.processing_thread = threading.Thread(
            target=self._run_processing,
            args=(input_dir, output_dir, current_api_keys,
                  rename_enabled, delay_sec, num_workers,
                  auto_kategori_enabled, auto_foldering_enabled, self.model_var.get(), str(keyword_count), priority),
            kwargs={
                'bypass_api_key_limit': self.extra_settings_var.get()
            },
            daemon=True
        )
        self.processing_thread.start()

    def _disable_ui_during_processing(self):
        self.start_button.configure(state=tk.DISABLED)
        self.clear_button.configure(state=tk.DISABLED)
        self.rename_switch.configure(state=tk.DISABLED)
        self.auto_kategori_switch.configure(state=tk.DISABLED)
        self.auto_foldering_switch.configure(state=tk.DISABLED)
        self.api_textbox.configure(state=tk.DISABLED)
        self.theme_dropdown.configure(state=tk.DISABLED)
        self.model_dropdown.configure(state=tk.DISABLED)
        self.priority_dropdown.configure(state=tk.DISABLED)
        self.embedding_dropdown.configure(state=tk.DISABLED)
        self.keyword_entry.configure(state=tk.DISABLED)
        self.workers_entry.configure(state=tk.DISABLED)
        self.delay_entry.configure(state=tk.DISABLED)
        self.input_entry.configure(state=tk.DISABLED)
        self.output_entry.configure(state=tk.DISABLED)
        self.cek_api_button.configure(state=tk.DISABLED)
        self.save_api_button.configure(state=tk.DISABLED)
        self.input_button.configure(state=tk.DISABLED)
        self.output_button.configure(state=tk.DISABLED)
        if hasattr(self, "provider_dropdown"):
            self.provider_dropdown.configure(state=tk.DISABLED)
        if hasattr(self, "_base_url_entry"):
            self._base_url_entry.configure(state=tk.DISABLED)
        if hasattr(self, "instruction_textbox"):
            self.instruction_textbox.configure(state=tk.DISABLED)
        if hasattr(self, "hint_textbox"):
            self.hint_textbox.configure(state=tk.DISABLED)
        if hasattr(self, "inject_kw_entry"):
            self.inject_kw_entry.configure(state=tk.DISABLED)
        if hasattr(self, "title_min_entry"):
            self.title_min_entry.configure(state=tk.DISABLED)
        if hasattr(self, "title_max_entry"):
            self.title_max_entry.configure(state=tk.DISABLED)
        if hasattr(self, "desc_min_entry"):
            self.desc_min_entry.configure(state=tk.DISABLED)
        if hasattr(self, "desc_max_entry"):
            self.desc_max_entry.configure(state=tk.DISABLED)

    def _run_processing(self, input_dir, output_dir, api_keys, rename_enabled, delay_seconds, num_workers, auto_kategori_enabled, auto_foldering_enabled, selected_model=None, keyword_count="49", priority="Details", bypass_api_key_limit=False):
        from src.utils.system_checks import GHOSTSCRIPT_PATH as gs_path_found

        try:
            embedding_enabled = self.embedding_var.get() == "Enable"
            auto_retry_enabled = self.auto_retry_var.get()
            
            provider_name = self.provider_var.get() if hasattr(self, "provider_var") else provider_manager.get_default_provider()
            if provider_name not in self.available_providers:
                provider_name = provider_manager.get_default_provider()
            self.selected_provider = provider_name

            # Read Advanced tab values
            user_hint = self.hint_var.get().strip() if hasattr(self, "hint_var") else ""
            custom_instruction = self.custom_instruction_var.get().strip() \
                if hasattr(self, "custom_instruction_var") else ""
            inject_keywords_raw = self.inject_keywords_var.get().strip() \
                if hasattr(self, "inject_keywords_var") else ""

            def _safe_int(var_attr, fallback):
                try:
                    v = int(getattr(self, var_attr).get().strip())
                    return v if v > 0 else fallback
                except (ValueError, AttributeError):
                    return fallback

            title_min_words = _safe_int("title_min_words_var", 0)
            title_max_chars = _safe_int("title_max_chars_var", 0)
            desc_min_words  = _safe_int("desc_min_words_var", 0)
            desc_max_chars  = _safe_int("desc_max_chars_var", 0)

            inject_keywords_list = [
                kw.strip().lower()
                for kw in inject_keywords_raw.split(",")
                if kw.strip()
            ] if inject_keywords_raw else []

            prompt_config = {
                "user_hint":        user_hint,
                "custom_instruction": custom_instruction,
                "inject_keywords":  inject_keywords_list,
                "title_min_words":  title_min_words,
                "title_max_chars":  title_max_chars,
                "desc_min_words":   desc_min_words,
                "desc_max_chars":   desc_max_chars,
            }

            result = batch_process_files(
                input_dir=input_dir,
                output_dir=output_dir,
                api_keys=api_keys,
                provider_name=provider_name,
                ghostscript_path=gs_path_found,
                rename_enabled=rename_enabled,
                delay_seconds=delay_seconds,
                num_workers=num_workers,
                auto_kategori_enabled=auto_kategori_enabled,
                auto_foldering_enabled=auto_foldering_enabled,
                selected_model=selected_model,
                embedding_enabled=embedding_enabled,
                auto_retry_enabled=auto_retry_enabled,
                keyword_count=keyword_count,
                priority=priority,
                bypass_api_key_limit=bypass_api_key_limit,
                prompt_config=prompt_config,
                base_url_override=(
                    self._custom_base_url_var.get().strip()
                    if provider_name == provider_manager.PROVIDER_CUSTOM
                    and hasattr(self, "_custom_base_url_var")
                    else None
                ),
            )

            self.processed_count = result.get("processed_count", 0)
            self.failed_count = result.get("failed_count", 0)
            self.skipped_count = result.get("skipped_count", 0)
            self.stopped_count = result.get("stopped_count", 0)

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

            final_message = "Unknown error occurred."

            if result.get("status") == "no_files":
                final_message = "No files found in input folder."
                self.after(100, lambda msg=final_message: tk.messagebox.showinfo("Info Proses", msg))
                self.after(200, self._reset_ui_after_processing)
            elif self.stop_event.is_set():
                final_message = "Processing stopped by user."
                self.after(100, lambda: self.completion_manager.show_completion_message())
                self.after(200, self._reset_ui_after_processing)
            else:
                final_message = "Processing completed!"
                final_completed = self.processed_count + self.failed_count + self.skipped_count + self.stopped_count
                total_files = result.get("total_files", final_completed)
                self.after(100, lambda: self.completion_manager.show_completion_message())
                self.after(200, self._reset_ui_after_processing)

        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            self._log(f"Fatal error in processing thread: {e}\nTraceback:\n{tb_str}", "error")
            self.after(0, self._reset_ui_after_processing)

    def _update_progress(self, current, total):
        self.update_idletasks()

    def _format_time(self, seconds):
        if seconds is None or not isinstance(seconds, (int, float)) or seconds < 0:
            return "00:00:00"

        hours = int(seconds) // 3600
        minutes = (int(seconds) % 3600) // 60
        secs = int(seconds) % 60

        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _stop_processing(self):
        if self.processing_thread and self.processing_thread.is_alive():
            if tk.messagebox.askyesno("Stop Processing", "Stop processing? Active tasks will be signaled to stop."):
                self._log("Received stop request...", "warning")
                self.stop_event.set()

                from src.api import provider_manager
                provider_manager.set_force_stop()

                self.stop_button.configure(state=tk.DISABLED, text="Stopping...")
                self._stop_request_time = time.monotonic()
                self.update_idletasks()
                self.update()

                try:
                    if self.is_executable:
                        self._log("Executable mode detected, using interrupt force...", "warning")
                    else:
                        self._log("Stopping all active processes...", "warning")
                except Exception as e:
                    self._log(f"Error when trying to force interrupt: {e}", "error")

                self._check_thread_ended()
        else:
            self.stop_button.configure(state=tk.DISABLED)
            self._reset_ui_after_processing()

    def _check_thread_ended(self):
        self.update_idletasks()
        thread_ended = not self.processing_thread or not self.processing_thread.is_alive()
        force_reset = False

        if hasattr(self, '_stop_request_time') and self._stop_request_time is not None:
            elapsed_since_stop = time.monotonic() - self._stop_request_time
            timeout_threshold = 30.0  # Allow threads enough time to see the flag

            if elapsed_since_stop > timeout_threshold:
                self._log(
                    f"Thread did not respond after {elapsed_since_stop:.1f}s, forcing UI reset. "
                    "Background thread may still be finishing its current file.",
                    "warning",
                )
                force_reset = True

        if thread_ended:
            # Thread is confirmed dead — safe to clear all stop state
            self.after(10, self._reset_ui_after_processing)
        elif force_reset:
            # UI timeout reached but thread still alive — reset UI buttons only,
            # do NOT clear stop_flag or stop_event (thread must keep seeing them)
            self.after(10, self._reset_ui_buttons_only)
        else:
            self.after(50, self._check_thread_ended)

    def _reset_ui_buttons_only(self):
        """Reset UI controls to idle state without clearing the stop flag.

        Used when the UI timeout fires but the background thread is still alive.
        The stop flag must remain active so the thread can still observe it.
        """
        try:
            self._stop_request_time = None
            self.start_button.configure(state=tk.NORMAL, text="Start Processing")
            self.stop_button.configure(state=tk.DISABLED, text="Stop")
            self.processing_thread = None
            self.start_time = None
            self.update_idletasks()
            self._save_cache()
            self._save_settings()
            self.clear_button.configure(state=tk.NORMAL)
        except Exception as e:
            self._log(f"Error resetting UI buttons: {e}", "error")

    def _reset_ui_after_processing(self):
        try:
            self._stop_request_time = None
            from src.utils.stop_flag import reset_force_stop
            reset_force_stop()
            self.start_button.configure(state=tk.NORMAL, text="Start Processing")
            self.stop_button.configure(state=tk.DISABLED, text="Stop")
            self.processing_thread = None
            self.start_time = None
            self.stop_event.clear()
            self.update_idletasks()
            self._save_cache()
            self._save_settings()
            self.start_button.configure(state=tk.NORMAL)
            self.clear_button.configure(state=tk.NORMAL)
            self.rename_switch.configure(state=tk.NORMAL)
            self.auto_kategori_switch.configure(state=tk.NORMAL)
            self.auto_foldering_switch.configure(state=tk.NORMAL)
            self.workers_entry.configure(state=tk.NORMAL)
            self.theme_dropdown.configure(state=tk.NORMAL)
            self.model_dropdown.configure(state=tk.NORMAL)
            self.priority_dropdown.configure(state=tk.NORMAL)
            self.embedding_dropdown.configure(state=tk.NORMAL)
            self.keyword_entry.configure(state=tk.NORMAL)
            self.delay_entry.configure(state=tk.NORMAL)
            self.input_entry.configure(state=tk.NORMAL)
            self.output_entry.configure(state=tk.NORMAL)
            self.cek_api_button.configure(state=tk.NORMAL)
            self.save_api_button.configure(state=tk.NORMAL)
            self.input_button.configure(state=tk.NORMAL)
            self.output_button.configure(state=tk.NORMAL)
            if hasattr(self, "provider_dropdown"):
                self.provider_dropdown.configure(state=tk.NORMAL)
            if hasattr(self, "instruction_textbox"):
                self.instruction_textbox.configure(state=tk.NORMAL)
            if hasattr(self, "hint_textbox"):
                self.hint_textbox.configure(state=tk.NORMAL)
            if hasattr(self, "inject_kw_entry"):
                self.inject_kw_entry.configure(state=tk.NORMAL)
            self._on_quality_change()
            self._update_base_url_field()
        except Exception as e:
            print(f"Error when resetting UI: {e}")
            import traceback
            traceback.print_exc()

            try:
                self.start_button.configure(state=tk.NORMAL, text="Start Processing")
                self.stop_button.configure(state=tk.DISABLED, text="Stop")
                self.update_idletasks()
            except:
                pass

    def _log(self, message, tag=None):
        self.log_queue.put((message, tag))

    def _process_log_queue(self):
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
        allowed_patterns = [
            r"^Auto compression active for large files$",
            r"^Starting process \(\d+ worker, delay \d+s\)$",
            r"^Found \d+ files to process$",
            r"^Output CSV will be saved in subfolder: metadata_csv$",
            r"^ → Processing .+\.\w+\.\.\.$",
            r"^Batch \d+: Waiting for \d+ file\.\.\.$",
            r"^Batch \d+ \(\d+/\d+\): Waiting for \d+ file\.\.\.$",
            r"^✓ .+\.\w+ → .+\.\w+$",
            r"^✓ .+\.\w+$",
            r"^✗ .+\.\w+ \(.*\)$",
            r"^✗ .+\.\w+$",
            r"^⚠  .+\.\w+$",
            r"^⚠ .+\.\w+ \(.*\)$",
            r"^Cool-down \d+ seconds before processing\.\.\.$",
            r"^Retry Batch \d+: Waiting for \d+ file\.\.\.$",
            r"^Retry cool-down \d+ seconds before next batch\.\.\.$",
            r"^Successfully loaded \d+ API key$",
            r"^API Keys \(\d+\) saved to file$",
            r"^Adjusting worker count to \d+ to match available API keys\.$",
            r"^Received stop request\.\.\.$",
            r"^Executable mode detected, using interrupt force\.\.\.$",
            r"^Stopping all active processes\.\.\.$",
            r"^Thread did not respond after \d+\.\d+s, forcing UI reset\.",
            r"^Processing stopped before starting \(initial detection\)$",
            r"^Stop detected after processing batch results\.$",
            r"^Processing stopped by user \(cooldown detection\)$",
            r"^Cancelling remaining tasks\.\.\.$",
            r"^Creating new installation ID: .+$",
            r"^Installation ID found: .+\.\.\.$",
            r"^Installation ID not found in config\.$",
            r"^Loading other settings\.\.\.$",
            r"^Other settings loaded from configuration$",
            r"^Config file not found$",
            r"^AUTO RETRY ENABLED - Processing failed files\.\.\.$",
            r"^AUTO RETRY COMPLETED: \d+ file\(s\) still failed after \d+ attempts$",
            r"^AUTO RETRY: No retryable files found \(.*\)$",
            r"^AUTO RETRY SUCCESS: All files processed successfully!$", 
            r"^RETRY ATTEMPT \d+: \d+ file\(S\) remaining$",
            r"^New config file created$",
            r"^============= Summary Process =============",
            r"^Total file: \d+$",
            r"^Success: \d+$",
            r"^Failed: \d+$",
            r"^Skipped: \d+$",
            r"^Stopped: \d+$",
            r"^=========================================$",
            r"^All API keys OK \(\d+/\d+\)$",
            r"^\d+ API keys OK, \d+ API keys error:$",
            r"^No API keys to check\.$",
            r"^Error when checking API keys:.*$",
            r"^    - \.\.\.[A-Za-z0-9]{5}: \d+ - .+$",
        ]

        for pattern in allowed_patterns:
            if re.match(pattern, message):
                if message == "\n============= Summary Process =============":
                    self._in_summary_block = True
                elif message == "=========================================\n":
                    self._in_summary_block = False
                return True

        if self._in_summary_block:
            if re.match(r"^=========================================$", message):
                self._in_summary_block = False
            return True

        return False

    def _write_to_log(self, message, tag=None):
        if not self._should_display_in_gui(message):
            if self._in_summary_block and not message.startswith("="):
                 self._in_summary_block = False
            return

        try:
            self.log_text.configure(state=tk.NORMAL)

            if tag is None:
                if message.startswith("✓"):
                    tag = "success"
                elif message.startswith("✗"):
                    tag = "error"
                elif message.startswith("⚠"):
                    tag = "warning"
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

            if not message.startswith((" ✓", " ⋯", " ✗", " ⊘", " ⚠")) or message.startswith("==="):
                timestamp = time.strftime("%H:%M:%S")
                self.log_text._textbox.insert(tk.END, f"[{timestamp}] ", "")
                self.log_text._textbox.insert(tk.END, f"{message}\n", tag if tag else "")
            else:
                self.log_text._textbox.insert(tk.END, f"{message}\n", tag if tag else "")

            self.log_text._textbox.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
        except tk.TclError:
            pass

    def _clear_log(self):
        try:
            self.log_text.configure(state=tk.NORMAL)
            self.log_text._textbox.delete("1.0", tk.END)
            self.log_text.configure(state=tk.DISABLED)
        except tk.TclError:
            pass

    def on_closing(self):
        try:
            self._save_settings()
            self._save_cache()

            if self.processing_thread and self.processing_thread.is_alive():
                if tk.messagebox.askyesno("Exit",
                        "Processing is running. Are you sure you want to exit?\nProcessing will be stopped."):
                    self.stop_event.set()

                    from src.utils.stop_flag import set_force_stop
                    set_force_stop()

                    self.after(300, self._force_close)
                return

            self._force_close()
        except Exception as e:
            print(f"Error when closing application: {e}")
            self.destroy()

    def _force_close(self):
        if hasattr(self, '_log_queue_after_id') and self._log_queue_after_id:
            try:
                self.after_cancel(self._log_queue_after_id)
            except tk.TclError:
                pass
        self.destroy()

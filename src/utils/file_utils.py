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

# src/utils/file_utils.py
import os
import re
import time
import csv
import portalocker
import hashlib
import shutil
from src.utils.logging import log_message

# Konstanta
CSV_LOCK_EXTENSION = ".processing"
TEMP_FILES_CREATED = []
SUPPORTED_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.eps', '.ai', '.svg')
SUPPORTED_VIDEO_EXTENSIONS = ('.mp4', '.mpeg', '.3gp', '.avi', '.mov', '.mkv', '.flv', '.wmv')
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS + SUPPORTED_VIDEO_EXTENSIONS
WRITABLE_EXIF_EXTENSIONS = ('.jpg', '.jpeg')
WRITABLE_METADATA_VIDEO_EXTENSIONS = ('.mp4', '.mov', '.mkv', '.avi')
title_history = {}

def sanitize_filename(filename):
    sanitized = filename.replace('_', ' ')
    sanitized = re.sub(r'[^a-zA-Z0-9 ]', '', sanitized)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    max_len = 160
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len].strip()
    if not sanitized:
        timestamp_fallback = int(time.time() * 1000)
        sanitized = f"untitled_{timestamp_fallback}"
    return sanitized

def sanitize_csv_field(value):
    if not value:
        return ""
    sanitized = re.sub(r'[\r\n\t]+', ' ', str(value))
    sanitized = re.sub(r'/', '-', sanitized)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    return sanitized

def ensure_unique_title(title, image_path):
    sanitized = sanitize_filename(title)
    if sanitized in title_history:
        try:
            hash_md5 = hashlib.md5()
            with open(image_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            file_hash = hash_md5.hexdigest()[:8]
            timestamp = int(time.time()) % 10000
            if len(sanitized) > 160:
                sanitized = sanitized[:160]
            unique_suffix = f" Variant {file_hash}"
            return sanitized + unique_suffix
        except Exception as e:
            log_message(f"Error membuat judul unik: {e}")
            return sanitized + f" Variant {len(title_history)}"
    title_history[sanitized] = True
    return sanitized

def is_writable_directory(directory):
    if not os.path.exists(directory):
        return False
    try:
        test_file = os.path.join(directory, f"write_test_{int(time.time())}.tmp")
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return True
    except (IOError, PermissionError, OSError):
        return False

def lock_csv_file(csv_path):
    lock_file = csv_path + CSV_LOCK_EXTENSION
    try:
        with open(lock_file, 'w') as f:
            f.write("Processing in progress. Please wait.")
        return True
    except Exception as e:
        log_message(f"Error mengunci file CSV: {e}")
        return False

def unlock_csv_file(csv_path):
    lock_file = csv_path + CSV_LOCK_EXTENSION
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
        return True
    except Exception as e:
        log_message(f"Error membuka kunci file CSV: {e}")
        return False

def is_csv_locked(csv_path):
    lock_file = csv_path + CSV_LOCK_EXTENSION
    return os.path.exists(lock_file)

def write_to_csv_with_lock(csv_path, header, data_row):
    try:
        if is_csv_locked(csv_path):
            temp_csv_path = csv_path + ".temp"
            result = write_to_csv(temp_csv_path, header, data_row)
            return result
        return write_to_csv(csv_path, header, data_row)
    except Exception as e:
        log_message(f"Error menulis CSV dengan penguncian: {e}")
        return False

def write_to_csv(csv_path, header, data_row):
    csv_dir = os.path.dirname(csv_path)
    if not os.path.exists(csv_dir):
        try:
            os.makedirs(csv_dir)
            log_message(f"  Membuat direktori CSV: {csv_dir}")
        except Exception as e:
            log_message(f"  Error: Gagal membuat direktori CSV '{csv_dir}': {e}")
            return False
    file_exists = os.path.isfile(csv_path)
    try:
        with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
            if not file_exists or os.path.getsize(csv_path) == 0: 
                writer.writerow(header)
            writer.writerow(data_row)
        return True
    except Exception as e:
        log_message(f"  Error: Gagal menulis ke file CSV '{os.path.basename(csv_path)}': {e}")
        return False

def read_api_keys(file_path):
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            keys = [line.strip() for line in f if line.strip()]
            if not keys:
                log_message(f"Warning: File API key '{os.path.basename(file_path)}' kosong atau tidak berisi kunci valid.")
                return []
            return keys
    except FileNotFoundError:
        log_message(f"Error: File API key tidak ditemukan di {file_path}")
        return None
    except Exception as e:
        log_message(f"Error saat membaca file API key '{os.path.basename(file_path)}': {e}")
        return None

def is_running_as_executable():
    """
    Memeriksa apakah program berjalan sebagai executable.
    """
    global IS_NUITKA_EXECUTABLE
    if IS_NUITKA_EXECUTABLE:
        return True
    if getattr(sys, 'frozen', False):
        IS_NUITKA_EXECUTABLE = True
        return True
    for attr in ['__compiled__', '_MEIPASS', '_MEIPASS2']:
        if hasattr(sys, attr):
            IS_NUITKA_EXECUTABLE = True
            return True
    try:
        import os
        import sys
        exe_path = os.path.realpath(sys.executable).lower()
        if (exe_path.endswith('.exe') and 'python' not in exe_path) or '.exe.' in exe_path:
            IS_NUITKA_EXECUTABLE = True
            return True
    except Exception:
        pass
    return False

# Tambahkan variabel global untuk flag
IS_NUITKA_EXECUTABLE = False
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

# src/metadata/exif_writer.py
import os
import time
import sys
import subprocess
from src.utils.logging import log_message
from src.api.gemini_api import check_stop_event, is_stop_requested

def check_exiftool_exists():
    """
    Memeriksa apakah exiftool tersedia di sistem.
    
    Returns:
        Boolean: True jika exiftool ditemukan, False jika tidak.
    """
    try:
        # Try running exiftool directly first
        result = subprocess.run(["exiftool", "-ver"], check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        log_message(f"Exiftool ditemukan (versi: {result.stdout.strip()}).")
        global EXIFTOOL_PATH # Set global path if found directly
        EXIFTOOL_PATH = "exiftool"
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        # If direct call fails, search in potential paths
        try:
            if getattr(sys, 'frozen', False):
                if hasattr(sys, '_MEIPASS'):
                    base_dir = sys._MEIPASS
                elif hasattr(sys, '_MEIPASS2'):
                     base_dir = sys._MEIPASS2
                else:
                    # Fallback for some frozen environments
                    base_dir = os.path.dirname(sys.executable)
                log_message(f"Menggunakan base_dir untuk Nuitka/PyInstaller: {base_dir}")
            else:
                # Running as script
                base_dir = os.path.dirname(os.path.abspath(__file__))
                # Go up two levels from src/metadata to reach the project root
                base_dir = os.path.dirname(os.path.dirname(base_dir))

            potential_paths = [
                # Path relative to project root (for dev and correct installer structure)
                os.path.join(base_dir, "tools", "exiftool", "exiftool.exe"),
                # Paths relative to executable (might be needed for some bundlers)
                os.path.join(os.path.dirname(sys.executable), "tools", "exiftool", "exiftool.exe"),
                # Paths within potential _MEIPASS temp folders
                os.path.join(os.environ.get('TEMP', ''), "_MEI", "tools", "exiftool", "exiftool.exe"),
                # Absolute path (less likely but possible)
                os.path.abspath("tools/exiftool/exiftool.exe")
            ]

            for path in potential_paths:
                normalized_path = os.path.normpath(path)
                log_message(f"Memeriksa exiftool di: {normalized_path}")
                if os.path.exists(normalized_path):
                    # Verify it's executable (simple check)
                    try:
                         test_result = subprocess.run([normalized_path, "-ver"], check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                         log_message(f"Exiftool ditemukan dan valid di: {normalized_path} (versi: {test_result.stdout.strip()})")
                         EXIFTOOL_PATH = normalized_path # Set the found path
                         return True
                    except Exception as e_test:
                         log_message(f"  Ditemukan tapi gagal eksekusi: {normalized_path} - Error: {e_test}")
                         continue # Try next path

            log_message("Error: 'exiftool' tidak ditemukan di lokasi yang diharapkan.", "error")
            return False
        except Exception as e:
            log_message(f"Error tak terduga saat memeriksa exiftool: {e}", "error")
            return False

# Menyimpan path exiftool saat ditemukan
EXIFTOOL_PATH = None

def write_exif_with_exiftool(image_path, output_path, metadata, stop_event):
    """
    Menulis metadata EXIF ke file gambar menggunakan exiftool.

    Args:
        image_path: Path file sumber
        output_path: Path file output
        metadata: Dictionary berisi metadata (title, description, tags)
        stop_event: Event threading untuk menghentikan proses

    Returns:
        Tuple(bool, str): (True/False indicating if processing should continue, status string)
                           Possible status strings: "exif_ok", "exif_failed", "no_metadata",
                           "stopped", "copy_failed", "exiftool_not_found", "unknown_error"
    """
    title = metadata.get('title', '')
    description = metadata.get('description', '')
    tags = metadata.get('tags', [])
    cleaned_tags = [tag.strip() for tag in tags if tag.strip()]

    if stop_event.is_set() or is_stop_requested():
        log_message("  Proses dihentikan sebelum menulis EXIF.")
        return False, "stopped"

    if not os.path.exists(output_path):
        try:
            import shutil
            shutil.copy2(image_path, output_path)
        except Exception as e:
            log_message(f"  Gagal menyalin file '{os.path.basename(image_path)}' ke output: {e}")
            return False, "copy_failed" # Critical failure, cannot proceed

    if stop_event.is_set() or is_stop_requested():
        log_message("  Proses dihentikan setelah menyalin file.")
        # Even if stopped here, the file was copied, so maybe allow proceeding?
        # Let's consider this a critical stop for now.
        return False, "stopped"

    if not title and not description and not cleaned_tags:
        log_message("  Info: Tidak ada metadata valid untuk ditulis ke EXIF.")
        return True, "no_metadata" # Proceed, but indicate no metadata was written

    # Tentukan perintah exiftool yang akan digunakan
    if not EXIFTOOL_PATH:
        log_message("  Error: Path Exiftool tidak diset.", "error")
        return True, "exiftool_not_found" # Allow proceeding, but log the failure reason

    exiftool_cmd = EXIFTOOL_PATH
    log_message(f"  Menggunakan perintah exiftool: {exiftool_cmd}")

    # Bersihkan metadata yang ada terlebih dahulu (Best effort)
    clear_command = [
        exiftool_cmd,
        "-all=",
        "-overwrite_original",
        output_path
    ]
    try:
        if stop_event.is_set() or is_stop_requested():
            log_message("  Proses dihentikan sebelum membersihkan metadata.")
            return False, "stopped"

        result = subprocess.run(clear_command, check=False, capture_output=True, text=True, # check=False
                                encoding='utf-8', errors='replace', timeout=30,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode == 0:
            log_message("  Metadata lama dibersihkan dari file")
        else:
             log_message(f"  Warning: Gagal membersihkan metadata lama (Kode: {result.returncode}). Error: {result.stderr.strip()}", "warning")
             # Continue even if clearing fails

    except subprocess.TimeoutExpired:
         log_message(f"  Warning: Timeout saat membersihkan metadata lama.", "warning")
    except Exception as e:
        log_message(f"  Warning: Gagal membersihkan metadata lama: {e}", "warning")
        # Continue even if clearing fails

    if stop_event.is_set() or is_stop_requested():
        log_message("  Proses dihentikan setelah mencoba membersihkan metadata.")
        return False, "stopped"

    # Buat command untuk menulis metadata baru
    command = [
        exiftool_cmd,
        "-overwrite_original",
        "-charset", "UTF8", # Ensure UTF8 handling
        "-codedcharacterset=utf8" # Explicitly set coded character set
    ]

    if title:
        truncated_title = title[:64].strip() # Max 64 chars for Title/ObjectName
        command.extend([f'-Title={truncated_title}', f'-ObjectName={truncated_title}'])

    if description:
        # Use common tags for description
        command.extend([f'-XPComment={description}', f'-UserComment={description}', f'-ImageDescription={description}'])

    if cleaned_tags:
        # Reset and add keywords/subject tags
        command.append("-Keywords=")
        command.append("-Subject=")
        for tag in cleaned_tags:
             # Ensure tags are properly handled, especially with special characters
             # Exiftool usually handles this, but be mindful
             command.append(f"-Keywords+={tag}")
             command.append(f"-Subject+={tag}")

    command.append(output_path)

    exiftool_process = None
    try:
        if stop_event.is_set() or is_stop_requested():
            log_message("  Proses dihentikan sebelum menulis metadata baru.")
            return False, "stopped"

        # Use Popen for better control and stop handling
        exiftool_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8', # Specify encoding
            errors='replace', # Handle potential encoding errors
            creationflags=subprocess.CREATE_NO_WINDOW # Hide console window on Windows
        )

        # Wait for process completion or stop signal
        while exiftool_process.poll() is None:
            if stop_event.is_set() or is_stop_requested():
                log_message("  Menghentikan proses exiftool yang sedang berjalan.")
                try:
                    exiftool_process.terminate()
                    time.sleep(0.5) # Give it time to terminate
                    if exiftool_process.poll() is None:
                        exiftool_process.kill() # Force kill if terminate fails
                except Exception as kill_e:
                     log_message(f"  Error saat menghentikan exiftool: {kill_e}")
                return False, "stopped" # Return stopped status
            time.sleep(0.1) # Prevent busy-waiting

        stdout, stderr = exiftool_process.communicate()
        return_code = exiftool_process.returncode

        if return_code == 0:
            # Check stdout for confirmation, though return code 0 is usually enough
            if stdout and "1 image files updated" in stdout:
                 log_message(f"  ✓ Metadata EXIF berhasil ditulis ke {os.path.basename(output_path)}")
            else:
                 log_message(f"  ✓ Metadata EXIF ditulis (return code 0, output: {stdout.strip()})")
            if stderr: # Log stderr even on success, might contain warnings
                 log_message(f"  Exiftool stderr (sukses): {stderr.strip()}")
            return True, "exif_ok"
        else:
            # EXIF write failed
            log_message(f"  ✗ Gagal menulis EXIF (exit code {return_code}) pada {os.path.basename(output_path)}")
            if stderr:
                log_message(f"  Exiftool stderr (gagal): {stderr.strip()}")
            if stdout: # Log stdout on failure too, might give clues
                 log_message(f"  Exiftool stdout (gagal): {stdout.strip()}")
            return True, "exif_failed" # Proceed, but report failure

    except subprocess.TimeoutExpired:
        log_message(f"  Error: Exiftool timeout saat memproses {os.path.basename(output_path)}")
        if exiftool_process and exiftool_process.poll() is None:
            try: exiftool_process.kill()
            except: pass
        return True, "exif_failed" # Proceed, report failure
    except FileNotFoundError:
        # This case should be caught by the initial EXIFTOOL_PATH check, but handle defensively
        log_message("  Error: Perintah 'exiftool' tidak ditemukan saat eksekusi.", "error")
        return True, "exiftool_not_found" # Proceed, report failure
    except Exception as e:
        # Catch other potential errors during Popen or communicate
        log_message(f"  Error tak terduga saat menjalankan exiftool: {e}", "error")
        if exiftool_process and exiftool_process.poll() is None:
             try: exiftool_process.kill()
             except: pass
        import traceback
        log_message(f"  Traceback: {traceback.format_exc()}", "error")
        return True, "exif_failed" # Proceed, report as general exif failure

def write_exif_to_video(input_path, output_path, metadata, stop_event):
    """
    Menulis metadata ke file video menggunakan exiftool.

    Args:
        input_path: Path file sumber
        output_path: Path file output
        metadata: Dictionary berisi metadata (title, description, tags)
        stop_event: Event threading untuk menghentikan proses

    Returns:
        Tuple(bool, str): (True/False indicating if processing should continue, status string)
                           Possible status strings: "exif_ok", "exif_failed", "no_metadata",
                           "stopped", "copy_failed", "exiftool_not_found", "unknown_error"
                           (Note: copy_failed is less likely here as video processing often creates the output)
    """
    title = metadata.get('title', '')
    description = metadata.get('description', '')
    tags = metadata.get('tags', [])
    cleaned_tags = [tag.strip() for tag in tags if tag.strip()]

    if stop_event.is_set() or is_stop_requested():
        log_message("  Proses dihentikan sebelum menulis metadata ke video.")
        return False, "stopped"

    # Assume output_path exists as video processing likely created it
    # Add a check just in case?
    if not os.path.exists(output_path):
         log_message(f"  Error: File video output tidak ditemukan: {output_path}", "error")
         # This might indicate a prior failure in video processing itself
         return False, "output_missing" # Cannot proceed without output file

    if not title and not description and not cleaned_tags:
        log_message("  Info: Tidak ada metadata valid untuk ditulis ke video.")
        return True, "no_metadata"

    # Tentukan perintah exiftool
    if not EXIFTOOL_PATH:
        log_message("  Error: Path Exiftool tidak diset.", "error")
        return True, "exiftool_not_found"

    exiftool_cmd = EXIFTOOL_PATH
    log_message(f"  Menggunakan perintah exiftool untuk video: {exiftool_cmd}")

    # Buat command untuk menulis metadata ke video
    # Video tags can be different, use common ones
    command = [
        exiftool_cmd,
        "-overwrite_original", # Modify the file in place
        "-charset", "UTF8",
        "-codedcharacterset=utf8"
    ]

    if title:
        # Common video title tags
        truncated_title = title[:160].strip() # Allow longer titles for video
        command.extend([f'-Title={truncated_title}', f'-Track1:Title={truncated_title}', f'-Movie:Title={truncated_title}'])

    if description:
        # Common video description/comment tags
        command.extend([
            f'-Description={description}',
            f'-Comment={description}',
            f'-UserComment={description}', # Sometimes used
            f'-Track1:Comment={description}',
            f'-Movie:Comment={description}',
            f'-Caption-Abstract={description}' # IPTC tag, sometimes supported
        ])

    if cleaned_tags:
        # Common video keyword/subject tags
        command.append("-Keywords=")
        command.append("-Subject=")
        command.append("-Category=") # Another common tag
        for tag in cleaned_tags:
             command.append(f"-Keywords+={tag}")
             command.append(f"-Subject+={tag}")
             command.append(f"-Category+={tag}") # Add to category too

    command.append(output_path)

    exiftool_process = None
    try:
        if stop_event.is_set() or is_stop_requested():
            log_message("  Proses dihentikan sebelum menulis metadata video.")
            return False, "stopped"

        exiftool_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        while exiftool_process.poll() is None:
            if stop_event.is_set() or is_stop_requested():
                log_message("  Menghentikan proses exiftool untuk video.")
                try:
                    exiftool_process.terminate()
                    time.sleep(0.5)
                    if exiftool_process.poll() is None:
                        exiftool_process.kill()
                except Exception as kill_e:
                     log_message(f"  Error saat menghentikan exiftool video: {kill_e}")
                return False, "stopped"
            time.sleep(0.1)

        stdout, stderr = exiftool_process.communicate()
        return_code = exiftool_process.returncode

        if return_code == 0:
            log_message(f"  ✓ Metadata berhasil ditulis ke file video {os.path.basename(output_path)}")
            if stderr:
                 log_message(f"  Exiftool stderr (sukses video): {stderr.strip()}")
            return True, "exif_ok"
        else:
            log_message(f"  ✗ Gagal menulis metadata video (exit code {return_code}) pada {os.path.basename(output_path)}")
            if stderr:
                log_message(f"  Exiftool stderr (gagal video): {stderr.strip()}")
            if stdout:
                 log_message(f"  Exiftool stdout (gagal video): {stdout.strip()}")
            return True, "exif_failed" # Proceed, report failure

    except subprocess.TimeoutExpired:
        log_message(f"  Error: Exiftool timeout saat memproses video {os.path.basename(output_path)}")
        if exiftool_process and exiftool_process.poll() is None:
            try: exiftool_process.kill()
            except: pass
        return True, "exif_failed"
    except FileNotFoundError:
        log_message("  Error: Perintah 'exiftool' tidak ditemukan saat eksekusi video.", "error")
        return True, "exiftool_not_found"
    except Exception as e:
        log_message(f"  Error tak terduga saat menulis metadata video: {e}", "error")
        if exiftool_process and exiftool_process.poll() is None:
             try: exiftool_process.kill()
             except: pass
        import traceback
        log_message(f"  Traceback: {traceback.format_exc()}", "error")
        return True, "exif_failed"

# Pastikan EXIFTOOL_PATH diinisialisasi di awal
# check_exiftool_exists() # Panggil ini di awal aplikasi, bukan di sini

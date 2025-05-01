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

# src/processing/vector_processing/format_eps_ai_processing.py
import os
import time
import subprocess
import platform # Import platform for OS specific checks if needed
from src.utils.logging import log_message
from src.api.gemini_api import check_stop_event
# Import the variable holding the discovered Ghostscript path - REMOVED
# from src.utils.system_checks import GHOSTSCRIPT_PATH
# Global import removed, path is passed as parameter

def convert_eps_to_jpg(eps_path, output_jpg_path, ghostscript_path, stop_event=None):
    """
    Mengkonversi file EPS/AI ke JPG menggunakan path Ghostscript yang ditemukan saat startup.

    Args:
        eps_path: Path file EPS/AI sumber
        output_jpg_path: Path file JPG tujuan
        ghostscript_path: Full path to the Ghostscript executable
        stop_event: Event threading untuk menghentikan proses

    Returns:
        Tuple (success, error_message):
            - success: Boolean yang menunjukkan keberhasilan konversi
            - error_message: String pesan error (None jika sukses)
    """
    filename = os.path.basename(eps_path)
    log_message(f"Memulai konversi EPS/AI ke JPG: {filename}")

    # --- Cek Path Ghostscript ---
    if not ghostscript_path: # Check the parameter
        error_message = "Error: Ghostscript executable path not found during application startup check."
        log_message(f"  ✗ {error_message}")
        return False, error_message

    # --- Cek Stop Event Awal ---
    if check_stop_event(stop_event, f"Konversi EPS/AI dibatalkan sebelum mulai: {filename}"):
        return False, f"Konversi dibatalkan sebelum mulai: {filename}"

    # --- Persiapan Perintah Ghostscript ---
    command = [
        ghostscript_path,           # Gunakan path dari parameter
        "-sDEVICE=jpeg",
        "-dEPSCrop",                # Use EPS BoundingBox for cropping
        "-dJPEGQ=90",               # Kualitas JPEG (0-100)
        "-dBATCH",                  # Mode batch (keluar setelah selesai)
        "-dNOPAUSE",                # Jangan menunggu antar halaman
        "-dSAFER",                  # Mode aman (membatasi akses file)
        "-dGraphicsAlphaBits=4",    # Penanganan alpha untuk grafis
        "-dTextAlphaBits=4",        # Penanganan alpha untuk teks
        # "-dHaveTransparency=true",  # Mungkin tidak diperlukan untuk output JPEG
        # "-dBackgroundColor=16#FFFFFF", # Latar belakang putih (JPEG tidak mendukung transparansi)
        f"-sOutputFile={output_jpg_path}", # File output
        eps_path                    # File input
    ]

    success = False
    final_error_message = f"Unknown error during Ghostscript conversion for {filename}."
    process = None # Initialize process variable

    # --- Eksekusi Ghostscript ---
    try:
        log_message(f"  Menjalankan Ghostscript: {ghostscript_path} ...")
        # Gunakan CREATE_NO_WINDOW hanya di Windows
        creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags
        )

        # --- Loop Pemantauan Proses dengan Timeout dan Stop Event ---
        start_time = time.time()
        timeout_seconds = 180 # Timeout 3 menit per file (sesuaikan jika perlu)

        while process.poll() is None:
            # Cek stop event
            if check_stop_event(stop_event, f"Menghentikan konversi Ghostscript: {filename}"):
                log_message(f"  Stop event triggered, terminating Ghostscript process for {filename}")
                try:
                    process.terminate()
                    process.wait(timeout=1) # Tunggu sebentar untuk terminate
                except subprocess.TimeoutExpired:
                    log_message(f"  Ghostscript tidak terminate, killing process for {filename}")
                    process.kill()
                except Exception as term_err:
                    log_message(f"  Error saat terminasi Ghostscript for {filename}: {term_err}")
                return False, f"Konversi Ghostscript dihentikan: {filename}"

            # Cek timeout
            if time.time() - start_time > timeout_seconds:
                log_message(f"  Ghostscript process timed out (> {timeout_seconds}s) for {filename}, terminating.")
                try:
                    process.terminate()
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    log_message(f"  Ghostscript tidak terminate setelah timeout, killing process for {filename}")
                    process.kill()
                except Exception as term_err:
                    log_message(f"  Error saat terminasi Ghostscript setelah timeout for {filename}: {term_err}")
                return False, f"Konversi Ghostscript timeout: {filename}"

            time.sleep(0.1) # Hindari busy-waiting

        # --- Proses Selesai, Ambil Output ---
        try:
            stdout, stderr = process.communicate(timeout=15) # Timeout untuk communicate
        except subprocess.TimeoutExpired:
            log_message(f"  Ghostscript communicate() timed out for {filename}. Killing process.")
            process.kill()
            # Coba ambil output lagi setelah kill
            try:
                stdout, stderr = process.communicate()
            except Exception as final_comm_err:
                 log_message(f"  Error getting output even after kill for {filename}: {final_comm_err}")
                 stdout, stderr = b"", b""
        except Exception as comm_err:
            log_message(f"  Error during Ghostscript communicate() for {filename}: {comm_err}")
            stdout, stderr = b"", b"" # Asumsi tidak ada output

        return_code = process.returncode

        # --- Evaluasi Hasil ---
        if return_code == 0:
            # Periksa apakah file output ada dan tidak kosong
            if os.path.exists(output_jpg_path) and os.path.getsize(output_jpg_path) > 100: # Cek ukuran > 100 bytes (arbitrary small size)
                log_message(f"  ✓ Konversi EPS/AI ke JPG berhasil: {os.path.basename(output_jpg_path)}")
                success = True
                final_error_message = None # Berhasil, tidak ada error
            else:
                final_error_message = f"Ghostscript selesai (kode 0) tapi file output '{os.path.basename(output_jpg_path)}' tidak valid atau terlalu kecil."
                log_message(f"  ✗ {final_error_message}")
                if os.path.exists(output_jpg_path): # Hapus file output yang gagal
                    try: os.remove(output_jpg_path)
                    except Exception: pass
        else:
            # Decode stderr dengan aman
            try:
                error_output = stderr.decode(errors='replace').strip()
            except Exception as decode_err:
                error_output = f"(Tidak dapat decode stderr: {decode_err})"
            final_error_message = f"Gagal konversi EPS/AI dengan Ghostscript (kode {return_code}): {error_output[:350]}{'...' if len(error_output) > 350 else ''}"
            log_message(f"  ✗ {final_error_message}")

    except FileNotFoundError:
        # Seharusnya tidak terjadi jika GHOSTSCRIPT_PATH valid
        final_error_message = f"Fatal Error: Ghostscript executable not found at the expected path: {ghostscript_path}"
        log_message(f"  ✗ {final_error_message}")
    except Exception as e:
        final_error_message = f"Error tak terduga saat menjalankan Ghostscript process: {e}"
        log_message(f"  ✗ {final_error_message}")
        if process and process.poll() is None: # Jika proses masih berjalan saat error lain terjadi
             try: process.kill()
             except Exception: pass

    # --- Pembersihan File Output Gagal ---
    if not success and os.path.exists(output_jpg_path):
        try:
            os.remove(output_jpg_path)
            log_message(f"  Membersihkan file output gagal: {os.path.basename(output_jpg_path)}")
        except Exception as del_err:
            log_message(f"  Gagal membersihkan file output {os.path.basename(output_jpg_path)}: {del_err}")

    return success, final_error_message
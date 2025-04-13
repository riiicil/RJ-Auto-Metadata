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
from src.utils.logging import log_message
from src.api.gemini_api import check_stop_event

def convert_eps_to_jpg(eps_path, output_jpg_path, stop_event=None):
    """
    Mengkonversi file EPS/AI ke JPG menggunakan Ghostscript.
    
    Args:
        eps_path: Path file EPS/AI sumber
        output_jpg_path: Path file JPG tujuan
        stop_event: Event threading untuk menghentikan proses
        
    Returns:
        Tuple (success, error_message): 
            - success: Boolean yang menunjukkan keberhasilan konversi
            - error_message: String pesan error (None jika sukses)
    """
    filename = os.path.basename(eps_path)
    # log_message(f"  Mencoba konversi EPS ke JPG menggunakan Ghostscript: {filename}")
    
    # Daftar perintah Ghostscript yang mungkin ada
    gs_commands = ['gswin64c', 'gs']
    success = False
    last_error = "Ghostscript command not found or failed."
    
    for gs_cmd in gs_commands:
        if check_stop_event(stop_event, f"  Konversi EPS dibatalkan: {filename}"):
            return False, f"Konversi dibatalkan: {filename}"
        
        command = [
            gs_cmd,
            "-sDEVICE=jpeg",
            "-dJPEGQ=90",
            "-r300",
            "-dBATCH",
            "-dNOPAUSE",
            "-dSAFER",
            f"-sOutputFile={output_jpg_path}",
            eps_path
        ]
        
        try:
            # log_message(f"  Menjalankan: {' '.join(command)}")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            try:
                while process.poll() is None:
                    if check_stop_event(stop_event, f"  Menghentikan konversi Ghostscript: {filename}"):
                        process.terminate()
                        time.sleep(0.5)
                        if process.poll() is None: process.kill()
                        return False, f"Konversi Ghostscript dihentikan: {filename}"
                    time.sleep(0.1)
                
                stdout, stderr = process.communicate()
                return_code = process.returncode
            except Exception as comm_error:
                 log_message(f"  Error saat berkomunikasi dengan proses Ghostscript: {comm_error}")
                 return_code = process.poll() if process else -1 
                 stderr = b""
            
            if return_code == 0:
                if os.path.exists(output_jpg_path) and os.path.getsize(output_jpg_path) > 0:
                    log_message(f"  Konversi EPS ke JPG berhasil dengan '{gs_cmd}': {os.path.basename(output_jpg_path)}")
                    success = True
                    break
                else:
                    last_error = f"Ghostscript ({gs_cmd}) selesai tapi file output tidak valid."
                    log_message(f"  {last_error}")
            else:
                error_output = stderr.decode('utf-8', errors='replace').strip()
                last_error = f"Gagal konversi EPS dengan '{gs_cmd}' (exit code {return_code}): {error_output[:250]}..."
                log_message(f"  {last_error}")
        except FileNotFoundError:
            last_error = f"Perintah '{gs_cmd}' tidak ditemukan. Mencoba alternatif..."
            log_message(f"  {last_error}")
            continue
        except Exception as e:
            last_error = f"Error tak terduga saat konversi EPS dengan '{gs_cmd}': {e}"
            log_message(f"  {last_error}")
            continue
    
    if not success:
        if os.path.exists(output_jpg_path):
            try: os.remove(output_jpg_path)
            except Exception: pass
        return False, f"Gagal mengkonversi EPS setelah mencoba semua perintah: {filename}. Error terakhir: {last_error}"
    
    return True, None
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
        result = subprocess.run(["exiftool", "-ver"], check=True, capture_output=True, text=True)
        log_message(f"Exiftool ditemukan (versi: {result.stdout.strip()}).")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        try:
            if getattr(sys, 'frozen', False):
                if hasattr(sys, '_MEIPASS'):
                    base_dir = sys._MEIPASS
                else:
                    if hasattr(sys, '_MEIPASS2'):
                        base_dir = sys._MEIPASS2
                    else:
                        base_dir = os.path.dirname(sys.executable)
                log_message(f"Menggunakan base_dir untuk Nuitka/PyInstaller: {base_dir}")
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            
            potential_paths = [
                os.path.join(base_dir, "exiftool.exe"),
                os.path.join(base_dir, "tools", "exiftool.exe"), 
                os.path.join(os.path.dirname(base_dir), "tools", "exiftool.exe"),
                os.path.join(os.environ.get('TEMP', ''), "_MEI", "tools", "exiftool.exe"),
                os.path.abspath("tools/exiftool.exe")
            ]
            
            for path in potential_paths:
                log_message(f"Memeriksa exiftool di: {path}")
                if os.path.exists(path):
                    global EXIFTOOL_PATH
                    EXIFTOOL_PATH = path
                    log_message(f"Exiftool ditemukan di: {path}")
                    return True
            
            log_message("Error: 'exiftool' tidak ditemukan.")
            return False
        except Exception as e:
            log_message(f"Error tak terduga saat memeriksa exiftool: {e}")
            return False

def write_exif_with_exiftool(image_path, output_path, metadata, stop_event):
    """
    Menulis metadata EXIF ke file gambar menggunakan exiftool.
    
    Args:
        image_path: Path file sumber
        output_path: Path file output
        metadata: Dictionary berisi metadata (title, description, tags)
        stop_event: Event threading untuk menghentikan proses
        
    Returns:
        Boolean: True jika berhasil, False jika gagal
    """
    title = metadata.get('title', '')
    description = metadata.get('description', '')
    tags = metadata.get('tags', [])
    cleaned_tags = [tag.strip() for tag in tags if tag.strip()]
    
    if stop_event.is_set() or is_stop_requested():
        log_message("  Proses dihentikan sebelum menulis EXIF.")
        return False
    
    if not os.path.exists(output_path):
        try:
            import shutil
            shutil.copy2(image_path, output_path)
        except Exception as e:
            log_message(f"  Gagal menyalin file '{os.path.basename(image_path)}' ke output: {e}")
            return False
    
    if stop_event.is_set() or is_stop_requested():
        log_message("  Proses dihentikan setelah menyalin file.")
        return False
    
    if not title and not description and not cleaned_tags:
        log_message("  Info: Tidak ada metadata valid untuk ditulis ke EXIF.")
        return True
    
    # Bersihkan metadata yang ada terlebih dahulu
    clear_command = [
        "exiftool",
        "-all=",
        "-overwrite_original",
        output_path
    ]
    
    try:
        if stop_event.is_set() or is_stop_requested():
            log_message("  Proses dihentikan sebelum menjalankan exiftool.")
            return False
        
        result = subprocess.run(clear_command, check=True, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=30,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        log_message("  Metadata lama dibersihkan dari file")
    except Exception as e:
        log_message(f"  Warning: Gagal membersihkan metadata lama: {e}")
    
    if stop_event.is_set() or is_stop_requested():
        log_message("  Proses dihentikan setelah membersihkan metadata.")
        return False
    
    # Buat command untuk menulis metadata baru
    command = [
        "exiftool",
        "-overwrite_original",
        "-charset", "UTF8",
        "-codedcharacterset=utf8"
    ]
    
    if title:
        truncated_title = title[:64].strip()
        command.extend([f'-Title={truncated_title}', f'-ObjectName={truncated_title}'])
    
    if description:
        command.extend([f'-XPComment={description}', f'-UserComment={description}', f'-ImageDescription={description}'])

    if cleaned_tags:
        command.append("-Keywords=")
        command.append("-Subject=")
        for tag in cleaned_tags:
             command.append(f"-Keywords+={tag}")
             command.append(f"-Subject+={tag}")
    
    command.append(output_path)
    
    exiftool_process = None
    try:
        if stop_event.is_set() or is_stop_requested():
            log_message("  Proses dihentikan sebelum menulis metadata baru.")
            return False
        
        exiftool_process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            encoding='utf-8', 
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        try:
            while exiftool_process.poll() is None:
                if stop_event.is_set() or is_stop_requested():
                    log_message("  Menghentikan proses exiftool yang sedang berjalan.")
                    exiftool_process.terminate()
                    time.sleep(0.5)
                    if exiftool_process.poll() is None:
                        exiftool_process.kill()
                    return False
                time.sleep(0.1)
            
            stdout, stderr = exiftool_process.communicate()
            
            if exiftool_process.returncode != 0:
                log_message(f"  Error exiftool (exit code {exiftool_process.returncode})")
                return False
            
            if stdout:
                output_lines = stdout.strip().splitlines()
                if output_lines and "1 image files updated" in output_lines[-1]:
                    pass
                else:
                    log_message(f"  Exiftool output (mungkin sukses):\n{stdout.strip()}")
            
            if stderr:
                log_message(f"  Exiftool stderr: {stderr.strip()}")
            
            return True
        except Exception as e:
            if exiftool_process and exiftool_process.poll() is None:
                try:
                    exiftool_process.terminate()
                except:
                    pass
            log_message(f"  Error saat menjalankan exiftool: {e}")
            return False
    except subprocess.TimeoutExpired:
        if exiftool_process and exiftool_process.poll() is None:
            try:
                exiftool_process.terminate()
            except:
                pass
        log_message(f"  Error: Exiftool timeout saat memproses {os.path.basename(output_path)}")
        return False
    except FileNotFoundError:
        log_message("  Error: Perintah 'exiftool' tidak ditemukan. Pastikan terinstal dan di PATH.")
        return False
    except subprocess.CalledProcessError as e:
        log_message(f"  Gagal menulis EXIF dengan exiftool (exit code {e.returncode}) pada {os.path.basename(output_path)}")
        return False
    except Exception as e:
        log_message(f"  Error tak terduga saat menjalankan exiftool: {e}")
        return False

def write_exif_to_video(input_path, output_path, metadata, stop_event):
    """
    Menulis metadata ke file video menggunakan exiftool.
    
    Args:
        input_path: Path file sumber
        output_path: Path file output
        metadata: Dictionary berisi metadata (title, description, tags)
        stop_event: Event threading untuk menghentikan proses
        
    Returns:
        Boolean: True jika berhasil, False jika gagal
    """
    title = metadata.get('title', '')
    description = metadata.get('description', '')
    tags = metadata.get('tags', [])
    cleaned_tags = [tag.strip() for tag in tags if tag.strip()]
    
    if stop_event.is_set() or is_stop_requested():
        log_message("  Proses dihentikan sebelum menulis metadata ke video.")
        return False
    
    # Buat command untuk menulis metadata ke video
    command = [
        "exiftool",
        "-overwrite_original",
        "-charset", "UTF8",
        "-codedcharacterset=utf8"
    ]
    
    if title:
        truncated_title = title[:160].strip()
        command.extend([f'-Title={truncated_title}'])
    
    if description:
        command.extend([
            f'-Description={description}', 
            f'-Comment={description}',
            f'-Caption-Abstract={description}'
        ])
    
    if cleaned_tags:
        command.append("-Keywords=")
        command.append("-Subject=")
        for tag in cleaned_tags:
             command.append(f"-Keywords+={tag}")
             command.append(f"-Subject+={tag}")
    
    command.append(output_path)
    
    exiftool_process = None
    try:
        if stop_event.is_set() or is_stop_requested():
            log_message("  Proses dihentikan sebelum menulis metadata video.")
            return False
        
        exiftool_process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            encoding='utf-8', 
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        try:
            while exiftool_process.poll() is None:
                if stop_event.is_set() or is_stop_requested():
                    log_message("  Menghentikan proses exiftool untuk video.")
                    exiftool_process.terminate()
                    time.sleep(0.5)
                    if exiftool_process.poll() is None:
                        exiftool_process.kill()
                    return False
                time.sleep(0.1)
            
            stdout, stderr = exiftool_process.communicate()
            
            if exiftool_process.returncode != 0:
                log_message(f"  Error exiftool untuk video (exit code {exiftool_process.returncode})")
                if stderr:
                    log_message(f"  Exiftool stderr: {stderr.strip()}")
                return False
            
            if stdout:
                if "1 image files updated" in stdout:
                    log_message(f"  Metadata berhasil ditulis ke file video")
                else:
                    log_message(f"  Exiftool output video: {stdout.strip()}")
            
            return True
        except Exception as e:
            if exiftool_process and exiftool_process.poll() is None:
                try:
                    exiftool_process.terminate()
                except:
                    pass
            log_message(f"  Error saat menjalankan exiftool untuk video: {e}")
            return False
    except subprocess.TimeoutExpired:
        if exiftool_process and exiftool_process.poll() is None:
            try:
                exiftool_process.terminate()
            except:
                pass
        log_message(f"  Error: Exiftool timeout saat memproses video {os.path.basename(output_path)}")
        return False
    except FileNotFoundError:
        log_message("  Error: Perintah 'exiftool' tidak ditemukan.")
        return False
    except Exception as e:
        log_message(f"  Error tak terduga saat menulis metadata video: {e}")
        return False

# Menyimpan path exiftool saat ditemukan
EXIFTOOL_PATH = None
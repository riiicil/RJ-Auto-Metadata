# src/utils/compression.py
import os
import time
import random
from PIL import Image
from src.utils.logging import log_message
from src.api.gemini_api import check_stop_event, is_stop_requested

# Konstanta
TEMP_COMPRESSION_FOLDER_NAME = "temp_compressed"
MAX_IMAGE_SIZE_MB = 2
COMPRESSION_QUALITY = 20 
MAX_IMAGE_DIMENSION = 3000 

def get_temp_compression_folder(base_dir=None, output_dir=None):
    """
    Dapatkan folder untuk menyimpan file kompresi sementara.
    """
    if output_dir and os.path.exists(output_dir) and os.path.isdir(output_dir):
        temp_folder = os.path.join(output_dir, TEMP_COMPRESSION_FOLDER_NAME)
        try:
            if not os.path.exists(temp_folder):
                os.makedirs(temp_folder, exist_ok=True)
                log_message(f"Folder kompresi sementara dibuat di output: {temp_folder}")
            return temp_folder
        except Exception as e:
            log_message(f"Error membuat folder kompresi di output: {e}")
    
    if base_dir and os.path.exists(base_dir) and os.path.isdir(base_dir):
        temp_folder = os.path.join(base_dir, TEMP_COMPRESSION_FOLDER_NAME)
        try:
            if not os.path.exists(temp_folder):
                os.makedirs(temp_folder, exist_ok=True)
                log_message(f"Folder kompresi sementara dibuat di input: {temp_folder}")
            return temp_folder
        except Exception as e:
            log_message(f"Error membuat folder kompresi di input: {e}")
    
    try:
        import tempfile
        system_temp = os.path.join(tempfile.gettempdir(), TEMP_COMPRESSION_FOLDER_NAME)
        os.makedirs(system_temp, exist_ok=True)
        log_message(f"Menggunakan folder temp sistem: {system_temp}")
        return system_temp
    except Exception as e:
        log_message(f"Error membuat folder kompresi di sistem: {e}")
        return None

def compress_image(input_path, temp_folder=None, max_size_mb=MAX_IMAGE_SIZE_MB, quality=COMPRESSION_QUALITY, max_dimension=MAX_IMAGE_DIMENSION, stop_event=None):
    try:
        if stop_event and stop_event.is_set() or is_stop_requested():
            log_message("  Kompresi dibatalkan karena permintaan berhenti.")
            return input_path, False
        
        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        filename = os.path.basename(input_path)
        
        if file_size_mb <= max_size_mb:
            log_message(f"  File ukuran {file_size_mb:.2f}MB tidak perlu kompresi: {filename}")
            return input_path, False
        
        if temp_folder is None:
            parent_dir = os.path.dirname(input_path)
            temp_folder = os.path.join(parent_dir, TEMP_COMPRESSION_FOLDER_NAME)
        
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder, exist_ok=True)
            log_message(f"  Folder kompresi dibuat: {temp_folder}")
        
        if stop_event and stop_event.is_set() or is_stop_requested():
            log_message("  Kompresi dibatalkan karena permintaan berhenti.")
            return input_path, False
        
        base, ext = os.path.splitext(filename)
        ext_lower = ext.lower()
        
        try:
            with Image.open(input_path) as img:
                original_width, original_height = img.size
                original_mode = img.mode
                has_transparency = original_mode == 'RGBA' or original_mode == 'LA' or 'transparency' in img.info
                
                if stop_event and stop_event.is_set() or is_stop_requested():
                    log_message("  Kompresi dibatalkan karena permintaan berhenti (setelah load image).")
                    return input_path, False
                
                # Resize jika dimensi terlalu besar
                scale_factor = 1.0
                if original_width > max_dimension or original_height > max_dimension:
                    scale_factor = min(max_dimension / original_width, max_dimension / original_height)
                    new_width = int(original_width * scale_factor)
                    new_height = int(original_height * scale_factor)
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    log_message(f"  Resize {filename}: {original_width}x{original_height} → {new_width}x{new_height}")
                
                if stop_event and stop_event.is_set() or is_stop_requested():
                    log_message("  Kompresi dibatalkan karena permintaan berhenti (setelah resize).")
                    return input_path, False
                
                # Adaptif quality berdasarkan ukuran file
                adaptive_quality = max(10, quality - int(min(file_size_mb, 50) / 10))
                
                # Untuk file PNG
                if ext_lower == '.png':
                    jpg_path = os.path.join(temp_folder, f"{base}_compressed.jpg")
                    png_path = os.path.join(temp_folder, f"{base}_compressed.png")
                    
                    if stop_event and stop_event.is_set() or is_stop_requested():
                        log_message("  Kompresi dibatalkan karena permintaan berhenti (sebelum konversi ke JPG).")
                        return input_path, False
                    
                    log_message(f"  File PNG perlu kompresi. Mencoba konversi ke JPG.")
                    try:
                        if original_mode in ['RGBA', 'LA']:
                            log_message(f"  Konversi PNG (semula transparan) ke JPG dengan background putih")
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            alpha_channel = img.split()[-1]
                            background.paste(img, mask=alpha_channel)
                            
                            if stop_event and stop_event.is_set() or is_stop_requested():
                                log_message("  Kompresi dibatalkan karena permintaan berhenti (setelah prepare background).")
                                return input_path, False
                            
                            background.save(jpg_path, 'JPEG', quality=adaptive_quality, optimize=True)
                        else:
                            if stop_event and stop_event.is_set() or is_stop_requested():
                                log_message("  Kompresi dibatalkan karena permintaan berhenti (sebelum konversi direct ke JPG).")
                                return input_path, False
                            
                            img.convert('RGB').save(jpg_path, 'JPEG', quality=adaptive_quality, optimize=True)
                        
                        if os.path.exists(jpg_path):
                            if stop_event and stop_event.is_set() or is_stop_requested():
                                try:
                                    if os.path.exists(jpg_path):
                                        os.remove(jpg_path)
                                except Exception:
                                    pass
                                log_message("  Kompresi dibatalkan karena permintaan berhenti (setelah konversi ke JPG).")
                                return input_path, False
                            
                            jpg_size_mb = os.path.getsize(jpg_path) / (1024 * 1024)
                            compression_ratio = (1 - (jpg_size_mb / file_size_mb)) * 100
                            
                            # Jika masih terlalu besar, kompres lebih lanjut
                            if jpg_size_mb > max_size_mb and adaptive_quality > 15:
                                if stop_event and stop_event.is_set() or is_stop_requested():
                                    try:
                                        if os.path.exists(jpg_path):
                                            os.remove(jpg_path)
                                    except Exception:
                                        pass
                                    log_message("  Kompresi dibatalkan karena permintaan berhenti (sebelum kompresi agresif).")
                                    return input_path, False
                                
                                log_message(f"  Ukuran JPG masih terlalu besar, kompres lebih agresif")
                                try:
                                    if original_mode in ['RGBA', 'LA']:
                                         background.save(jpg_path, 'JPEG', quality=max(10, adaptive_quality - 10), optimize=True)
                                    else:
                                         img.convert('RGB').save(jpg_path, 'JPEG', quality=max(10, adaptive_quality - 10), optimize=True)
                                    jpg_size_mb = os.path.getsize(jpg_path) / (1024 * 1024)
                                    compression_ratio = (1 - (jpg_size_mb / file_size_mb)) * 100
                                except Exception as e:
                                    log_message(f"  Error kompresi JPG agresif: {e}")
                            
                            log_message(f"  Konversi PNG→JPG: {file_size_mb:.2f}MB → {jpg_size_mb:.2f}MB ({compression_ratio:.1f}% pengurangan)")
                            return jpg_path, True
                        else:
                            log_message(f"  Error: File JPG hasil konversi tidak ditemukan.")
                            return input_path, False
                    except Exception as e:
                        log_message(f"  Error saat mencoba konversi PNG ke JPG: {e}")
                        return input_path, False
                
                # Untuk file JPG/JPEG
                elif ext_lower in ['.jpg', '.jpeg']:
                    compressed_path = os.path.join(temp_folder, f"{base}_compressed{ext}")
                    
                    if stop_event and stop_event.is_set() or is_stop_requested():
                        log_message("  Kompresi dibatalkan karena permintaan berhenti (sebelum kompresi JPG).")
                        return input_path, False
                    
                    try:
                        img.save(compressed_path, 'JPEG', quality=adaptive_quality, optimize=True)
                        
                        if stop_event and stop_event.is_set() or is_stop_requested():
                            try:
                                if os.path.exists(compressed_path):
                                    os.remove(compressed_path)
                            except Exception:
                                pass
                            log_message("  Kompresi dibatalkan karena permintaan berhenti (setelah kompresi JPG).")
                            return input_path, False
                        
                        if os.path.exists(compressed_path):
                            compressed_size_mb = os.path.getsize(compressed_path) / (1024 * 1024)
                            compression_ratio = (1 - (compressed_size_mb / file_size_mb)) * 100
                            
                            # Kompresi lebih agresif jika masih terlalu besar
                            if compressed_size_mb > max_size_mb and adaptive_quality > 15:
                                if stop_event and stop_event.is_set() or is_stop_requested():
                                    try:
                                        if os.path.exists(compressed_path):
                                            os.remove(compressed_path)
                                    except Exception:
                                        pass
                                    log_message("  Kompresi dibatalkan karena permintaan berhenti (sebelum kompresi JPG agresif).")
                                    return input_path, False
                                
                                log_message(f"  Ukuran JPG masih terlalu besar, kompres lebih agresif")
                                try:
                                    img.save(compressed_path, 'JPEG', quality=max(10, adaptive_quality - 10), optimize=True)
                                    
                                    if stop_event and stop_event.is_set() or is_stop_requested():
                                        try:
                                            if os.path.exists(compressed_path):
                                                os.remove(compressed_path)
                                        except Exception:
                                            pass
                                        log_message("  Kompresi dibatalkan karena permintaan berhenti (setelah kompresi JPG agresif).")
                                        return input_path, False
                                    
                                    compressed_size_mb = os.path.getsize(compressed_path) / (1024 * 1024)
                                    compression_ratio = (1 - (compressed_size_mb / file_size_mb)) * 100
                                except Exception as e:
                                    log_message(f"  Error kompresi JPG agresif: {e}")
                            
                            log_message(f"  Kompresi JPG: {file_size_mb:.2f}MB → {compressed_size_mb:.2f}MB ({compression_ratio:.1f}% pengurangan)")
                            return compressed_path, True
                    except Exception as e:
                        log_message(f"  Error kompresi JPG: {e}")
                        return input_path, False
                
                # Untuk format lain (SVG, EPS, dll)
                else:
                    jpg_path = os.path.join(temp_folder, f"{base}_compressed.jpg")
                    try:
                        if has_transparency:
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if original_mode == 'RGBA':
                                background.paste(img, mask=img.split()[3])
                            else:
                                background.paste(img, mask=img.split()[1])
                            background.save(jpg_path, 'JPEG', quality=adaptive_quality, optimize=True)
                        else:
                            img.convert('RGB').save(jpg_path, 'JPEG', quality=adaptive_quality, optimize=True)
                        
                        if os.path.exists(jpg_path):
                            jpg_size_mb = os.path.getsize(jpg_path) / (1024 * 1024)
                            compression_ratio = (1 - (jpg_size_mb / file_size_mb)) * 100
                            log_message(f"  Konversi {ext_lower}→JPG: {file_size_mb:.2f}MB → {jpg_size_mb:.2f}MB ({compression_ratio:.1f}% pengurangan)")
                            return jpg_path, True
                    except Exception as e:
                        log_message(f"  Error konversi format lain ke JPG: {e}")
                        return input_path, False
        
        except (IOError, OSError) as e:
            log_message(f"  Error I/O saat kompresi {filename}: {e}")
            return input_path, False
        except Exception as e:
            log_message(f"  Error kompresi {filename}: {e}")
            return input_path, False
        
        return input_path, False
    except Exception as e:
        log_message(f"  Error kompresi {os.path.basename(input_path)}: {e}")
        import traceback
        log_message(f"  Detail error: {traceback.format_exc()}")
        return input_path, False

def cleanup_temp_files(temp_folder, older_than_hours=1):
    if not temp_folder or not os.path.exists(temp_folder):
        return 0
    
    try:
        count = 0
        now = time.time()
        older_than_seconds = older_than_hours * 3600
        
        for filename in os.listdir(temp_folder):
            if "_compressed" in filename:
                file_path = os.path.join(temp_folder, filename)
                if os.path.isfile(file_path):
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > older_than_seconds:
                        try:
                            os.remove(file_path)
                            count += 1
                        except Exception as e:
                            log_message(f"Error hapus file temp {filename}: {e}")
        
        if count > 0:
            log_message(f"Dibersihkan {count} file sementara dari {temp_folder}")
        
        return count
    except Exception as e:
        log_message(f"Error membersihkan folder temp: {e}")
        return 0

def cleanup_temp_compression_folder(folder_path):
    if not folder_path or not os.path.exists(folder_path):
        return
    
    try:
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        os.rmdir(folder_path)
        log_message(f"Membersihkan folder kompresi sementara")
    except Exception as e:
        log_message(f"Error saat membersihkan folder sementara: {e}")

def manage_temp_folders(input_dir, output_dir):
    temp_folders = {}
    
    try:
        output_temp = os.path.join(output_dir, TEMP_COMPRESSION_FOLDER_NAME)
        os.makedirs(output_temp, exist_ok=True)
        temp_folders['output'] = output_temp
    except Exception as e:
        log_message(f"Error mengatur folder temp output: {e}")
    
    if not temp_folders:
        import tempfile
        system_temp = os.path.join(tempfile.gettempdir(), TEMP_COMPRESSION_FOLDER_NAME)
        os.makedirs(system_temp, exist_ok=True)
        temp_folders['system'] = system_temp
        log_message(f"Menggunakan folder temp sistem: {system_temp}")
    
    return temp_folders
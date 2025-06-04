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

# src/processing/batch_processing.py
import os
import shutil
import time
import random
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from src.utils.logging import log_message
from src.utils.file_utils import ensure_unique_title, sanitize_filename
from src.utils.file_utils import SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_VIDEO_EXTENSIONS, ALL_SUPPORTED_EXTENSIONS
from src.utils.compression import cleanup_temp_compression_folder, manage_temp_folders
from src.processing.image_processing.format_jpg_jpeg_processing import process_jpg_jpeg
from src.processing.image_processing.format_png_processing import process_png
from src.processing.vector_processing.format_eps_ai_processing import convert_eps_to_jpg
from src.processing.vector_processing.format_svg_processing import convert_svg_to_jpg
from src.processing.video_processing import process_video
from src.api.gemini_api import check_stop_event, is_stop_requested, select_smart_api_key
from src.metadata.csv_exporter import write_to_platform_csvs
from src.metadata.exif_writer import write_exif_with_exiftool

def process_vector_file(input_path, output_dir, selected_api_key: str, ghostscript_path, stop_event, auto_kategori_enabled=True, selected_model=None, keyword_count="49", priority="Kualitas"):
    """
    Memproses file vektor (EPS, AI, SVG).
    
    Args:
        input_path: Path file sumber
        output_dir: Direktori output
        selected_api_key: API key Gemini yang sudah dipilih secara cerdas
        ghostscript_path: Full path to the Ghostscript executable
        stop_event: Event threading untuk menghentikan proses
        auto_kategori_enabled: Flag untuk mengaktifkan penentuan kategori otomatis
        selected_model: Selected model for processing
        keyword_count: Number of keywords to use for processing
        priority: Priority for processing
    Returns:
        Tuple (status, metadata, output_path):
            - status: String status pemrosesan
            - metadata: Dictionary metadata hasil API, atau None jika gagal
            - output_path: Path file output, atau None jika gagal
    """
    filename = os.path.basename(input_path)
    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    is_eps_original = (ext_lower == '.eps')
    is_ai_original = (ext_lower == '.ai')
    is_svg_original = (ext_lower == '.svg')
    
    # Tentukan path output awal
    initial_output_path = os.path.join(output_dir, filename)
    temp_raster_path = None
    conversion_needed = is_eps_original or is_ai_original or is_svg_original
    
    if check_stop_event(stop_event): 
        return "stopped", None, None
    
    # Periksa apakah file output sudah ada
    if os.path.exists(initial_output_path):
        return "skipped_exists", None, initial_output_path
    
    # Dapatkan folder kompresi sementara
    chosen_temp_folder = os.path.join(output_dir, "temp_compressed")
    os.makedirs(chosen_temp_folder, exist_ok=True)
    
    # Konversi file vektor ke JPG
    if conversion_needed:
        base, _ = os.path.splitext(filename)
        if is_eps_original or is_ai_original:
            temp_raster_path = os.path.join(chosen_temp_folder, f"{base}_converted.jpg")
            conversion_func = convert_eps_to_jpg
            target_format = "JPG"
        elif is_svg_original:
            temp_raster_path = os.path.join(chosen_temp_folder, f"{base}_converted.jpg")
            conversion_func = convert_svg_to_jpg
            target_format = "JPG"
        else:
            return "failed_unknown", None, None
        
        if check_stop_event(stop_event):
            return "stopped", None, None
        
        log_message(f"  Memulai konversi {ext_lower.upper()} ke {target_format}...")
        # Pass ghostscript_path only if it's needed (i.e., for convert_eps_to_jpg)
        if conversion_func == convert_eps_to_jpg:
             conversion_success, error_msg = conversion_func(input_path, temp_raster_path, ghostscript_path, stop_event)
        else: # For SVG conversion or others that might be added
             conversion_success, error_msg = conversion_func(input_path, temp_raster_path, stop_event)
        
        if not conversion_success:
            log_message(f"  Gagal konversi {ext_lower.upper()}: {error_msg}")
            if temp_raster_path and os.path.exists(temp_raster_path):
                try: os.remove(temp_raster_path)
                except Exception: pass
            return "failed_conversion", None, None
        
        log_message(f"  Konversi {ext_lower.upper()} ke {target_format} selesai.")
        
        # Jangan lakukan apa-apa dengan raster hasil konversi di sini
        # Kita hanya gunakan untuk dapatkan metadata dari API
    
    # Memproses seperti file raster dan mendapatkan metadata
    api_key_to_use = selected_api_key
    
    # Gunakan file hasil konversi untuk mendapatkan metadata
    from src.api.gemini_api import get_gemini_metadata
    metadata_result = get_gemini_metadata(
        temp_raster_path if temp_raster_path else input_path, 
        api_key_to_use, 
        stop_event, 
        use_png_prompt=True,  # Gunakan prompt PNG untuk semua file vektor
        selected_model_input=selected_model,
        keyword_count=keyword_count,
        priority=priority
    )
    
    # Bersihkan file sementara
    if temp_raster_path and os.path.exists(temp_raster_path):
        try:
            os.remove(temp_raster_path)
            log_message(f"  File konversi sementara dihapus: {os.path.basename(temp_raster_path)}")
        except Exception as e:
            log_message(f"  Warning: Gagal hapus file konversi: {e}")
    
    if metadata_result == "stopped":
        return "stopped", None, None
    elif isinstance(metadata_result, dict) and "error" in metadata_result:
        log_message(f"  API Error detail: {metadata_result['error']}")
        return "failed_api", None, None
    elif isinstance(metadata_result, dict):
        metadata = metadata_result
    else:
        log_message(f"  API call gagal mendapatkan metadata (hasil tidak valid).")
        return "failed_api", None, None
    
    if check_stop_event(stop_event):
        return "stopped", metadata, None
    
    # Salin file ke output (vektor tidak bisa menyimpan EXIF metadata)
    try:
        if not os.path.exists(initial_output_path):
            shutil.copy2(input_path, initial_output_path)
        else:
            log_message(f"  Menimpa file output yang sudah ada: {filename}")
            shutil.copy2(input_path, initial_output_path)
        
        # Tulis metadata EXIF
        # Pastikan keyword_count ikut dikirim ke metadata
        if isinstance(metadata, dict):
            metadata['keyword_count'] = keyword_count
        proceed, exif_status = write_exif_with_exiftool(input_path, initial_output_path, metadata, stop_event)
        
        return "processed_no_exif", metadata, initial_output_path
    except Exception as e:
        log_message(f"  Gagal menyalin {filename}: {e}")
        return "failed_copy", metadata, None

def process_image(input_path, output_dir, selected_api_key: str, ghostscript_path, stop_event, auto_kategori_enabled=True, selected_model=None, keyword_count="49", priority="Kualitas"):
    """
    Memproses file gambar.
    
    Args:
        input_path: Path file sumber
        output_dir: Direktori output
        selected_api_key: API key Gemini yang sudah dipilih secara cerdas
        ghostscript_path: Full path to the Ghostscript executable (needed for vector processing)
        stop_event: Event threading untuk menghentikan proses
        auto_kategori_enabled: Flag untuk mengaktifkan penentuan kategori otomatis
        selected_model: Selected model for processing
        keyword_count: Number of keywords to use for processing
        priority: Priority for processing
    Returns:
        Tuple (status, metadata, output_path):
            - status: String status pemrosesan
            - metadata: Dictionary metadata hasil API, atau None jika gagal
            - output_path: Path file output, atau None jika gagal
    """
    filename = os.path.basename(input_path)
    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    
    # Periksa apakah file terlalu kecil
    try:
        file_size = os.path.getsize(input_path)
        if file_size < 100:
            log_message(f"  File terlalu kecil atau kosong: {filename} ({file_size} bytes)")
            return "failed_empty", None, None
    except Exception as e:
        log_message(f"  Error memeriksa file: {e}")
        return "failed_unknown", None, None
    
    # Proses berdasarkan tipe file
    if ext_lower == '.png':
        from src.processing.image_processing.format_png_processing import process_png
        return process_png(input_path, output_dir, selected_api_key, stop_event, auto_kategori_enabled, selected_model=selected_model, keyword_count=keyword_count, priority=priority)
    elif ext_lower in ['.eps', '.ai', '.svg']:
        return process_vector_file(input_path, output_dir, selected_api_key, ghostscript_path, stop_event, auto_kategori_enabled, selected_model=selected_model, keyword_count=keyword_count, priority=priority)
    elif ext_lower in ['.jpg', '.jpeg']:
        from src.processing.image_processing.format_jpg_jpeg_processing import process_jpg_jpeg
        return process_jpg_jpeg(input_path, output_dir, selected_api_key, stop_event, auto_kategori_enabled, selected_model=selected_model, keyword_count=keyword_count, priority=priority)
    else:
        log_message(f"  Format file tidak didukung: {ext_lower}")
        return "failed_format", None, None

def process_single_file(input_path, output_dir, api_keys_list, ghostscript_path, rename_enabled, auto_kategori_enabled, auto_foldering_enabled, selected_model=None, keyword_count="49", priority="Kualitas", stop_event=None):
    """
    Memproses satu file, menentukan tipe dan memanggil fungsi pemrosesan yang sesuai.
    
    Args:
        input_path: Path file sumber
        output_dir: Direktori output utama
        api_keys_list: List API key Gemini
        ghostscript_path: Full path to the Ghostscript executable
        rename_enabled: Flag untuk mengaktifkan rename otomatis
        auto_kategori_enabled: Flag untuk mengaktifkan penentuan kategori otomatis
        auto_foldering_enabled: Flag untuk menempatkan file dalam subfolder berdasarkan tipe
        selected_model: Selected model for processing
        keyword_count: Number of keywords to use for processing
        priority: Priority for processing
        stop_event: Event threading untuk menghentikan proses (passed from parent)
    Returns:
        Dictionary dengan informasi hasil pemrosesan
    """
    # Use the provided stop_event or create a new one if not provided
    if stop_event is None:
        import threading
        stop_event = threading.Event()
        
    original_filename = os.path.basename(input_path)
    final_output_path = None
    processed_metadata = None
    status = "failed"
    new_filename = None
    
    if is_stop_requested() or stop_event.is_set():
        return {"status": "stopped", "input": input_path}
    
    original_file_size = None
    original_file_mtime = None
    
    try:
        if stop_event.is_set() or is_stop_requested():
            return {"status": "stopped", "input": input_path}
        
        _, ext = os.path.splitext(input_path)
        ext_lower = ext.lower()
        is_video = ext_lower in SUPPORTED_VIDEO_EXTENSIONS
        is_vector = ext_lower in ('.eps', '.ai', '.svg')
        is_image = not is_video and not is_vector
        
        # Tentukan target output berdasarkan auto_foldering
        target_output_dir = output_dir
        if auto_foldering_enabled:
            if is_video:
                target_output_dir = os.path.join(output_dir, "Videos")
            elif is_vector:
                target_output_dir = os.path.join(output_dir, "Vectors")
            else:
                target_output_dir = os.path.join(output_dir, "Images")
            
            if not os.path.exists(target_output_dir):
                try:
                    os.makedirs(target_output_dir, exist_ok=True)
                except Exception as e:
                    log_message(f"Error membuat subfolder '{os.path.basename(target_output_dir)}': {e}", "error")
                    target_output_dir = output_dir
        
        try:
            if os.path.exists(input_path):
                original_file_size = os.path.getsize(input_path)
                original_file_mtime = os.path.getmtime(input_path)
            else:
                log_message(f"⨯ File input {original_filename} hilang sebelum diproses.", "error")
                return {"status": "failed_input_missing", "input": input_path}
        except Exception as e_info:
            log_message(f"Warning: Gagal mendapatkan info awal {original_filename}: {e_info}", "warning")
        
        if not api_keys_list:
            log_message(f"⨯ Tidak ada API Key tersedia dalam daftar untuk {original_filename}", "error")
            return {"status": "failed_api_list_empty", "input": input_path}
        
        selected_api_key = select_smart_api_key(api_keys_list)
        
        if not selected_api_key:
            log_message(f"⨯ Gagal memilih API Key cerdas untuk {original_filename} (daftar mungkin kosong atau error internal).", "error")
            return {"status": "failed_api_selection", "input": input_path}
        
        if stop_event.is_set() or is_stop_requested():
            return {"status": "stopped", "input": input_path}
        
        # Proses file berdasarkan jenisnya
        if is_video:
            status, processed_metadata, initial_output_path = process_video(
                input_path, target_output_dir, selected_api_key, stop_event, auto_kategori_enabled, selected_model, keyword_count, priority
            )
        elif ext_lower in ['.eps', '.ai', '.svg']:
            status, processed_metadata, initial_output_path = process_vector_file(
                input_path, target_output_dir, selected_api_key, ghostscript_path, stop_event, auto_kategori_enabled, selected_model, keyword_count, priority
            )
        elif ext_lower in ['.jpg', '.jpeg']:
            status, processed_metadata, initial_output_path = process_jpg_jpeg(
                input_path, target_output_dir, selected_api_key, stop_event, auto_kategori_enabled, selected_model, keyword_count, priority
            )
        elif ext_lower == '.png':
            status, processed_metadata, initial_output_path = process_png(
                input_path, target_output_dir, selected_api_key, stop_event, auto_kategori_enabled, selected_model, keyword_count, priority
            )
        else:
            log_message(f"  Format file tidak didukung untuk API: {ext_lower}")
            status, processed_metadata, initial_output_path = "failed_format", None, None
        
        if stop_event.is_set() or is_stop_requested():
            return {"status": "stopped", "input": input_path}
        
        # Check if processing was generally successful (metadata obtained, file copied/renamed)
        # even if EXIF writing specifically failed.
        processed_statuses = ["processed_exif", "processed_no_exif", 
                              "processed_exif_failed", "processed_unknown_exif_status"]
        if status in processed_statuses:
            final_output_path = initial_output_path
            
            # Rename file jika diperlukan
            if rename_enabled and processed_metadata and processed_metadata.get("title"):
                current_output_path = final_output_path
                rename_success = True
                _, file_ext = os.path.splitext(original_filename)
                title_for_rename = processed_metadata.get("title", "").strip()
                
                if title_for_rename:
                    sanitized_title = sanitize_filename(title_for_rename)
                    if not sanitized_title:
                        sanitized_title = f"untitled_{os.path.splitext(original_filename)[0]}"
                    
                    new_base_filename = f"{sanitized_title}{file_ext}"
                    new_path = os.path.join(target_output_dir, new_base_filename)
                    
                    if new_path.lower() != initial_output_path.lower():
                        counter = 0
                        max_rename_attempts = 50
                        
                        while os.path.exists(new_path) and counter < max_rename_attempts:
                            counter += 1
                            new_base_filename = f"{sanitized_title} ({counter}){file_ext}"
                            new_path = os.path.join(target_output_dir, new_base_filename)
                        
                        if counter >= max_rename_attempts:
                            log_message(f"  Error: Gagal menemukan nama unik untuk rename.")
                            rename_success = False
                        else:
                            try:
                                shutil.move(initial_output_path, new_path)
                                # log_message(f"  -> Berhasil di-rename menjadi: {new_base_filename}")
                                final_output_path = new_path
                                new_filename = new_base_filename
                            except Exception as e_rename:
                                log_message(f"  ERROR: Gagal rename: {e_rename}")
                                rename_success = False
                                final_output_path = current_output_path
            
            # Hapus file input jika berhasil diproses
            if status != "failed_copy" and status != "skipped_exists" and os.path.exists(input_path):
                try:
                    os.remove(input_path)
                except OSError as e_remove:
                    log_message(f"  WARNING: Gagal menghapus file asli '{original_filename}': {e_remove}")

            # Tulis metadata ke CSV setelah rename (jika ada) dan proses berhasil
            # Use the same check for processed statuses here
            if status in processed_statuses and processed_metadata and final_output_path:
                try:
                    # Tentukan direktori CSV (gunakan target_output_dir karena file sudah dipindah ke sana)
                    csv_subfolder = os.path.join(target_output_dir, "metadata_csv")
                    if not os.path.exists(csv_subfolder):
                        os.makedirs(csv_subfolder, exist_ok=True)

                    # Dapatkan nama file akhir untuk kolom Filename
                    final_filename_for_csv = os.path.basename(final_output_path)

                    # Tentukan judul untuk kolom Title/Description
                    # Jika di-rename, gunakan nama file baru (tanpa ekstensi) sebagai judul
                    # Jika tidak, gunakan judul dari metadata
                    title_for_csv = processed_metadata.get('title', '')
                    if rename_enabled and new_filename:
                        title_for_csv = os.path.splitext(new_filename)[0]

                    # Determine if the original file was a vector
                    is_vector_file = original_filename.lower().endswith(('.eps', '.ai', '.svg'))
                    
                    # Tulis ke CSV menggunakan nama file akhir dan judul yang sesuai
                    # Pastikan keyword_count dipakai untuk limit
                    try:
                        max_keywords = int(keyword_count)
                        if max_keywords < 1: max_keywords = 49
                    except Exception:
                        max_keywords = 49
                    write_to_platform_csvs(
                        csv_subfolder,
                        final_filename_for_csv,
                        title_for_csv,
                        processed_metadata.get('description', ''), # Deskripsi tetap dari metadata
                        processed_metadata.get('tags', []), # Keywords tetap dari metadata
                        auto_kategori_enabled=auto_kategori_enabled, # Flag kategori
                        is_vector=is_vector_file, # Pass the vector flag
                        max_keywords=max_keywords # Limit keyword
                    )
                except Exception as e_csv:
                    log_message(f"  Warning: Gagal menulis metadata ke CSV untuk {final_filename_for_csv}: {e_csv}")
        
    except Exception as e:
        log_message(f"Error processing {original_filename}: {e}", "error")
        import traceback
        log_message(f"Detail error: {traceback.format_exc()}", "error")
        status = "failed_worker"
    
    if stop_event.is_set() or is_stop_requested():
        return {"status": "stopped", "input": input_path}
    
    return {
        "status": status,
        "input": input_path,
        "output": final_output_path,
        "metadata": processed_metadata,
        "original_filename": original_filename,
        "new_filename": new_filename
    }

def batch_process_files(input_dir, output_dir, api_keys, ghostscript_path, rename_enabled, delay_seconds, num_workers, auto_kategori_enabled, auto_foldering_enabled, progress_callback=None, stop_event=None, selected_model=None, keyword_count="49", priority="Kualitas", bypass_api_key_limit=False):
    """
    Memproses batch file dari direktori input.
    
    Args:
        input_dir: Direktori sumber file
        output_dir: Direktori output untuk file yang diproses
        api_keys: List API key Gemini
        ghostscript_path: Full path to the Ghostscript executable
        rename_enabled: Flag untuk mengaktifkan rename otomatis
        delay_seconds: Delay dalam detik antara batch
        num_workers: Jumlah worker paralel
        auto_kategori_enabled: Flag untuk mengaktifkan penentuan kategori otomatis
        auto_foldering_enabled: Flag untuk menempatkan file dalam subfolder berdasarkan tipe
        progress_callback: Callback untuk melaporkan progres
        stop_event: Event threading untuk menghentikan proses
        selected_model: Selected model for processing
        keyword_count: Number of keywords to use for processing
        priority: Priority for processing
        bypass_api_key_limit: Jika True, tidak membatasi worker ke jumlah API key
        
    Returns:
        Dictionary dengan statistik hasil pemrosesan
    """
    log_message(f"Memulai proses ({num_workers} worker, delay {delay_seconds}s)", "warning")
    
    # Reset flag global
    from src.api.gemini_api import reset_force_stop
    reset_force_stop()
    
    try:
        # Check for stop request immediately at start
        if stop_event and stop_event.is_set() or is_stop_requested():
            log_message("Proses dihentikan sebelum dimulai.", "warning")
            return {
                "processed_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "stopped_count": 0,
                "total_files": 0
            }
            
        # Siapkan folder sementara untuk kompresi
        temp_folders = manage_temp_folders(input_dir, output_dir)
        
        # Cari file yang bisa diproses
        processable_extensions = ALL_SUPPORTED_EXTENSIONS
        
        try:
            dir_list = os.listdir(input_dir)
        except Exception as e:
            log_message(f"Error membaca direktori input: {e}", "error")
            return {
                "processed_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "stopped_count": 0
            }
        
        files_to_process = []
        for filename in dir_list:
            # Check for stop in the file enumeration loop
            if stop_event and stop_event.is_set() or is_stop_requested():
                log_message("Proses dihentikan saat mengenumerasi file.", "warning")
                return {
                    "processed_count": 0,
                    "failed_count": 0,
                    "skipped_count": 0,
                    "stopped_count": 0,
                    "total_files": 0
                }
                
            if filename.lower().endswith(processable_extensions) and not filename.startswith('.'):
                full_path = os.path.join(input_dir, filename)
                if os.path.isfile(full_path):
                    files_to_process.append(full_path)
        
        files_to_process = [f for f in files_to_process if os.path.exists(f)]
        total_files = len(files_to_process)
        
        if total_files == 0:
            log_message("Tidak ada file baru/valid yang dapat diproses di folder input.", "warning")
            return {
                "status": "no_files", # Tambahkan status ini
                "processed_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "stopped_count": 0,
                "total_files": 0 # Sertakan total_files juga
            }
        
        log_message(f"Ditemukan {total_files} file untuk diproses", "success")
        
        if progress_callback:
            progress_callback(0, total_files)
        
        if stop_event and stop_event.is_set() or is_stop_requested():
            log_message("Proses dihentikan sebelum mulai (deteksi awal)", "warning")
            return {
                "processed_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "stopped_count": total_files
            }
        
        processed_count = 0
        failed_count = 0
        skipped_count = 0
        stopped_count = 0
        completed_count = 0
        
        # Siapkan folder CSV di output utama jika auto_foldering dinonaktifkan
        if not auto_foldering_enabled:
            csv_subfolder_main = os.path.join(output_dir, "metadata_csv")
            try:
                if not os.path.exists(csv_subfolder_main):
                    os.makedirs(csv_subfolder_main)
                log_message(f"Output CSV akan disimpan di subfolder: {os.path.basename(csv_subfolder_main)}", "info")
            except Exception as e:
                log_message(f"Warning: Tidak dapat membuat direktori CSV utama: {e}", "warning")
        
        # NEW: Optimize worker count based on available API keys
        # If bypass_api_key_limit is False, limit workers to API key count
        effective_num_workers = num_workers
        if not bypass_api_key_limit and len(api_keys) < num_workers:
            effective_num_workers = len(api_keys)
            log_message(f"Menyesuaikan jumlah worker menjadi {effective_num_workers} agar sesuai dengan jumlah API key yang tersedia.", "warning")
        
        futures = []
        processed_files = set()
        # Track current API key index for assignment
        current_api_key_index = 0
        
        with ThreadPoolExecutor(max_workers=effective_num_workers) as executor:
            log_message(f"Mengirim {total_files} pekerjaan ke {effective_num_workers} worker...", "warning")
            
            batch_index = 0
            while batch_index < len(files_to_process) and not (stop_event and stop_event.is_set() or is_stop_requested()):
                # Minimal delay between batches
                if batch_index > 0 and delay_seconds > 0 and not (stop_event and stop_event.is_set() or is_stop_requested()):
                    # Restore cooldown message
                    cooldown_msg = f"Cool-down {delay_seconds} detik dulu ngabbbb..."
                    log_message(cooldown_msg, "cooldown")
                    
                    # Apply user-defined delay between batches with stop check
                    cooldown_start = time.time()
                    while time.time() - cooldown_start < delay_seconds:
                        if stop_event and stop_event.is_set() or is_stop_requested():
                            log_message("Proses dihentikan selama cooldown.", "warning")
                            break
                        time.sleep(0.1)  # Check for stop every 100ms
                
                # Check for stop again after cooldown
                if stop_event and stop_event.is_set() or is_stop_requested():
                    log_message("Proses dihentikan setelah cooldown.", "warning")
                    break
                
                # Ambil batch file berikutnya
                current_batch_paths = files_to_process[batch_index:batch_index + effective_num_workers]
                current_batch = [f for f in current_batch_paths
                                 if os.path.exists(f) and f not in processed_files]
                
                if not current_batch:
                    batch_index += effective_num_workers
                    continue
                
                batch_futures = []
                for idx, input_path in enumerate(current_batch):
                    if stop_event and stop_event.is_set() or is_stop_requested():
                        break
                    
                    if not os.path.exists(input_path) or input_path in processed_files:
                        continue
                    
                    original_filename = os.path.basename(input_path)
                    log_message(f" → Memproses {original_filename}...", "info") 
                    
                    try:
                        # NEW: Assign a specific API key to each worker instead of passing the full list
                        # This ensures each worker gets a dedicated API key in rotation
                        assigned_api_key = api_keys[current_api_key_index % len(api_keys)]
                        current_api_key_index = (current_api_key_index + 1) % len(api_keys)
                        
                        future = executor.submit(
                            process_single_file,
                            input_path,
                            output_dir,
                            [assigned_api_key],  # Pass a list with just one API key
                            ghostscript_path,
                            rename_enabled,
                            auto_kategori_enabled,
                            auto_foldering_enabled,
                            selected_model,
                            keyword_count,
                            priority,
                            stop_event  # Pass the stop_event to the worker
                        )
                        batch_futures.append(future)
                        futures.append(future)
                        processed_files.add(input_path)
                    except Exception as e:
                        log_message(f"Error submit job untuk {original_filename}: {e}", "error")
                        failed_count += 1
                        completed_count += 1
                
                current_batch_size = len(batch_futures)
                comp_count = completed_count + current_batch_size
                
                if batch_futures:
                    log_message(f"Batch {batch_index//effective_num_workers + 1} ({comp_count}/{total_files}): Menunggu hasil {len(batch_futures)} file...", "warning")
                    
                    for future in concurrent.futures.as_completed(batch_futures):
                        if stop_event and stop_event.is_set() or is_stop_requested():
                            # Cancel all remaining futures when stop is requested
                            for remaining_future in batch_futures:
                                if not remaining_future.done():
                                    remaining_future.cancel()
                            log_message("Proses dihentikan saat menunggu hasil batch.", "warning")
                            break
                        
                        try:
                            result = future.result(timeout=120)
                            completed_count += 1 # Increment total completed count only after successful result retrieval
                            
                            if not result:
                                log_message(f"⨯ Hasil tidak valid diterima", "error")
                                failed_count += 1
                                continue
                            
                            status = result.get("status", "failed")
                            input_path_result = result.get("input", "")
                            filename = os.path.basename(input_path_result) if input_path_result else "unknown file"
                            
                            # Logika penanganan status lainnya (processed, skipped, stopped, other fails)
                            if status == "processed_exif" or status == "processed_no_exif":
                                processed_count += 1
                                new_name = result.get("new_filename")
                                log_msg = f"✓ {filename}" + (f" → {new_name}" if new_name else "")
                                log_message(log_msg)
                            elif status == "processed_exif_failed" or status == "processed_unknown_exif_status": # Handle specific EXIF failure status
                                processed_count += 1 # Count as processed because CSV/move happened
                                new_name = result.get("new_filename")
                                log_msg = f"⚠ {filename}" + (f" → {new_name}" if new_name else "") + " (exif_write_failed, proceeding)"
                                log_message(log_msg, "warning") # Log as warning
                            elif status == "skipped_exists":
                                skipped_count += 1
                                log_message(f"⋯ {filename} (sudah ada)", "info")
                            elif status == "stopped":
                                stopped_count += 1
                                log_message(f"⊘ {filename} (dihentikan internal)", "warning")
                            else: 
                                failed_count += 1
                                if status == "failed_api":
                                     log_message(f"✗ {filename} (API Error/Limit)", "error")
                                elif status == "failed_copy":
                                     log_message(f"✗ {filename} (gagal copy)", "error")
                                elif status == "failed_format":
                                     log_message(f"✗ {filename} (format/file error)", "error")
                                elif status == "failed_empty":
                                    log_message(f"✗ {filename} (file kosong)", "error")
                                elif status == "failed_input_missing":
                                     log_message(f"✗ {filename} (input hilang)", "error")
                                else: 
                                     log_message(f"✗ {filename} ({status})", "error")
                            
                        except concurrent.futures.TimeoutError:
                            completed_count += 1 # Update total count
                            log_message(f"⨯ Timeout menunggu hasil pekerjaan untuk {filename if 'filename' in locals() else 'unknown file'}", "error")
                            failed_count += 1
                        except concurrent.futures.CancelledError:
                            log_message(f"Pekerjaan dibatalkan.", "warning")
                            stopped_count += 1
                        except Exception as e:
                            log_message(f"Error saat memproses hasil: {e}", "error")
                            failed_count += 1
                        
                        # Update progres
                        if progress_callback:
                            progress_callback(completed_count, total_files)
                
                if stop_event and stop_event.is_set() or is_stop_requested():
                    log_message("Stop terdeteksi setelah memproses hasil batch.", "warning")
                    break
                
                batch_index += effective_num_workers
            
            # Batalkan pekerjaan yang tersisa jika dihentikan
            if stop_event and stop_event.is_set() or is_stop_requested():
                log_message("Membatalkan pekerjaan yang tersisa...", "warning")
                # Set global force stop to ensure all subprocesses stop
                from src.api.gemini_api import set_force_stop
                set_force_stop()
                
                # Try to cancel all futures that aren't done yet
                remaining_submitted = 0
                for f in futures:
                    if not f.done():
                        f.cancel()
                        remaining_submitted += 1
                        
                # Count all remaining jobs as stopped
                if remaining_submitted > 0:
                    log_message(f"Membatalkan {remaining_submitted} pekerjaan yang sedang berjalan.", "warning")
                    stopped_count += remaining_submitted
                    completed_count += remaining_submitted 
        
        # Bersihkan folder sementara
        try:
            for folder_type, folder_path in temp_folders.items():
                if os.path.exists(folder_path):
                    cleanup_temp_compression_folder(folder_path)
            
            if auto_foldering_enabled:
                possible_subfolders = [
                    os.path.join(output_dir, "Images"),
                    os.path.join(output_dir, "Videos"),
                    os.path.join(output_dir, "Vectors")
                ]
                
                for subfolder in possible_subfolders:
                    if os.path.exists(subfolder) and os.path.isdir(subfolder):
                        temp_subfolder = os.path.join(subfolder, "temp_compressed")
                        if os.path.exists(temp_subfolder):
                            log_message(f"Membersihkan folder kompresi di {os.path.basename(subfolder)}", "info")
                            cleanup_temp_compression_folder(temp_subfolder)
        except Exception as e:
            log_message(f"Error saat membersihkan folder temp akhir: {e}", "warning")
        
        # Statistik akhir
        log_message("", None)
        log_message("============= Ringkasan Proses =============", "bold")
        log_message(f"Total file: {total_files}", None)
        log_message(f"Berhasil diproses: {processed_count}", "success")
        log_message(f"Gagal: {failed_count}", "error")
        log_message(f"Dilewati: {skipped_count}", "info")
        log_message(f"Dihentikan: {stopped_count}", "warning")
        log_message("=========================================", None)
        
        return {
            "processed_count": processed_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "stopped_count": stopped_count,
            "total_files": total_files
        }
    
    except Exception as e:
        log_message(f"Error fatal dalam processing thread: {e}", "error")
        import traceback
        tb_str = traceback.format_exc()
        log_message(f"Traceback:\n{tb_str}", "error")
        
        return {
            "processed_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "stopped_count": 0,
            "error": str(e)
        }

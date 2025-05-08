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

# src/processing/image_processing/format_png_processing.py
import os
import shutil
from src.utils.logging import log_message
from src.api.gemini_api import check_stop_event, is_stop_requested
from src.utils.compression import compress_image, get_temp_compression_folder
from src.api.gemini_api import get_gemini_metadata
from src.metadata.csv_exporter import write_to_platform_csvs

def process_png(input_path, output_dir, selected_api_key: str, stop_event, auto_kategori_enabled=True, selected_model=None, keyword_count="49", priority="Kualitas"):
    """
    Memproses file PNG: mengompres jika perlu, mendapatkan metadata dengan prompt khusus PNG.
    
    Args:
        input_path: Path file sumber
        output_dir: Direktori output
        selected_api_key: API key Gemini yang sudah dipilih secara cerdas
        stop_event: Event threading untuk menghentikan proses
        auto_kategori_enabled: Flag untuk mengaktifkan penentuan kategori otomatis
        selected_model: Model pemrosesan gambar, atau None untuk auto-rotasi
        keyword_count: Jumlah kata kunci untuk diambil dari hasil API
        priority: Prioritas pemrosesan
        
    Returns:
        Tuple (status, metadata, output_path):
            - status: String status pemrosesan
            - metadata: Dictionary metadata hasil API, atau None jika gagal
            - output_path: Path file output, atau None jika gagal
    """
    filename = os.path.basename(input_path)
    initial_output_path = os.path.join(output_dir, filename)
    temp_files_created = []
    
    if check_stop_event(stop_event): 
        return "stopped", None, None
    
    # Periksa apakah file output sudah ada
    if os.path.exists(initial_output_path):
        return "skipped_exists", None, initial_output_path
    
    # Dapatkan folder kompresi sementara
    chosen_temp_folder = get_temp_compression_folder(output_dir)
    if not chosen_temp_folder:
        log_message("  Error: Tidak dapat menemukan folder temporari yang bisa ditulis.")
        return "failed_unknown", None, None
    
    # Kompresi gambar jika perlu
    try:
        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        if file_size_mb > 2:  # 2MB adalah batas ukuran file
            log_message(f"  File PNG {filename} ({file_size_mb:.2f}MB) perlu kompresi.")
            compressed_path, is_compressed = compress_image(
                input_path, chosen_temp_folder, stop_event=stop_event
            )
            
            if is_compressed and compressed_path and os.path.exists(compressed_path):
                log_message(f"  Kompresi berhasil: {os.path.basename(compressed_path)}")
                path_for_api = compressed_path
                temp_files_created.append(compressed_path)
            else:
                log_message(f"  Kompresi gagal. Menggunakan file asli: {filename}")
                path_for_api = input_path
        else:
            log_message(f"  File {filename} ({file_size_mb:.2f}MB) tidak perlu kompresi.")
            path_for_api = input_path
    except Exception as e:
        log_message(f"  Error saat memeriksa ukuran/kompresi: {e}")
        path_for_api = input_path
    
    if check_stop_event(stop_event):
        # Bersihkan file sementara jika dibatalkan
        for temp_file in temp_files_created:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
        return "stopped", None, None
    
    # Dapatkan metadata dari API Gemini, gunakan prompt khusus PNG
    api_key_to_use = selected_api_key
    metadata_result = get_gemini_metadata(path_for_api, api_key_to_use, stop_event, use_png_prompt=True, selected_model_input=selected_model, keyword_count=keyword_count, priority=priority)
    
    # Bersihkan file kompresi sementara
    for temp_file in temp_files_created:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                log_message(f"  File kompresi sementara dihapus: {os.path.basename(temp_file)}")
        except Exception as e:
            log_message(f"  Warning: Gagal hapus file sementara: {e}")
    
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
    
    # Salin file ke output (PNG tidak bisa menyimpan EXIF metadata)
    try:
        if not os.path.exists(initial_output_path):
            shutil.copy2(input_path, initial_output_path)
        else:
            log_message(f"  Menimpa file output yang sudah ada: {filename}")
            shutil.copy2(input_path, initial_output_path)
    except Exception as e:
        log_message(f"  Gagal menyalin {filename}: {e}")
        return "failed_copy", metadata, None
    
    if check_stop_event(stop_event):
        try: os.remove(initial_output_path)
        except Exception: pass
        return "stopped", metadata, None
    
    return "processed_no_exif", metadata, initial_output_path
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

# src/processing/video_processing.py
import os
import time
import shutil
import cv2
from src.utils.logging import log_message
from src.api.gemini_api import check_stop_event, get_gemini_metadata
from src.utils.compression import compress_image, get_temp_compression_folder
from src.metadata.exif_writer import write_exif_to_video # Corrected import
from src.metadata.csv_exporter import write_to_platform_csvs
from src.utils.file_utils import WRITABLE_METADATA_VIDEO_EXTENSIONS # Import the constant

def extract_frames_from_video(video_path, output_folder, num_frames=3, stop_event=None):
    """
    Mengekstrak beberapa frame dari file video.

    Args:
        video_path: Path file video sumber
        output_folder: Folder tempat menyimpan frame yang diekstrak
        num_frames: Jumlah frame yang diekstrak
        stop_event: Event threading untuk menghentikan proses

    Returns:
        List path frame yang diekstrak, atau None jika gagal
    """
    filename = os.path.basename(video_path)
    log_message(f"  Mengekstrak {num_frames} frame dari video: {filename}")

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            log_message(f"  Error: Tidak dapat membuka video: {filename}")
            return None

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        log_message(f"  Video: {width}x{height}, {fps:.2f} fps, {duration:.2f} detik, {total_frames} frame")

        if total_frames <= 0:
            log_message(f"  Error: Video tidak memiliki frame: {filename}")
            cap.release()
            return None

        num_frames = min(num_frames, total_frames)

        # Tentukan posisi frame yang akan diekstrak
        frame_positions = []
        if num_frames == 1:
            frame_positions = [total_frames // 2]
        elif num_frames == 2:
            frame_positions = [int(total_frames * 0.25), int(total_frames * 0.75)]
        elif num_frames == 3:
            frame_positions = [int(total_frames * 0.2), int(total_frames * 0.5), int(total_frames * 0.8)]
        elif num_frames == 4:
            frame_positions = [int(total_frames * 0.2), int(total_frames * 0.4), int(total_frames * 0.6), int(total_frames * 0.8)]
        else:
            # Distribute frames evenly including start and end if num_frames > 1
            if num_frames > 1:
                 for i in range(num_frames):
                     pos = int(total_frames * (i / (num_frames - 1)))
                     frame_positions.append(min(pos, total_frames - 1))
            else: # Single frame case
                 frame_positions = [total_frames // 2]


        frame_positions = sorted(list(set(frame_positions))) # Ensure unique and sorted positions
        log_message(f"  Mengambil frame dari posisi: {frame_positions}")

        extracted_frames = []
        for i, pos in enumerate(frame_positions):
            if check_stop_event(stop_event, f"  Ekstraksi frame dibatalkan: {filename}"):
                for frame_path in extracted_frames:
                    try:
                        if os.path.exists(frame_path):
                            os.remove(frame_path)
                    except Exception:
                        pass
                cap.release()
                return None

            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ret, frame = cap.read()
            if not ret:
                log_message(f"  Warning: Gagal membaca frame {pos} dari {filename}")
                continue

            base_name = os.path.splitext(filename)[0]
            frame_path = os.path.join(output_folder, f"{base_name}_frame{i+1}.jpg")
            success = cv2.imwrite(frame_path, frame)

            if success and os.path.exists(frame_path):
                extracted_frames.append(frame_path)
                log_message(f"  Frame {i+1}/{len(frame_positions)} diekstrak: {os.path.basename(frame_path)}")
            else:
                log_message(f"  Error: Gagal menyimpan frame {i+1} dari {filename}")

        cap.release()

        if not extracted_frames:
            log_message(f"  Error: Tidak ada frame yang berhasil diekstrak dari {filename}")
            return None

        log_message(f"  Berhasil mengekstrak {len(extracted_frames)} frame dari {filename}")
        return extracted_frames
    except Exception as e:
        log_message(f"  Error saat mengekstrak frame dari {filename}: {e}")
        import traceback
        log_message(f"  Detail error: {traceback.format_exc()}")
        return None

def process_video(input_path, output_dir, api_keys, stop_event, auto_kategori_enabled=True, selected_model=None, keyword_count="49", priority="Kualitas"):
    """
    Memproses file video: mengekstrak frame, mendapatkan metadata, dan menulis metadata ke video.

    Args:
        input_path: Path file sumber
        output_dir: Direktori output
        api_keys: List API key Gemini
        stop_event: Event threading untuk menghentikan proses
        auto_kategori_enabled: Flag untuk mengaktifkan penentuan kategori otomatis
        selected_model: Model yang dipilih untuk diproses, atau None untuk auto-rotasi
        keyword_count: Jumlah kata kunci yang diambil dari hasil API
        priority: Prioritas pemrosesan

    Returns:
        Tuple (status, metadata, output_path):
            - status: String status pemrosesan
            - metadata: Dictionary metadata hasil API, atau None jika gagal
            - output_path: Path file output, atau None jika gagal
    """
    filename = os.path.basename(input_path)
    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    initial_output_path = os.path.join(output_dir, filename)
    extracted_frames = []
    compressed_frames_to_clean = [] # Keep track of compressed frames specifically

    if check_stop_event(stop_event):
        return "stopped", None, None

    # Periksa apakah file output sudah ada
    if os.path.exists(initial_output_path):
        return "skipped_exists", None, initial_output_path

    # Pilih API key secara acak jika ada beberapa
    import random
    api_key = random.choice(api_keys) if isinstance(api_keys, list) else api_keys

    # Dapatkan folder kompresi sementara untuk frame yang diekstrak
    chosen_temp_folder = get_temp_compression_folder(output_dir)
    if not chosen_temp_folder:
        log_message("  Error: Tidak dapat menemukan folder temporari yang bisa ditulis.")
        return "failed_unknown", None, None

    # Ekstrak frame dari video
    try:
        extracted_frames = extract_frames_from_video(input_path, chosen_temp_folder, num_frames=3, stop_event=stop_event)
        if not extracted_frames:
            log_message(f"  Gagal mengekstrak frame dari video: {filename}")
            return "failed_frames", None, None
    except Exception as e:
        log_message(f"  Error saat ekstraksi frame: {e}")
        return "failed_frames", None, None

    if check_stop_event(stop_event):
        # Clean up extracted frames if stopped
        for frame in extracted_frames:
            try:
                if os.path.exists(frame): os.remove(frame)
            except Exception: pass
        return "stopped", None, None

    # Kompres frame jika perlu
    frames_for_api = []
    for frame_path in extracted_frames:
        if not os.path.exists(frame_path): continue # Skip if frame doesn't exist

        frame_filename = os.path.basename(frame_path)
        try:
            frame_size_mb = os.path.getsize(frame_path) / (1024 * 1024)
            if frame_size_mb > 2:  # 2MB adalah batas ukuran file
                log_message(f"  Frame {frame_filename} ({frame_size_mb:.2f}MB) perlu kompresi.")
                compressed_path, is_compressed = compress_image(
                    frame_path, chosen_temp_folder, stop_event=stop_event
                )

                if is_compressed and compressed_path and os.path.exists(compressed_path):
                    log_message(f"  Kompresi frame berhasil: {os.path.basename(compressed_path)}")
                    frames_for_api.append(compressed_path)
                    compressed_frames_to_clean.append(compressed_path) # Add to cleanup list
                    # Clean original large frame immediately after successful compression
                    try: os.remove(frame_path)
                    except Exception: pass
                else:
                    log_message(f"  Kompresi frame gagal. Menggunakan frame asli: {frame_filename}")
                    frames_for_api.append(frame_path) # Use original if compression failed
            else:
                log_message(f"  Frame {frame_filename} ({frame_size_mb:.2f}MB) tidak perlu kompresi.")
                frames_for_api.append(frame_path) # Use original if no compression needed
        except Exception as e_comp:
             log_message(f"  Error saat kompresi frame {frame_filename}: {e_comp}")
             frames_for_api.append(frame_path) # Use original on error

        if check_stop_event(stop_event): break # Check stop event within loop

    if check_stop_event(stop_event):
        # Clean up all frames (original and compressed) if stopped
        for frame in extracted_frames + compressed_frames_to_clean:
            try:
                if os.path.exists(frame): os.remove(frame)
            except Exception: pass
        return "stopped", None, None

    # Pilih frame terbaik untuk dikirim ke API
    best_frame = None
    if frames_for_api:
        # Prioritize middle frame if available
        middle_index = len(frames_for_api) // 2
        if middle_index < len(frames_for_api):
             best_frame = frames_for_api[middle_index]
        else: # Fallback to first frame if middle index is out of bounds (e.g., only 1 frame)
             best_frame = frames_for_api[0]
        log_message(f"  Menggunakan {os.path.basename(best_frame)} sebagai frame utama untuk API")

    if not best_frame or not os.path.exists(best_frame):
        log_message(f"  Error: Tidak ada frame yang tersedia untuk diproses API: {filename}")
        # Clean up remaining frames
        for frame in extracted_frames + compressed_frames_to_clean:
             try:
                 if os.path.exists(frame): os.remove(frame)
             except Exception: pass
        return "failed_frames", None, None

    # Dapatkan metadata dari API Gemini, gunakan prompt khusus video
    metadata_result = get_gemini_metadata(best_frame, api_key, stop_event, use_video_prompt=True, selected_model=selected_model, keyword_count=keyword_count, priority=priority)

    # Bersihkan SEMUA frame (original yang tidak terkompres + hasil kompresi) setelah API call
    # extracted_frames might contain originals if compression failed or wasn't needed
    # compressed_frames_to_clean contains only successfully compressed files
    all_frames_to_clean = list(set(extracted_frames + compressed_frames_to_clean))
    for frame in all_frames_to_clean:
        try:
            if os.path.exists(frame):
                os.remove(frame)
                # log_message(f"  File frame sementara dihapus: {os.path.basename(frame)}") # Optional: reduce log verbosity
        except Exception as e_clean:
            log_message(f"  Warning: Gagal hapus file frame sementara {os.path.basename(frame)}: {e_clean}")

    # Handle API result
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

    # Salin file video ke output
    try:
        if not os.path.exists(initial_output_path):
            shutil.copy2(input_path, initial_output_path)
        else:
            log_message(f"  Menimpa file output yang sudah ada: {filename}")
            shutil.copy2(input_path, initial_output_path)
        output_path = initial_output_path # Define output_path after successful copy
    except Exception as e:
        log_message(f"  Gagal menyalin {filename}: {e}")
        return "failed_copy", metadata, None

    if check_stop_event(stop_event):
        try:
            if os.path.exists(output_path): os.remove(output_path)
        except Exception: pass
        return "stopped", metadata, None

    # Tulis metadata ke video jika format yang didukung
    final_status = "processed_no_exif" # Default status if not writable or fails
    if ext_lower in WRITABLE_METADATA_VIDEO_EXTENSIONS:
        try:
            proceed, exif_status = write_exif_to_video(input_path, output_path, metadata, stop_event)

            if not proceed:
                 # Handle critical failures during EXIF write attempt
                 log_message(f"  Proses dihentikan atau gagal kritis saat mencoba menulis metadata video untuk {filename} (Status: {exif_status})")
                 # Don't delete the video file here, as the copy succeeded
                 return f"failed_{exif_status}", metadata, output_path # Return failure status

            # If proceed is True, check the specific EXIF status
            if exif_status == "exif_ok":
                log_message(f"  Metadata berhasil ditulis ke video: {filename}")
                final_status = "processed_exif"
            elif exif_status == "exif_failed":
                log_message(f"  Warning: Gagal menulis metadata ke video {filename}, tapi proses dilanjutkan.", "warning")
                final_status = "processed_exif_failed" # Indicate EXIF failed but proceed
            elif exif_status == "no_metadata":
                 # This case was handled earlier, but double-check
                 log_message(f"  Info: Tidak ada metadata untuk ditulis ke video {filename}.")
                 final_status = "processed_no_exif"
            elif exif_status == "exiftool_not_found":
                 log_message(f"  Error: Exiftool tidak ditemukan saat mencoba menulis metadata video untuk {filename}.", "error")
                 final_status = "processed_exif_failed" # Treat as EXIF failure
            else:
                 log_message(f"  Status EXIF video tidak dikenal '{exif_status}' untuk {filename}", "warning")
                 final_status = "processed_unknown_exif_status"

        except Exception as e_write:
            log_message(f"  Error saat memanggil write_exif_to_video: {e_write}")
            final_status = "processed_exif_failed" # Treat unexpected error as EXIF failure
    else:
        log_message(f"  Format {ext_lower} tidak optimal untuk metadata, metadata tidak ditulis ke file.")
        final_status = "processed_no_exif"

    # Return the final status and path
    return final_status, metadata, output_path

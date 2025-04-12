# src/processing/video_processing.py
import os
import time
import shutil
import cv2
from src.utils.logging import log_message
from src.api.gemini_api import check_stop_event, get_gemini_metadata
from src.utils.compression import compress_image, get_temp_compression_folder
from src.metadata.exif_writer import write_exif_to_video
from src.metadata.csv_exporter import write_to_platform_csvs

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
            for i in range(num_frames):
                pos = int(total_frames * (i / (num_frames - 1))) if num_frames > 1 else total_frames // 2
                frame_positions.append(min(pos, total_frames - 1))
        
        frame_positions = sorted(frame_positions)
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
                log_message(f"  Frame {i+1}/{num_frames} diekstrak: {os.path.basename(frame_path)}")
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

def process_video(input_path, output_dir, api_keys, stop_event, auto_kategori_enabled=True):
    """
    Memproses file video: mengekstrak frame, mendapatkan metadata, dan menulis metadata ke video.
    
    Args:
        input_path: Path file sumber
        output_dir: Direktori output
        api_keys: List API key Gemini
        stop_event: Event threading untuk menghentikan proses
        auto_kategori_enabled: Flag untuk mengaktifkan penentuan kategori otomatis
        
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
        for frame in extracted_frames:
            try:
                if os.path.exists(frame):
                    os.remove(frame)
            except Exception:
                pass
        return "stopped", None, None
    
    # Kompres frame jika perlu
    compressed_frames = []
    for frame_path in extracted_frames:
        frame_filename = os.path.basename(frame_path)
        frame_size_mb = os.path.getsize(frame_path) / (1024 * 1024)
        
        if frame_size_mb > 2:  # 2MB adalah batas ukuran file
            log_message(f"  Frame {frame_filename} ({frame_size_mb:.2f}MB) perlu kompresi.")
            compressed_path, is_compressed = compress_image(
                frame_path, chosen_temp_folder, stop_event=stop_event
            )
            
            if is_compressed and compressed_path and os.path.exists(compressed_path):
                log_message(f"  Kompresi frame berhasil: {os.path.basename(compressed_path)}")
                compressed_frames.append(compressed_path)
            else:
                log_message(f"  Kompresi frame gagal. Menggunakan frame asli: {frame_filename}")
                compressed_frames.append(frame_path)
        else:
            log_message(f"  Frame {frame_filename} ({frame_size_mb:.2f}MB) tidak perlu kompresi.")
            compressed_frames.append(frame_path)
    
    if check_stop_event(stop_event):
        return "stopped", None, None
    
    # Pilih frame terbaik untuk dikirim ke API
    best_frame = None
    if compressed_frames:
        if len(compressed_frames) >= 3:
            best_frame = compressed_frames[1]  # Ambil frame tengah
        else:
            best_frame = compressed_frames[0]
        log_message(f"  Menggunakan {os.path.basename(best_frame)} sebagai frame utama untuk API")
    
    if not best_frame or not os.path.exists(best_frame):
        log_message(f"  Error: Tidak ada frame yang tersedia untuk diproses: {filename}")
        return "failed_frames", None, None
    
    # Dapatkan metadata dari API Gemini, gunakan prompt khusus video
    metadata_result = get_gemini_metadata(best_frame, api_key, stop_event, use_video_prompt=True)
    
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
    
    # Salin file ke output
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
        try:
            os.remove(initial_output_path)
        except Exception:
            pass
        return "stopped", metadata, None
    
    # Tulis metadata ke video jika format yang didukung
    from src.utils.file_utils import WRITABLE_METADATA_VIDEO_EXTENSIONS
    if ext_lower in WRITABLE_METADATA_VIDEO_EXTENSIONS:
        try:
            exif_success = write_exif_to_video(input_path, initial_output_path, metadata, stop_event)
            if exif_success:
                log_message(f"  Metadata berhasil ditulis ke video: {filename}")
                status = "processed_exif"
            else:
                log_message(f"  Warning: Gagal menulis metadata ke video: {filename}")
                status = "processed_no_exif"
        except Exception as e:
            log_message(f"  Error saat menulis metadata ke video: {e}")
            status = "processed_no_exif"
    else:
        log_message(f"  Format {ext_lower} tidak optimal untuk metadata, melakukan copy tanpa metadata")
        status = "processed_no_exif"
    
    # Tulis metadata ke CSV
    try:
        csv_subfolder = os.path.join(output_dir, "metadata_csv")
        write_to_platform_csvs(
            csv_subfolder,
            os.path.basename(initial_output_path),
            metadata.get('title', ''),
            metadata.get('description', ''),
            metadata.get('tags', []),
            auto_kategori_enabled
        )
    except Exception as e:
        log_message(f"  Warning: Gagal menulis metadata ke CSV: {e}")
    
    # Bersihkan frame yang diekstrak
    for frame in extracted_frames + compressed_frames:
        try:
            if os.path.exists(frame):
                os.remove(frame)
        except Exception:
            pass
    
    return status, metadata, initial_output_path
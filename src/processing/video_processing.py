# RJ Auto Metadata
# Copyright (C) 2026 Riiicil
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

from src.api import provider_manager
from src.metadata.csv_exporter import write_to_platform_csvs
from src.metadata.exif_writer import write_exif_to_video  # Corrected import
from src.utils.compression import compress_image, get_temp_compression_folder
from src.utils.file_utils import WRITABLE_METADATA_VIDEO_EXTENSIONS  # Import the constant
from src.utils.logging import log_message

def extract_frames_from_video(video_path, output_folder, provider_name, num_frames=3, stop_event=None):
    filename = os.path.basename(video_path)
    log_message(f"Extracting {num_frames} frames from video: {filename}")

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            log_message(f"Error: Failed to open video: {filename}")
            return None

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        log_message(f"Video: {width}x{height}, {fps:.2f} fps, {duration:.2f} seconds, {total_frames} frames")

        if total_frames <= 0:
            log_message(f"Error: Video has no frames: {filename}")
            cap.release()
            return None

        num_frames = min(num_frames, total_frames)

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
            if num_frames > 1:
                 for i in range(num_frames):
                     pos = int(total_frames * (i / (num_frames - 1)))
                     frame_positions.append(min(pos, total_frames - 1))
            else:
                 frame_positions = [total_frames // 2]


        frame_positions = sorted(list(set(frame_positions)))
        log_message(f"Extracting frames from positions: {frame_positions}")

        extracted_frames = []
        for i, pos in enumerate(frame_positions):
            if provider_manager.check_stop_event(provider_name, stop_event, f"Extraction of frame cancelled: {filename}"):
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
                log_message(f"Warning: Failed to read frame {pos} from {filename}")
                continue

            base_name = os.path.splitext(filename)[0]
            frame_path = os.path.join(output_folder, f"{base_name}_frame{i+1}.jpg")
            success = cv2.imwrite(frame_path, frame)

            if success and os.path.exists(frame_path):
                extracted_frames.append(frame_path)
            else:
                log_message(f"Error: Failed to save frame {i+1} from {filename}")

        cap.release()

        if not extracted_frames:
            log_message(f"Error: No frames successfully extracted from {filename}")
            return None

        log_message(f"Successfully extracted {len(extracted_frames)} frames from {filename}")
        return extracted_frames
    except Exception as e:
        log_message(f"Error when extracting frames from {filename}: {e}")
        import traceback
        log_message(f"Detail error: {traceback.format_exc()}")
        return None

def process_video(
    input_path,
    output_dir,
    selected_api_key: str,
    stop_event,
    provider_name: str,
    auto_kategori_enabled=True,
    selected_model=None,
    embedding_enabled=True,
    keyword_count="49",
    priority="Details",
    base_url_override=None,
):
    filename = os.path.basename(input_path)
    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    initial_output_path = os.path.join(output_dir, filename)
    extracted_frames = []
    compressed_frames_to_clean = []

    if provider_manager.check_stop_event(provider_name, stop_event):
        return "stopped", None, None

    if os.path.exists(initial_output_path):
        return "skipped_exists", None, initial_output_path

    chosen_temp_folder = get_temp_compression_folder(output_dir)
    if not chosen_temp_folder:
        log_message("Error: Failed to find writable temporary folder.")
        return "failed_unknown", None, None

    try:
        extracted_frames = extract_frames_from_video(
            input_path,
            chosen_temp_folder,
            provider_name,
            num_frames=3,
            stop_event=stop_event,
        )
        if not extracted_frames:
            log_message(f"Failed to extract frames from video: {filename}")
            return "failed_frames", None, None
    except Exception as e:
        log_message(f"Error when extracting frames: {e}")
        return "failed_frames", None, None

    if provider_manager.check_stop_event(provider_name, stop_event):
        for frame in extracted_frames:
            try:
                if os.path.exists(frame): os.remove(frame)
            except Exception: pass
        return "stopped", None, None

    frames_for_api = []
    for frame_path in extracted_frames:
        if not os.path.exists(frame_path): continue

        frame_filename = os.path.basename(frame_path)
        try:
            compressed_path, is_compressed = compress_image(
                frame_path, chosen_temp_folder, stop_event=stop_event
            )
            if is_compressed and compressed_path and os.path.exists(compressed_path):
                log_message(f"Compression/dimension cap applied to frame: {os.path.basename(compressed_path)}")
                frames_for_api.append(compressed_path)
                compressed_frames_to_clean.append(compressed_path)
                try: os.remove(frame_path)
                except Exception: pass
            else:
                log_message(f"No compression needed for frame: {frame_filename}")
                frames_for_api.append(frame_path)
        except Exception as e_comp:
             log_message(f"Error when compressing frame {frame_filename}: {e_comp}")
             frames_for_api.append(frame_path)

        if provider_manager.check_stop_event(provider_name, stop_event):
            break

    if provider_manager.check_stop_event(provider_name, stop_event):
        for frame in extracted_frames + compressed_frames_to_clean:
            try:
                if os.path.exists(frame): os.remove(frame)
            except Exception: pass
        return "stopped", None, None

    best_frame = None
    if frames_for_api:
        middle_index = len(frames_for_api) // 2
        if middle_index < len(frames_for_api):
             best_frame = frames_for_api[middle_index]
        else:
             best_frame = frames_for_api[0]

    if not frames_for_api or len(frames_for_api) == 0:
        log_message(f"Error: No frames available for API processing: {filename}")
        for frame in extracted_frames + compressed_frames_to_clean:
             try:
                 if os.path.exists(frame): os.remove(frame)
             except Exception: pass
        return "failed_frames", None, None
    metadata_result = provider_manager.get_metadata(
        provider_name,
        frames_for_api,
        selected_api_key,
        stop_event,
        use_video_prompt=True,
        selected_model=selected_model,
        keyword_count=keyword_count,
        priority=priority,
        is_vector_conversion=False,
        base_url_override=base_url_override,
    )

    all_frames_to_clean = list(set(extracted_frames + compressed_frames_to_clean))
    for frame in all_frames_to_clean:
        try:
            if os.path.exists(frame):
                os.remove(frame)
        except Exception as e_clean:
            log_message(f"Warning: Failed to delete temporary frame file {os.path.basename(frame)}: {e_clean}")

    if metadata_result == "stopped":
        return "stopped", None, None
    elif isinstance(metadata_result, dict) and "error" in metadata_result:
        log_message(f"API Error detail: {metadata_result['error']}")
        return "failed_api", None, None
    elif isinstance(metadata_result, dict):
        metadata = metadata_result
        metadata['keyword_count'] = keyword_count
    else:
        log_message(f"API call failed to get metadata (result is invalid).")
        return "failed_api", None, None

    if provider_manager.check_stop_event(provider_name, stop_event):
        return "stopped", metadata, None

    try:
        if not os.path.exists(initial_output_path):
            shutil.copy2(input_path, initial_output_path)
        else:
            log_message(f"Overwriting existing output file: {filename}")
            shutil.copy2(input_path, initial_output_path)
        output_path = initial_output_path
    except Exception as e:
        log_message(f"Failed to copy {filename}: {e}")
        return "failed_copy", metadata, None

    if provider_manager.check_stop_event(provider_name, stop_event):
        try:
            if os.path.exists(output_path): os.remove(output_path)
        except Exception: pass
        return "stopped", metadata, None

    final_status = "processed_no_exif"
    if ext_lower in WRITABLE_METADATA_VIDEO_EXTENSIONS:
        if not embedding_enabled:
            log_message(f"Embedding disabled - skipping EXIF metadata for video: {filename}")
            final_status = "processed_no_exif"
        else:
            try:
                proceed, exif_status = write_exif_to_video(input_path, output_path, metadata, stop_event)

                if not proceed:
                     log_message(f"Process stopped or critical failure when writing metadata video for {filename} (Status: {exif_status})")
                     return f"failed_{exif_status}", metadata, output_path

                if exif_status == "exif_ok":
                    log_message(f"Embedding enabled - EXIF metadata written for video: {filename}")
                    final_status = "processed_exif"
                elif exif_status == "exif_failed":
                    log_message(f"Warning: Failed to write metadata to video {filename}, but process continued.", "warning")
                    final_status = "processed_exif_failed"
                elif exif_status == "exif_timeout":
                    log_message(f"Warning: Exiftool timeout when writing metadata to video {filename}, but process continued.", "warning")
                    final_status = "processed_exif_timeout"
                elif exif_status == "no_metadata":
                     log_message(f"Info: No metadata to write to video {filename}.")
                     final_status = "processed_no_exif"
                elif exif_status == "exiftool_not_found":
                     log_message(f"Error: Exiftool not found when trying to write metadata video for {filename}.", "error")
                     final_status = "processed_exif_failed"
                else:
                     log_message(f"Unknown EXIF video status '{exif_status}' for {filename}", "warning")
                     final_status = "processed_unknown_exif_status"

            except Exception as e_write:
                log_message(f"Error when calling write_exif_to_video: {e_write}")
                final_status = "processed_exif_failed"
    else:
        log_message(f"Format {ext_lower} is not optimal for metadata, metadata not written to file.")
        final_status = "processed_no_exif"

    return final_status, metadata, output_path

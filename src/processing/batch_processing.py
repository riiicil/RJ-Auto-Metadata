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
from src.processing.error_classifier import (
    NON_RETRYABLE_ERROR_CODES,
    classify_metadata_error,
)
from src.api import provider_manager
from src.metadata.csv_exporter import write_to_platform_csvs
from src.metadata.exif_writer import write_exif_with_exiftool

RETRYABLE_STATUSES = {
    "failed_api": {"priority": "HIGH", "max_attempts": 5}, 
    "failed_copy": {"priority": "MEDIUM", "max_attempts": 3}, 
    "failed_conversion": {"priority": "MEDIUM", "max_attempts": 3}, 
    "failed_frames": {"priority": "MEDIUM", "max_attempts": 3}, 
    "failed_worker": {"priority": "MEDIUM", "max_attempts": 2}, 
    "failed_timeout": {"priority": "MEDIUM", "max_attempts": 2},
    "failed_exception": {"priority": "LOW", "max_attempts": 2}, 
    "debug_artificial_failure": {"priority": "HIGH", "max_attempts": 3}, 
}

NON_RETRYABLE_STATUSES = {
    "failed_format", "failed_empty", "failed_input_missing", "failed_config"  
}


def is_retryable(status: str, attempt: int) -> bool:
    if status in NON_RETRYABLE_STATUSES:
        return False
    
    if status in RETRYABLE_STATUSES:
        max_attempts = RETRYABLE_STATUSES[status]["max_attempts"]
        return attempt < max_attempts
    
    return False

def process_vector_file(
    input_path,
    output_dir,
    selected_api_key: str,
    ghostscript_path,
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
    is_eps_original = (ext_lower == '.eps')
    is_ai_original = (ext_lower == '.ai')
    is_svg_original = (ext_lower == '.svg')
    
    initial_output_path = os.path.join(output_dir, filename)
    temp_raster_path = None
    conversion_needed = is_eps_original or is_ai_original or is_svg_original
    
    def _check_stop(message=None):
        return provider_manager.check_stop_event(provider_name, stop_event, message)
    
    if _check_stop(): 
        return "stopped", None, None
    
    if os.path.exists(initial_output_path):
        return "skipped_exists", None, initial_output_path
    
    chosen_temp_folder = os.path.join(output_dir, "temp_compressed")
    os.makedirs(chosen_temp_folder, exist_ok=True)
    
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
        
        if _check_stop():
            return "stopped", None, None
        
        if conversion_func == convert_eps_to_jpg:
            conversion_success, error_msg = conversion_func(
                input_path,
                temp_raster_path,
                ghostscript_path,
                stop_event,
            )
        else:
            conversion_success, error_msg = conversion_func(
                input_path,
                temp_raster_path,
                stop_event,
            )
        
        if not conversion_success:
            log_message(f"Conversion of {ext_lower.upper()} failed: {error_msg}")
            if temp_raster_path and os.path.exists(temp_raster_path):
                try: os.remove(temp_raster_path)
                except Exception: pass
            return "failed_conversion", None, None
        if temp_raster_path and os.path.exists(temp_raster_path):
            try:
                from src.utils.compression import compress_image
                compressed_raster_path, is_compressed = compress_image(
                    temp_raster_path, chosen_temp_folder, stop_event=stop_event
                )
                if is_compressed and compressed_raster_path and os.path.exists(compressed_raster_path):
                    try:
                        os.remove(temp_raster_path)  
                        temp_raster_path = compressed_raster_path
                    except Exception as e:
                        log_message(f"Warning: Failed to replace with compressed version: {e}")
            except Exception as e:
                log_message(f"Warning: Failed to compress converted {ext_lower.upper()}: {e}")
        
    
    api_key_to_use = selected_api_key

    metadata_result = provider_manager.get_metadata(
        provider_name,
        temp_raster_path if temp_raster_path else input_path,
        api_key_to_use,
        stop_event,
        use_png_prompt=True,
        selected_model=selected_model,
        keyword_count=keyword_count,
        priority=priority,
        is_vector_conversion=True,
        base_url_override=base_url_override,
    )
    
    if temp_raster_path and os.path.exists(temp_raster_path):
        try:
            os.remove(temp_raster_path)
            log_message(f"Temporary conversion file deleted: {os.path.basename(temp_raster_path)}")
        except Exception as e:
            log_message(f"Warning: Failed to delete conversion file: {e}")
    
    if metadata_result == "stopped":
        return "stopped", None, None
    elif isinstance(metadata_result, dict) and "error" in metadata_result:
        log_message(f"API Error detail: {metadata_result['error']}")
        return classify_metadata_error(metadata_result["error"]), None, None
    elif isinstance(metadata_result, dict):
        metadata = metadata_result
    else:
        log_message(f"API call failed to get metadata (invalid result).")
        return "failed_api", None, None
    
    if _check_stop():
        return "stopped", metadata, None
    
    try:
        if not os.path.exists(initial_output_path):
            shutil.copy2(input_path, initial_output_path)
        else:
            log_message(f"Overwriting existing output file: {filename}")
            shutil.copy2(input_path, initial_output_path)
        
        if isinstance(metadata, dict):
            metadata['keyword_count'] = keyword_count
            
        if not embedding_enabled:
            log_message(f"Embedding disabled - skipping EXIF metadata for vector file: {filename}")
            return "processed_no_exif", metadata, initial_output_path
            
        proceed, exif_status = write_exif_with_exiftool(input_path, initial_output_path, metadata, stop_event)
        
        if not proceed:
            log_message(f"Process stopped or critical failure when writing EXIF for vector {filename} (Status: {exif_status})")
            return f"failed_{exif_status}", metadata, initial_output_path
            
        if exif_status == "exif_ok":
            log_message(f"Embedding enabled - EXIF metadata written for vector file: {filename}")
            return "processed_exif", metadata, initial_output_path
        elif exif_status == "exif_failed":
            log_message(f"Warning: Failed to write EXIF for vector {filename}, but process continued.", "warning")
            return "processed_exif_failed", metadata, initial_output_path
        elif exif_status == "no_metadata":
            return "processed_no_exif", metadata, initial_output_path
        elif exif_status == "exiftool_not_found":
            log_message(f"Error: Exiftool not found when writing EXIF for vector {filename}.", "error")
            return "processed_exif_failed", metadata, initial_output_path
        else:
            log_message(f"Status EXIF not recognized '{exif_status}' for vector {filename}", "warning")
            return "processed_unknown_exif_status", metadata, initial_output_path
    except Exception as e:
        log_message(f"Failed to copy {filename}: {e}")
        return "failed_copy", metadata, None

def process_image(
    input_path,
    output_dir,
    selected_api_key: str,
    ghostscript_path,
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
    
    try:
        file_size = os.path.getsize(input_path)
        if file_size < 100:
            log_message(f"File too small or empty: {filename} ({file_size} bytes)")
            return "failed_empty", None, None
    except Exception as e:
        log_message(f"Error checking file: {e}")
        return "failed_unknown", None, None
    
    if ext_lower == '.png':
        from src.processing.image_processing.format_png_processing import process_png
        return process_png(
            input_path,
            output_dir,
            selected_api_key,
            stop_event,
            provider_name,
            auto_kategori_enabled,
            selected_model=selected_model,
            embedding_enabled=embedding_enabled,
            keyword_count=keyword_count,
            priority=priority,
            base_url_override=base_url_override,
        )
    elif ext_lower in ['.eps', '.ai', '.svg']:
        return process_vector_file(
            input_path,
            output_dir,
            selected_api_key,
            ghostscript_path,
            stop_event,
            provider_name,
            auto_kategori_enabled,
            selected_model=selected_model,
            embedding_enabled=embedding_enabled,
            keyword_count=keyword_count,
            priority=priority,
            base_url_override=base_url_override,
        )
    elif ext_lower in ['.jpg', '.jpeg']:
        from src.processing.image_processing.format_jpg_jpeg_processing import process_jpg_jpeg
        return process_jpg_jpeg(
            input_path,
            output_dir,
            selected_api_key,
            stop_event,
            provider_name,
            auto_kategori_enabled,
            selected_model=selected_model,
            embedding_enabled=embedding_enabled,
            keyword_count=keyword_count,
            priority=priority,
            base_url_override=base_url_override,
        )
    else:
        log_message(f"Format file tidak didukung: {ext_lower}")
        return "failed_format", None, None

def process_single_file(
    input_path,
    output_dir,
    api_keys_list,
    ghostscript_path,
    rename_enabled,
    auto_kategori_enabled,
    auto_foldering_enabled,
    provider_name,
    selected_model=None,
    embedding_enabled=True,
    keyword_count="49",
    priority="Details",
    stop_event=None,
    prompt_config=None,
    base_url_override=None,
):
    if prompt_config is None:
        prompt_config = {}

    from src.api.prompts import _set_prompt_overrides, _clear_prompt_overrides
    _set_prompt_overrides(prompt_config)

    if stop_event is None:
        import threading
        stop_event = threading.Event()
        
    original_filename = os.path.basename(input_path)
    final_output_path = None
    processed_metadata = None
    status = "failed"
    new_filename = None
    
    def _should_stop(message=None):
        return provider_manager.check_stop_event(provider_name, stop_event, message) or provider_manager.is_stop_requested(provider_name)

    if _should_stop():
        return {"status": "stopped", "input": input_path}
    
    original_file_size = None
    original_file_mtime = None
    
    try:
        if _should_stop():
            return {"status": "stopped", "input": input_path}
        
        _, ext = os.path.splitext(input_path)
        ext_lower = ext.lower()
        is_video = ext_lower in SUPPORTED_VIDEO_EXTENSIONS
        is_vector = ext_lower in ('.eps', '.ai', '.svg')
        is_image = not is_video and not is_vector
        
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
                    log_message(f"Error creating subfolder '{os.path.basename(target_output_dir)}': {e}", "error")
                    target_output_dir = output_dir
        
        try:
            if os.path.exists(input_path):
                original_file_size = os.path.getsize(input_path)
                original_file_mtime = os.path.getmtime(input_path)
            else:
                log_message(f"⨯ File input {original_filename} missing before processing.", "error")
                return {"status": "failed_input_missing", "input": input_path}
        except Exception as e_info:
            log_message(f"Warning: Failed to get initial info for {original_filename}: {e_info}", "warning")
        
        if not api_keys_list:
            log_message(f"⨯ No API Key available in list for {original_filename}", "error")
            return {"status": "failed_api_list_empty", "input": input_path}
        
        selected_api_key = provider_manager.select_api_key(provider_name, api_keys_list)
        
        if not selected_api_key:
            log_message(f"⨯ Failed to select smart API Key for {original_filename} (list might be empty or internal error).", "error")
            return {"status": "failed_api_selection", "input": input_path}
        
        if _should_stop():
            return {"status": "stopped", "input": input_path}
        
        if is_video:
            status, processed_metadata, initial_output_path = process_video(
                input_path,
                target_output_dir,
                selected_api_key,
                stop_event,
                provider_name,
                auto_kategori_enabled,
                selected_model,
                embedding_enabled,
                keyword_count,
                priority,
                base_url_override,
            )
        elif ext_lower in ['.eps', '.ai', '.svg']:
            status, processed_metadata, initial_output_path = process_vector_file(
                input_path,
                target_output_dir,
                selected_api_key,
                ghostscript_path,
                stop_event,
                provider_name,
                auto_kategori_enabled,
                selected_model,
                embedding_enabled,
                keyword_count,
                priority,
                base_url_override,
            )
        elif ext_lower in ['.jpg', '.jpeg']:
            from src.processing.image_processing.format_jpg_jpeg_processing import process_jpg_jpeg
            status, processed_metadata, initial_output_path = process_jpg_jpeg(
                input_path,
                target_output_dir,
                selected_api_key,
                stop_event,
                provider_name,
                auto_kategori_enabled,
                selected_model,
                embedding_enabled,
                keyword_count,
                priority,
                base_url_override,
            )
        elif ext_lower == '.png':
            from src.processing.image_processing.format_png_processing import process_png
            status, processed_metadata, initial_output_path = process_png(
                input_path,
                target_output_dir,
                selected_api_key,
                stop_event,
                provider_name,
                auto_kategori_enabled,
                selected_model,
                embedding_enabled,
                keyword_count,
                priority,
                base_url_override,
            )
        else:
            log_message(f"Unsupported file format for API: {ext_lower}")
            status, processed_metadata, initial_output_path = "failed_format", None, None
        
        if _should_stop():
            return {"status": "stopped", "input": input_path}

        # Inject user keywords into LLM result tags
        inject_keywords = prompt_config.get("inject_keywords", [])
        if inject_keywords and processed_metadata and "tags" in processed_metadata:
            existing_tags = processed_metadata.get("tags", [])
            if isinstance(existing_tags, list):
                merged = list(inject_keywords)
                for tag in existing_tags:
                    if tag.strip().lower() not in [k.lower() for k in merged]:
                        merged.append(tag)
                try:
                    limit = int(keyword_count)
                except (ValueError, TypeError):
                    limit = 49
                processed_metadata["tags"] = merged[:limit]

        processed_statuses = ["processed_exif", "processed_no_exif", 
                              "processed_exif_failed", "processed_unknown_exif_status"]
        if status in processed_statuses:
            final_output_path = initial_output_path
            
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
                            log_message(f"Error: Failed to find unique name for rename.")
                            rename_success = False
                        else:
                            try:
                                shutil.move(initial_output_path, new_path)
                                final_output_path = new_path
                                new_filename = new_base_filename
                            except Exception as e_rename:
                                log_message(f"ERROR: Failed to rename: {e_rename}")
                                rename_success = False
                                final_output_path = current_output_path
            
            if status != "failed_copy" and status != "skipped_exists" and os.path.exists(input_path):
                try:
                    os.remove(input_path)
                except OSError as e_remove:
                    log_message(f"WARNING: Failed to delete original file '{original_filename}': {e_remove}")

            if status in processed_statuses and processed_metadata and final_output_path:
                try:
                    csv_subfolder = os.path.join(target_output_dir, "metadata_csv")
                    if not os.path.exists(csv_subfolder):
                        os.makedirs(csv_subfolder, exist_ok=True)

                    final_filename_for_csv = os.path.basename(final_output_path)

                    title_for_csv = processed_metadata.get('title', '')
                    if rename_enabled and new_filename:
                        title_for_csv = os.path.splitext(new_filename)[0]

                    is_vector_file = original_filename.lower().endswith(('.eps', '.ai', '.svg'))
                    
                    try:
                        max_keywords = int(keyword_count)
                        if max_keywords < 1: max_keywords = 49
                    except Exception:
                        max_keywords = 49
                    write_to_platform_csvs(
                        csv_subfolder,
                        final_filename_for_csv,
                        title_for_csv,
                        processed_metadata.get('description', ''),
                        processed_metadata.get('tags', []),
                        auto_kategori_enabled=auto_kategori_enabled,
                        is_vector=is_vector_file,
                        max_keywords=max_keywords,
                        is_video=is_video
                    )
                except Exception as e_csv:
                    log_message(f"Warning: Failed to write metadata to CSV for {final_filename_for_csv}: {e_csv}")
        
    except Exception as e:
        log_message(f"Error processing {original_filename}: {e}", "error")
        import traceback
        log_message(f"Detail error: {traceback.format_exc()}", "error")
        status = "failed_worker"
    
    if _should_stop():
        return {"status": "stopped", "input": input_path}
    
    return {
        "status": status,
        "input": input_path,
        "output": final_output_path,
        "metadata": processed_metadata,
        "original_filename": original_filename,
        "new_filename": new_filename
    }

def batch_process_files(
    input_dir,
    output_dir,
    api_keys,
    provider_name,
    ghostscript_path,
    rename_enabled,
    delay_seconds,
    num_workers,
    auto_kategori_enabled,
    auto_foldering_enabled,
    progress_callback=None,
    stop_event=None,
    selected_model=None,
    embedding_enabled=True,
    auto_retry_enabled=False,
    keyword_count="49",
    priority="Details",
    bypass_api_key_limit=False,
    prompt_config=None,
    base_url_override=None,
):
    if prompt_config is None:
        prompt_config = {}

    log_message(f"Starting process ({num_workers} worker, delay {delay_seconds}s)", "warning")
    
    provider_manager.reset_force_stop(provider_name)

    def should_stop(message=None):
        if provider_manager.check_stop_event(provider_name, stop_event, message):
            return True
        if provider_manager.is_stop_requested(provider_name):
            if message:
                log_message(message, "warning")
            return True
        return False
    
    try:
        if should_stop():
            log_message("Processing stopped before start.", "warning")
            return {
                "processed_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "stopped_count": 0,
                "total_files": 0
            }
            
        temp_folders = manage_temp_folders(input_dir, output_dir)
        
        processable_extensions = ALL_SUPPORTED_EXTENSIONS
        
        try:
            dir_list = os.listdir(input_dir)
        except Exception as e:
            log_message(f"Error reading input directory: {e}", "error")
            return {
                "processed_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "stopped_count": 0
            }
        
        files_to_process = []
        for filename in dir_list:
            if should_stop():
                log_message("Processing stopped while enumerating files.", "warning")
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
            log_message("No new/valid files to process in input folder.", "warning")
            return {
                "status": "no_files",
                "processed_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "stopped_count": 0,
                "total_files": 0
            }
        
        log_message(f"Found {total_files} files to process", "success")
        
        if progress_callback:
            progress_callback(0, total_files)
        
        if should_stop():
            log_message("Processing stopped before start (initial detection)", "warning")
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
        
        failed_files = []  
        if not auto_foldering_enabled:
            csv_subfolder_main = os.path.join(output_dir, "metadata_csv")
            try:
                if not os.path.exists(csv_subfolder_main):
                    os.makedirs(csv_subfolder_main)
                log_message(f"Output CSV will be saved in subfolder: {os.path.basename(csv_subfolder_main)}", "info")
            except Exception as e:
                log_message(f"Warning: Failed to create main CSV directory: {e}", "warning")
        
        effective_num_workers = num_workers
        
        futures = []
        processed_files = set()
        current_api_key_index = 0
        
        with ThreadPoolExecutor(max_workers=effective_num_workers) as executor:
            log_message(f"Sending {total_files} jobs to {effective_num_workers} workers...", "warning")
            
            batch_index = 0
            while batch_index < len(files_to_process) and not should_stop():
                if batch_index > 0 and delay_seconds > 0 and not should_stop():
                    effective_delay = delay_seconds
                    cooldown_msg = f"Cool-down {effective_delay} seconds before processing..."
                    
                    log_message(cooldown_msg, "cooldown")
                    
                    cooldown_start = time.time()
                    while time.time() - cooldown_start < effective_delay:
                        if should_stop():
                            log_message("Processing stopped during cooldown.", "warning")
                            break
                        time.sleep(0.1)
                
                if should_stop():
                    log_message("Processing stopped after cooldown.", "warning")
                    break
                
                current_batch_paths = files_to_process[batch_index:batch_index + effective_num_workers]
                current_batch = [f for f in current_batch_paths
                                 if os.path.exists(f) and f not in processed_files]
                
                if not current_batch:
                    batch_index += effective_num_workers
                    continue
                
                batch_futures = []
                for idx, input_path in enumerate(current_batch):
                    if should_stop():
                        break
                    
                    if not os.path.exists(input_path) or input_path in processed_files:
                        continue
                    
                    original_filename = os.path.basename(input_path)
                    log_message(f" → Processing {original_filename}...", "info") 
                    
                    try:
                        assigned_api_key = api_keys[current_api_key_index % len(api_keys)]
                        current_api_key_index = (current_api_key_index + 1) % len(api_keys)
                        
                        future = executor.submit(
                            process_single_file,
                            input_path,
                            output_dir,
                            [assigned_api_key],
                            ghostscript_path,
                            rename_enabled,
                            auto_kategori_enabled,
                            auto_foldering_enabled,
                            provider_name,
                            selected_model,
                            embedding_enabled,
                            keyword_count,
                            priority,
                            stop_event,
                            prompt_config,
                            base_url_override,
                        )
                        batch_futures.append(future)
                        futures.append(future)
                        processed_files.add(input_path)
                    except Exception as e:
                        log_message(f"Error submitting job for {original_filename}: {e}", "error")
                        failed_count += 1
                        completed_count += 1
                
                current_batch_size = len(batch_futures)
                comp_count = completed_count + current_batch_size
                
                if batch_futures:
                    log_message(f"Batch {batch_index//effective_num_workers + 1} ({comp_count}/{total_files}): Waiting for {len(batch_futures)} file...", "warning")
                    
                    for future in concurrent.futures.as_completed(batch_futures):
                        if should_stop():
                            for remaining_future in batch_futures:
                                if not remaining_future.done():
                                    remaining_future.cancel()
                            log_message("Processing stopped while waiting for batch results.", "warning")
                            break
                        
                        try:
                            result = future.result(timeout=120)
                            completed_count += 1
                            
                            if not result:
                                log_message(f"⨯ Invalid result received", "error")
                                failed_count += 1
                                continue
                            
                            status = result.get("status", "failed")
                            input_path_result = result.get("input", "")
                            filename = os.path.basename(input_path_result) if input_path_result else "unknown file"
                            
                            if status == "processed_exif" or status == "processed_no_exif":
                                processed_count += 1
                                new_name = result.get("new_filename")
                                log_msg = f"✓ {filename}" + (f" → {new_name}" if new_name else "")
                                log_message(log_msg)
                            elif status == "processed_exif_failed" or status == "processed_unknown_exif_status":
                                processed_count += 1
                                new_name = result.get("new_filename")
                                log_msg = f"⚠ {filename}" + (f" → {new_name}" if new_name else "") + " (EXIF write failed, proceeding)"
                                log_message(log_msg, "warning")
                            elif status == "skipped_exists":
                                skipped_count += 1
                                log_message(f"⋯ {filename} (already exists)", "info")
                            elif status == "stopped":
                                stopped_count += 1
                                log_message(f"⊘ {filename} (stopped internally)", "warning")
                            else: 
                                failed_count += 1
                                failed_files.append((input_path_result, status, 1))
                                if status == "failed_api":
                                     log_message(f"✗ {filename} (API Error/Limit)", "error")
                                elif status == "failed_copy":
                                     log_message(f"✗ {filename} (failed copy)", "error")
                                elif status == "failed_format":
                                     log_message(f"✗ {filename} (format/file error)", "error")
                                elif status == "failed_empty":
                                    log_message(f"✗ {filename} (empty file)", "error")
                                elif status == "failed_input_missing":
                                     log_message(f"✗ {filename} (input missing)", "error")
                                elif status == "failed_config":
                                     log_message(f"✗ {filename} (provider misconfiguration — fix and re-run)", "error")
                                else: 
                                     log_message(f"✗ {filename} ({status})", "error")
                            
                        except concurrent.futures.TimeoutError:
                            completed_count += 1
                            failed_count += 1
                            if 'input_path' in locals():
                                failed_files.append((input_path, "failed_timeout", 1))
                            log_message(f"⨯ Timeout waiting for job results for {filename if 'filename' in locals() else 'unknown file'}", "error")
                        except concurrent.futures.CancelledError:
                            log_message(f"Job cancelled.", "warning")
                            stopped_count += 1
                        except Exception as e:
                            log_message(f"Error processing results: {e}", "error")
                            failed_count += 1
                            if 'input_path' in locals():
                                failed_files.append((input_path, "failed_exception", 1))
                        
                        if progress_callback:
                            progress_callback(completed_count, total_files)
                
                if should_stop():
                    log_message("Stop detected after processing batch results.", "warning")
                    break
                
                batch_index += effective_num_workers
            
            if should_stop():
                log_message("Cancelling remaining tasks...", "warning")
                provider_manager.set_force_stop(provider_name)
                
                remaining_submitted = 0
                for f in futures:
                    if not f.done():
                        f.cancel()
                        remaining_submitted += 1
                        
                if remaining_submitted > 0:
                    log_message(f"Cancelling {remaining_submitted} running tasks.", "warning")
                    stopped_count += remaining_submitted
                    completed_count += remaining_submitted 
        
        retry_attempt = 1

        if auto_retry_enabled and failed_count > 0 and not should_stop():
            log_message("", None)
            log_message("AUTO RETRY ENABLED - Processing failed files...", "info")

            retryable_failed_files = []
            for file_path, status, attempt in failed_files:
                if file_path and os.path.exists(file_path) and is_retryable(status, attempt):
                    retryable_failed_files.append((file_path, status, attempt))
                else:
                    log_message(f"Skipping non-retryable: {os.path.basename(file_path)} ({status})", "info")

            retry_files = [f[0] for f in retryable_failed_files]

            while retry_files and not should_stop():
                log_message("", None)
                log_message(f"RETRY ATTEMPT {retry_attempt}: {len(retry_files)} file(s) remaining", "warning")

                retry_processed = 0
                retry_failed = 0
                retry_stopped = 0
                retry_processed_files = set()
                current_retry_failed_files = []

                with ThreadPoolExecutor(max_workers=effective_num_workers) as retry_executor:
                    log_message(
                        f"Sending {len(retry_files)} retry jobs to {effective_num_workers} workers...",
                        "warning",
                    )

                    retry_batch_index = 0

                    while retry_batch_index < len(retry_files) and not should_stop():
                        if retry_batch_index > 0 and delay_seconds > 0 and not should_stop():
                            effective_delay = delay_seconds
                            cooldown_msg = f"Retry cool-down {effective_delay} seconds before next batch..."

                            log_message(cooldown_msg, "cooldown")

                            cooldown_start = time.time()
                            while time.time() - cooldown_start < effective_delay:
                                if should_stop():
                                    log_message("Retry processing stopped during cooldown.", "warning")
                                    break
                                time.sleep(0.1)

                        if should_stop():
                            log_message("Retry processing stopped after cooldown.", "warning")
                            break

                        current_retry_batch = retry_files[
                            retry_batch_index:retry_batch_index + effective_num_workers
                        ]
                        current_retry_batch = [
                            f
                            for f in current_retry_batch
                            if os.path.exists(f) and f not in retry_processed_files
                        ]

                        if not current_retry_batch:
                            retry_batch_index += effective_num_workers
                            continue

                        batch_retry_futures = []
                        for input_path in current_retry_batch:
                            if should_stop():
                                break

                            if not os.path.exists(input_path) or input_path in retry_processed_files:
                                continue

                            original_filename = os.path.basename(input_path)
                            log_message(f" → Retrying {original_filename}...", "info")

                            try:
                                assigned_api_key = api_keys[current_api_key_index % len(api_keys)]
                                current_api_key_index = (current_api_key_index + 1) % len(api_keys)

                                future = retry_executor.submit(
                                    process_single_file,
                                    input_path,
                                    output_dir,
                                    [assigned_api_key],
                                    ghostscript_path,
                                    rename_enabled,
                                    auto_kategori_enabled,
                                    auto_foldering_enabled,
                                    provider_name,
                                    selected_model,
                                    embedding_enabled,
                                    keyword_count,
                                    priority,
                                    stop_event,
                                    prompt_config,
                                    base_url_override,
                                )
                                batch_retry_futures.append((future, input_path))
                                retry_processed_files.add(input_path)
                            except Exception as e:
                                log_message(f"Error submitting retry job for {original_filename}: {e}", "error")
                                retry_failed += 1
                                current_retry_failed_files.append(input_path)

                        if not batch_retry_futures:
                            retry_batch_index += effective_num_workers
                            continue

                        log_message(
                            f"Retry Batch {retry_batch_index // effective_num_workers + 1}: Waiting for {len(batch_retry_futures)} file...",
                            "warning",
                        )

                        for future, input_path in batch_retry_futures:
                            if should_stop():
                                for remaining_future, _ in batch_retry_futures:
                                    if not remaining_future.done():
                                        remaining_future.cancel()
                                log_message("Retry processing stopped while waiting for batch results.", "warning")
                                break

                            try:
                                result = future.result(timeout=120)
                                filename = os.path.basename(input_path)

                                if not result:
                                    retry_failed += 1
                                    current_retry_failed_files.append(input_path)
                                    log_message(f"⨯ RETRY: Invalid result for {filename}", "error")
                                    continue

                                status = result.get("status", "failed")

                                if status in [
                                    "processed_exif",
                                    "processed_no_exif",
                                    "processed_exif_failed",
                                    "processed_unknown_exif_status",
                                ]:
                                    retry_processed += 1
                                    processed_count += 1
                                    failed_count -= 1
                                    failed_files = [
                                        (fp, st, att)
                                        for fp, st, att in failed_files
                                        if fp != input_path
                                    ]
                                    new_name = result.get("new_filename")
                                    log_msg = f"✓ RETRY SUCCESS: {filename}" + (
                                        f" → {new_name}" if new_name else ""
                                    )
                                    log_message(log_msg)
                                elif status == "stopped":
                                    retry_stopped += 1
                                    log_message(f"⊘ RETRY STOPPED: {filename}")
                                    break
                                else:
                                    retry_failed += 1
                                    updated_failed_files = []
                                    new_attempt = 1
                                    for fp, st, att in failed_files:
                                        if fp == input_path:
                                            new_attempt = att + 1
                                            updated_failed_files.append((fp, status, new_attempt))
                                        else:
                                            updated_failed_files.append((fp, st, att))
                                    failed_files = updated_failed_files

                                    if is_retryable(status, new_attempt):
                                        current_retry_failed_files.append(input_path)

                                    log_message(f"✗ RETRY FAILED: {filename} ({status})")
                            except concurrent.futures.TimeoutError:
                                retry_failed += 1
                                current_retry_failed_files.append(input_path)
                                log_message(
                                    f"⨯ RETRY TIMEOUT: {os.path.basename(input_path)}",
                                    "error",
                                )
                            except concurrent.futures.CancelledError:
                                log_message(
                                    f"Retry job cancelled for {os.path.basename(input_path)}",
                                    "warning",
                                )
                                retry_stopped += 1
                            except Exception as e:
                                retry_failed += 1
                                current_retry_failed_files.append(input_path)
                                log_message(
                                    f"✗ RETRY ERROR: {os.path.basename(input_path)} - {e}"
                                )

                        if should_stop():
                            log_message("Stop detected after processing retry batch results.", "warning")
                            break

                        retry_batch_index += effective_num_workers

                retry_files = []
                for file_path in current_retry_failed_files:
                    if file_path and os.path.exists(file_path):
                        current_attempt = 1
                        current_status = "failed_unknown"
                        for fp, st, att in failed_files:
                            if fp == file_path:
                                current_attempt = att
                                current_status = st
                                break

                        if is_retryable(current_status, current_attempt):
                            retry_files.append(file_path)

                log_message(f"RETRY ATTEMPT {retry_attempt} RESULTS:")
                log_message(f"✓ Success: {retry_processed}")
                log_message(f"✗ Failed: {retry_failed}")
                if retry_stopped > 0:
                    log_message(f"⊘ Stopped: {retry_stopped}")

                retry_attempt += 1

                if retry_processed == 0 and len(retry_files) == 0:
                    log_message(
                        f"No retryable files remaining after attempt {retry_attempt-1}, stopping auto retry",
                        "warning",
                    )
                    break
                elif retry_processed == 0 and retry_failed > 0:
                    log_message(
                        f"No progress made in retry attempt {retry_attempt-1}, but retryable files remain",
                        "warning",
                    )

            if retry_files and not should_stop():
                log_message(
                    f"AUTO RETRY COMPLETED: {len(retry_files)} file(s) still failed after {retry_attempt-1} attempts",
                    "warning",
                )
            elif len(failed_files) == 0:
                log_message("AUTO RETRY SUCCESS: All files processed successfully!", "success")
            elif not retry_files and len(failed_files) > 0:
                log_message(
                    f"AUTO RETRY: No retryable files found ({len(failed_files)} failed files not suitable for retry)",
                    "warning",
                )
        
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
                            log_message(f"Cleaning up compression folder in {os.path.basename(subfolder)}", "info")
                            cleanup_temp_compression_folder(temp_subfolder)
        except Exception as e:
            log_message(f"Error when cleaning up temp folder: {e}", "warning")
        
        log_message("", None)
        log_message("============= Summary Process =============", "bold")
        log_message(f"Total file: {total_files}", None)
        log_message(f"Success: {processed_count}", "success")
        log_message(f"Failed: {failed_count}", "error")
        log_message(f"Skipped: {skipped_count}", "info")
        log_message(f"Stopped: {stopped_count}", "warning")
        log_message("=========================================", None)
        
        return {
            "processed_count": processed_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "stopped_count": stopped_count,
            "total_files": total_files
        }
    
    except Exception as e:
        log_message(f"Fatal error in processing thread: {e}", "error")
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

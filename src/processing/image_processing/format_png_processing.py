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

# src/processing/image_processing/format_png_processing.py
import os
import shutil

from src.api import provider_manager
from src.metadata.csv_exporter import write_to_platform_csvs
from src.utils.compression import compress_image, get_temp_compression_folder
from src.utils.logging import log_message


def process_png(
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
    initial_output_path = os.path.join(output_dir, filename)
    temp_files_created = []
    
    if provider_manager.check_stop_event(provider_name, stop_event): 
        return "stopped", None, None
    
    if os.path.exists(initial_output_path):
        return "skipped_exists", None, initial_output_path
    
    chosen_temp_folder = get_temp_compression_folder(output_dir)
    if not chosen_temp_folder:
        log_message("Error: Cannot find writable temporary folder.")
        return "failed_unknown", None, None
    
    try:
        compressed_path, is_compressed = compress_image(
            input_path, chosen_temp_folder, stop_event=stop_event
        )
        if is_compressed and compressed_path and os.path.exists(compressed_path):
            log_message(f"Compression/dimension cap applied: {os.path.basename(compressed_path)}")
            path_for_api = compressed_path
            temp_files_created.append(compressed_path)
        else:
            log_message(f"No compression needed for {filename}; using original")
            path_for_api = input_path
    except Exception as e:
        log_message(f"Error checking file size/compression: {e}")
        path_for_api = input_path
    
    if provider_manager.check_stop_event(provider_name, stop_event):
        for temp_file in temp_files_created:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
        return "stopped", None, None
    
    api_key_to_use = selected_api_key
    metadata_result = provider_manager.get_metadata(
        provider_name,
        path_for_api,
        api_key_to_use,
        stop_event,
        use_png_prompt=True,
        selected_model=selected_model,
        keyword_count=keyword_count,
        priority=priority,
        is_vector_conversion=False,
        base_url_override=base_url_override,
    )
    
    for temp_file in temp_files_created:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                log_message(f"Temporary compression file removed: {os.path.basename(temp_file)}")
        except Exception as e:
            log_message(f"Warning: Failed to remove temporary compression file: {e}")
    
    if metadata_result == "stopped":
        return "stopped", None, None
    elif isinstance(metadata_result, dict) and "error" in metadata_result:
        log_message(f"API Error detail: {metadata_result['error']}")
        return "failed_api", None, None
    elif isinstance(metadata_result, dict):
        metadata = metadata_result
    else:
        log_message(f"API call failed to get metadata (invalid result).")
        return "failed_api", None, None
    
    if provider_manager.check_stop_event(provider_name, stop_event):
        return "stopped", metadata, None
    
    try:
        if not os.path.exists(initial_output_path):
            shutil.copy2(input_path, initial_output_path)
        else:
            log_message(f"Overwriting existing output file: {filename}")
            shutil.copy2(input_path, initial_output_path)
    except Exception as e:
        log_message(f"Failed to copy {filename}: {e}")
        return "failed_copy", metadata, None
    
    if provider_manager.check_stop_event(provider_name, stop_event):
        try: os.remove(initial_output_path)
        except Exception: pass
        return "stopped", metadata, None
    
    if not embedding_enabled:
        log_message(f"Embedding disabled - PNG format does not support EXIF: {filename}")
    else:
        log_message(f"PNG format does not support EXIF embedding: {filename}")
    
    return "processed_no_exif", metadata, initial_output_path
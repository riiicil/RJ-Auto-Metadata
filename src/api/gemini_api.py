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

# src/api/gemini_api.py
import os
import sys
import random
import requests
import base64
import json
import time
import re
import threading
from collections import defaultdict

from src.utils.logging import log_message
from src.api.gemini_prompts import (
    PROMPT_TEXT, PROMPT_TEXT_PNG, PROMPT_TEXT_VIDEO,
    PROMPT_TEXT_BALANCED, PROMPT_TEXT_PNG_BALANCED, PROMPT_TEXT_VIDEO_BALANCED,
    PROMPT_TEXT_FAST, PROMPT_TEXT_PNG_FAST, PROMPT_TEXT_VIDEO_FAST
)

# Constants
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash"
    # "gemini-1.5-pro",  
    # "gemini-2.5-flash-preview-04-17",
    # "gemini-2.5-pro-preview-03-25"
]
DEFAULT_MODEL = "gemini-1.5-flash"
FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash"
]
MODEL_LAST_USED = defaultdict(float)
MODEL_LOCK = threading.Lock()
API_KEY_LAST_USED = defaultdict(float) 
API_KEY_LOCK = threading.Lock() 
API_KEY_MIN_INTERVAL = 2.0 
API_TIMEOUT = 90
API_MAX_RETRIES = 3
API_RETRY_DELAY = 10

# Global state for stop flags
FORCE_STOP_FLAG = False

def select_smart_api_key(api_keys_list: list) -> str | None:
    if not api_keys_list:
        return None

    with API_KEY_LOCK:
        key_statuses = []
        for key in api_keys_list:
            last_used_time = API_KEY_LAST_USED.get(key, 0)
            key_statuses.append((last_used_time, key))

        key_statuses.sort(key=lambda x: x[0])

        if not key_statuses:
            return None
            
        selected_key = key_statuses[0][1]
        API_KEY_LAST_USED[selected_key] = time.time() 
        return selected_key

def select_best_fallback_model(fallback_models_list: list, excluded_model_name: str | None = None) -> str | None:
    if not fallback_models_list:
        return None

    model_statuses = []
    for model_name in fallback_models_list:
        if model_name == excluded_model_name:
            log_message(f"Model fallback '{model_name}' dilewati karena sama dengan model yang baru gagal.", "info")
            continue
        if model_name not in GEMINI_MODELS:
            log_message(f"Model fallback '{model_name}' tidak ada di daftar GEMINI_MODELS, dilewati.", "warning")
            continue
        last_used_time = MODEL_LAST_USED.get(model_name, 0)
        model_statuses.append((last_used_time, model_name))

    if not model_statuses:
        return None

    model_statuses.sort(key=lambda x: x[0])
        
    return model_statuses[0][1]

def is_stop_requested():
    global FORCE_STOP_FLAG
    return FORCE_STOP_FLAG

def set_force_stop():
    global FORCE_STOP_FLAG
    FORCE_STOP_FLAG = True
    log_message("Force stop flag telah diaktifkan. Semua proses akan segera berhenti.", "warning")

def reset_force_stop():
    global FORCE_STOP_FLAG
    FORCE_STOP_FLAG = False

def check_stop_event(stop_event, message=None):
    if is_stop_requested():
        if message: log_message(message)
        return True
    if stop_event is not None:
        try:
            is_set = stop_event.is_set()
            if is_set and message: log_message(message)
            return is_set
        except Exception as e:
            log_message(f"Error memeriksa stop_event: {e}")
            return False
    return False

def get_api_endpoint(model_name):
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

def select_next_model():
    with MODEL_LOCK:
        sorted_models = sorted(GEMINI_MODELS, key=lambda m: MODEL_LAST_USED.get(m, 0))
        
        selected_model = sorted_models[0]
        
        MODEL_LAST_USED[selected_model] = time.time()
        return selected_model

def wait_for_model_cooldown(model_name, stop_event=None):
    # IMPORTANT: This function is intentionally empty to bypass local rate limiting.
    # The application now relies solely on server-side API rate limits,
    # which are much more permissive than the previous local limits.
    # This helps prevent false rate limit errors reported to users.
    return

def wait_for_api_key_cooldown(api_key, stop_event=None):
    # IMPORTANT: This function is intentionally empty to bypass local rate limiting.
    # The application now relies solely on server-side API rate limits,
    # which are much more permissive than the previous local limits.
    # This helps prevent false rate limit errors reported to users.
    return

def _attempt_gemini_request(
    image_paths,
    current_api_key: str,
    model_to_use: str,
    stop_event,
    use_png_prompt: bool,
    use_video_prompt: bool,
    priority: str,
    image_basename: str
) -> tuple:

    if check_stop_event(stop_event, f"API request dibatalkan sebelum cooldown model: {image_basename}"):
        return -2, None, "stopped", "Process stopped before model cooldown"

    wait_for_model_cooldown(model_to_use, stop_event)

    if check_stop_event(stop_event, f"API request dibatalkan setelah cooldown model: {image_basename}"):
        return -2, None, "stopped", "Process stopped after model cooldown"

    api_endpoint = get_api_endpoint(model_to_use)
    
    if isinstance(image_paths, str):
        image_paths = [image_paths]
        log_message(f"Mengirim {image_basename} ke model {model_to_use} (API Key: ...{current_api_key[-5:]})", "info")
    else:
        log_message(f"Mengirim {len(image_paths)} frame dari {image_basename} ke model {model_to_use} (API Key: ...{current_api_key[-5:]})", "info")

    selected_prompt_text = PROMPT_TEXT
    if priority == "Cepat":
        if use_video_prompt: selected_prompt_text = PROMPT_TEXT_VIDEO_FAST
        elif use_png_prompt: selected_prompt_text = PROMPT_TEXT_PNG_FAST
        else: selected_prompt_text = PROMPT_TEXT_FAST
    elif priority == "Seimbang":
        if use_video_prompt: selected_prompt_text = PROMPT_TEXT_VIDEO_BALANCED
        elif use_png_prompt: selected_prompt_text = PROMPT_TEXT_PNG_BALANCED
        else: selected_prompt_text = PROMPT_TEXT_BALANCED
    else:
        if use_video_prompt: selected_prompt_text = PROMPT_TEXT_VIDEO
        elif use_png_prompt: selected_prompt_text = PROMPT_TEXT_PNG

    parts = [{"text": selected_prompt_text}]
    
    for img_path in image_paths:
        try:
            with open(img_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")
            
            _, ext = os.path.splitext(img_path)
            mime_type = f"image/{ext.lower().replace('.', '')}"
            if mime_type == "image/jpg": mime_type = "image/jpeg"
            if mime_type not in ["image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"]:
                mime_type = "image/jpeg"
                
            parts.append({"inline_data": {"mime_type": mime_type, "data": image_data}})
            
        except Exception as e:
            log_message(f"Error membaca file gambar ({os.path.basename(img_path)}): {e}", "error")
            return -3, None, "file_read", str(e)

    payload = {
        "contents": [{"parts": parts}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500, "topP": 0.8, "topK": 40}
    }

    headers = {"Content-Type": "application/json", "User-Agent": "MetadataProcessor/1.0"}
    api_url = f"{api_endpoint}?key={current_api_key}"

    if check_stop_event(stop_event, f"API request dibatalkan sebelum POST: {image_basename}"):
        return -2, None, "stopped", "Process stopped before API POST"

    session = requests.Session()
    session.mount('https://', requests.adapters.HTTPAdapter(
        max_retries=requests.adapters.Retry(total=1, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504], allowed_methods=["POST"], respect_retry_after_header=True)
    ))
    
    response_event = threading.Event()
    response_container = {'response': None, 'error': None}

    def perform_api_request_in_thread():
        try:
            resp = session.post(api_url, headers=headers, json=payload, timeout=API_TIMEOUT, verify=True)
            response_container['response'] = resp
        except Exception as e_req:
            response_container['error'] = e_req
        finally:
            response_event.set()

    api_thread = threading.Thread(target=perform_api_request_in_thread)
    api_thread.daemon = True
    api_thread.start()

    while not response_event.is_set():
        if check_stop_event(stop_event, f"API request dibatalkan saat menunggu response: {image_basename}"):
            return -2, None, "stopped", "Process stopped while waiting for API response"
        response_event.wait(0.1)
    
    if response_container['error']:
        e = response_container['error']
        err_msg = f"RequestException ({type(e).__name__}): {str(e)}"
        log_message(f"Error request API untuk {image_basename} ke {model_to_use}: {err_msg}", "error")
        error_type = "timeout" if isinstance(e, requests.exceptions.Timeout) else "connection_error" if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.SSLError)) else "request_exception"
        return -4, None, error_type, str(e)

    response = response_container['response']
    if response is None:
        log_message(f"Error: Response dari API adalah None tanpa error di container ({image_basename}, {model_to_use}). Ini tidak seharusnya terjadi.", "error")
        return -1, None, "internal_null_response", "Response object was None without explicit error."
    
    http_status_code = response.status_code
    try:
        response_data = response.json()
    except json.JSONDecodeError:
        log_message(f"Error: Respons API bukan JSON valid (Status: {http_status_code}) dari {model_to_use} untuk {image_basename}. Respons: {response.text[:200]}...", "error")
        return http_status_code, None, "json_decode_error", response.text[:500]

    if http_status_code == 200:
        if "candidates" in response_data and response_data["candidates"]:
            return 200, response_data, None, None 
        elif "promptFeedback" in response_data and response_data.get("promptFeedback", {}).get("blockReason"):
            feedback = response_data["promptFeedback"]
            block_reason = feedback["blockReason"]
            log_message(f"Konten diblokir oleh Gemini ({model_to_use}) untuk {image_basename}. Alasan: {block_reason}", "warning")
            return 200, response_data, "blocked", block_reason
        else:
            log_message(f"Respons sukses (200) dari {model_to_use} untuk {image_basename} tapi tidak ada 'candidates' atau 'blockReason' yang jelas. Data: {str(response_data)[:200]}...", "warning")
            return 200, response_data, "success_no_candidates_or_block", "No candidates or blockReason in 200 response."
    else:
        error_details = response_data.get("error", {})
        api_error_code = error_details.get("code", "UNKNOWN_API_ERR_CODE")
        api_error_message = error_details.get("message", "No specific error message from API.")
        log_message(f"  API Error [{model_to_use}] untuk {image_basename}: HTTP {http_status_code}, Code API: {api_error_code} - {api_error_message}", "error")
        return http_status_code, response_data, "api_error", api_error_message

def _extract_metadata_from_text(generated_text: str, keyword_count: str) -> dict | None:
    title = ""
    description = ""
    tags = []
    as_category = ""
    ss_category = ""
    try:
        title_match = re.search(r"^Title:\s*(.*)", generated_text, re.MULTILINE | re.IGNORECASE)
        if title_match: title = title_match.group(1).strip()
        desc_match = re.search(r"^Description:\s*(.*)", generated_text, re.MULTILINE | re.IGNORECASE)
        if desc_match: description = desc_match.group(1).strip()
        keywords_match = re.search(r"^Keywords:\s*(.*)", generated_text, re.MULTILINE | re.IGNORECASE)
        if keywords_match:
            keywords_line = keywords_match.group(1).strip()
            keywords_line = re.split(r"AdobeStockCategory:|ShutterstockCategory:", keywords_line)[0].strip()
            tags = [k.strip() for k in keywords_line.split(",") if k.strip()]
            tags = list(dict.fromkeys(tags))
            try:
                max_kw = int(keyword_count)
                if max_kw < 1: max_kw = 49
            except Exception:
                max_kw = 49
            tags = tags[:max_kw]
        as_cat_match = re.search(r"AdobeStockCategory:\s*([\d]+\.?\s*[^\n]*)", generated_text)
        if as_cat_match:
            as_category = as_cat_match.group(1).strip()
        ss_cat_match = re.search(r"ShutterstockCategory:\s*([^\n]*)", generated_text)
        if ss_cat_match:
            ss_category = ss_cat_match.group(1).strip()
    except Exception as e:
        log_message(f"[ERROR] Gagal parsing metadata dari Gemini: {e}")
        return None
    return {
        "title": title,
        "description": description,
        "tags": tags,
        "as_category": as_category,
        "ss_category": ss_category
    }

def get_gemini_metadata(image_path, api_key, stop_event, use_png_prompt=False, use_video_prompt=False, selected_model_input=None, keyword_count="49", priority="Kualitas"):
    is_multi_image = isinstance(image_path, list)
    
    if is_multi_image:
        image_basename = f"{os.path.basename(image_path[0])} (+{len(image_path)-1} frame lainnya)"
        log_message(f"Memulai get_gemini_metadata untuk {len(image_path)} frame video dengan prioritas: {priority}, model input: {selected_model_input}")
    else:
        image_basename = os.path.basename(image_path)
        log_message(f"Memulai get_gemini_metadata untuk {image_basename} dengan prioritas: {priority}, model input: {selected_model_input}")
    
    allowed_api_ext = ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif')
    
    if is_multi_image:
        for img in image_path:
            _, ext = os.path.splitext(img)
            if not ext.lower() in allowed_api_ext:
                log_message(f"Tipe file {ext.lower()} tidak didukung untuk API call ({os.path.basename(img)}).", "warning")
                return None
    else:
        _, ext = os.path.splitext(image_path)
        if not ext.lower() in allowed_api_ext:
            log_message(f"Tipe file {ext.lower()} tidak didukung untuk API call ({image_basename}).", "warning")
            return None

    if check_stop_event(stop_event, f"get_gemini_metadata dibatalkan sebelum loop retry: {image_basename}"):
        return "stopped"

    wait_for_api_key_cooldown(api_key, stop_event)
    if check_stop_event(stop_event, f"get_gemini_metadata dibatalkan setelah cooldown API Key: {image_basename}"):
        return "stopped"

    current_retries = 0
    last_attempted_model = None
    
    model_to_use = DEFAULT_MODEL
    is_auto_rotate_mode = (selected_model_input is None or selected_model_input == "Auto Rotasi")

    if not is_auto_rotate_mode:
        if selected_model_input not in GEMINI_MODELS:
            log_message(f"WARNING: Model input '{selected_model_input}' tidak valid. Menggunakan default: {DEFAULT_MODEL}", "warning")
            model_to_use = DEFAULT_MODEL
        else:
            model_to_use = selected_model_input
            log_message(f"Menggunakan model tetap: {model_to_use} (user selected)", "info")
    
    while current_retries < API_MAX_RETRIES:
        if check_stop_event(stop_event, f"get_gemini_metadata loop retry ({current_retries + 1}) dibatalkan: {image_basename}"):
            return "stopped"

        model_for_this_attempt = model_to_use
        if is_auto_rotate_mode:
            model_for_this_attempt = select_next_model() 
            log_message(f"Auto Rotasi: Model dipilih {model_for_this_attempt} untuk upaya {current_retries + 1}", "info")
        
        last_attempted_model = model_for_this_attempt

        log_message(f"Upaya {current_retries + 1}/{API_MAX_RETRIES} menggunakan model: {model_for_this_attempt}", "info")
        
        http_status, response_data, error_type, error_detail = _attempt_gemini_request(
            image_path, api_key, model_for_this_attempt, stop_event,
            use_png_prompt, use_video_prompt, priority, image_basename
        )

    
        if http_status == 200 and error_type is None:
            if response_data and "candidates" in response_data and response_data["candidates"]:
                candidate = response_data["candidates"][0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                if parts and parts[0].get("text"):
                    generated_text = parts[0].get("text", "")
                    extracted_metadata = _extract_metadata_from_text(generated_text, keyword_count)
                    
                    if extracted_metadata:
                        log_message(f"Metadata berhasil diekstrak dari {model_for_this_attempt} untuk {image_basename}", "success")
                        return extracted_metadata
                    else:
                        log_message(f"Gagal mengekstrak struktur metadata (via helper) dari teks Gemini ({model_for_this_attempt}, {image_basename}).", "warning")
                        error_type = "extraction_failed"
                else:
                    log_message(f"Struktur respons Gemini tidak valid (tidak ada 'parts'/'text') dari {model_for_this_attempt} ({image_basename}).", "warning")
                    error_type = "invalid_response_structure"
            else:
                log_message(f"Respons sukses (200) tapi tidak ada 'candidates' dari {model_for_this_attempt} ({image_basename}).", "warning")
                error_type = "success_no_candidates_data"
        
        if error_type == "stopped":
            log_message(f"Pemrosesan dihentikan selama upaya API untuk {image_basename}. Detail: {error_detail}", "warning")
            return "stopped"
        elif error_type == "blocked":
            log_message(f"Konten diblokir untuk {image_basename} oleh {model_for_this_attempt}. Alasan: {error_detail}. Tidak ada retry.", "error")
            return {"error": f"Content blocked by {model_for_this_attempt}: {error_detail}"}
        elif http_status == 429 or (error_type == "api_error" and response_data and response_data.get("error", {}).get("code") == 429):
            log_message(f"Rate limit (429) diterima untuk model {model_for_this_attempt} / API key ...{api_key[-4:]} pada {image_basename}.", "warning")
            if not is_auto_rotate_mode:
                log_message(f"Peringatan: Model yang Anda pilih ({model_for_this_attempt}) sedang mencapai batas kuota. Coba gunakan model lain atau mode Auto Rotasi.", "warning")
        elif http_status in [400, 401, 403] or (error_type == "api_error" and response_data and response_data.get("error",{}).get("code",0) in [400,401,403]):
            err_msg = error_detail if error_detail else "Bad request/Auth error"
            log_message(f"Error klien (HTTP {http_status}) untuk {image_basename} dengan {model_for_this_attempt}: {err_msg}. Tidak ada retry.", "error")
            return {"error": f"{err_msg} (HTTP {http_status}, Model {model_for_this_attempt})"}

        current_retries += 1
        if current_retries < API_MAX_RETRIES:
            base_delay = API_RETRY_DELAY * (2 ** (current_retries -1 if current_retries > 0 else 0))
            jitter = random.uniform(0, 0.5 * base_delay)
            actual_delay = base_delay + jitter
            log_message(f"Menunggu {actual_delay:.1f} detik sebelum retry ({current_retries + 1}/{API_MAX_RETRIES}) untuk {image_basename} (Model terakhir: {model_for_this_attempt}, Error: {error_type or 'N/A'}) ...")
            
            wait_start_time = time.time()
            while time.time() - wait_start_time < actual_delay:
                if check_stop_event(stop_event, f"Retry delay dihentikan untuk {image_basename}"):
                    return "stopped"
                time.sleep(0.1)

    if is_auto_rotate_mode and last_attempted_model and http_status == 429:
        log_message(f"Model terakhir '{last_attempted_model}' gagal karena rate limit setelah semua retry. Tidak mencoba fallback karena Auto Rotasi sudah digunakan.", "warning")
    
    log_message(f"Semua upaya ({current_retries}) gagal untuk {image_basename}. Model terakhir dicoba: {last_attempted_model}", "error")
    return {"error": f"Maximum retries exceeded for {image_basename}. Last model: {last_attempted_model}"}
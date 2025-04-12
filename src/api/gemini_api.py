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

from src.api.rate_limiter import MODEL_RATE_LIMITERS, API_RATE_LIMITERS
from src.utils.logging import log_message

# Constants
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash",
    "gemini-1.5-pro",  
    "gemini-2.0-flash-lite"
]
DEFAULT_MODEL = "gemini-2.0-flash-exp"
MODEL_LAST_USED = defaultdict(float)
MODEL_LOCK = threading.Lock()
API_KEY_LAST_USED = defaultdict(float) 
API_KEY_LOCK = threading.Lock() 
API_KEY_MIN_INTERVAL = 1.0 
API_TIMEOUT = 30
API_MAX_RETRIES = 3
API_RETRY_DELAY = 2

# Prompts
PROMPT_TEXT = '''
Analyze the provided image and generate the following metadata strictly in English:

1.  Title: A unique, detailed and descriptive title for the image (minimum 6 words, maximum 160 characters). 
   - Make each title unique with specific details from the image
   - Focus on distinctive features, unusual aspects, or specific details
   - Include any unique lighting, composition, emotional tone, or context
   - Avoid generic descriptions that could apply to multiple similar images
   - Do not use any special characters or numbers in the title
   - Ensure the title is original and not repetitive
   - The title provides a clear and complete description of the image

2.  Description: A detailed description of the image content.
    - Minimum 6 words, maximum 160 characters
    - Use detailed, descriptive sentences or phrases to detail the Who, What, When, Where, and Why of your content.
    - Create a description that uniquely identifies your content
    - Include helpful details about angle, focus, etc
    - Avoid generic descriptions that could apply to multiple similar images
    - Do not merely list keywords as your description
    - Avoid repeating words or phrases
    - Do not include links, specific camera information, and trademarks (unless it is relevant for Editorial content only).
    - Maximum 160 characters!

3.  Keywords: A list of SINGLE-WORD keywords only, separated ONLY by commas.  
    - Use specific and unique words (or compound words)
    - Stay between 50 and 60 keywords
    - Each keyword must be just ONE word 
    - Keywords should be related to the content of the image
    - DO NOT use multi-word phrases, only individual single words
    - Ensure keywords are relevant to the image content
    - Remember to include broader topics, feelings, concepts, or even associations
    - Do not enter unrelated terms or concepts
    - Do not repeat the same words or compound words
    - Do not include links, specific camera information, and trademarks (except for Editorial content)
    - All keywords are need to be relevant and encompass various aspects of the image and ways to find it
    
    
Ensure all outputs are in English.

Provide the output STRICTLY in the following format, with each item on a new line and no extra text before or after:

Title: [Generated Title Here]
Description: [Generated Description Here]
Keywords: [keyword1, keyword2, keyword3, ..., keywordN]
'''

PROMPT_TEXT_PNG = '''
Analyze the provided image which has a transparent background and generate the following metadata strictly in English, focusing ONLY on the main subject(s):

1.  Title: A unique, detailed and descriptive title for the main subject(s) of the image (minimum 6 words, maximum 160 characters).
   - Describe only the visible subject(s), ignore the transparent background.
   - Make each title unique with specific details from the subject(s).
   - Focus on distinctive features, unusual aspects, or specific details of the subject(s).
   - Include any unique lighting, composition, emotional tone, or context related to the subject(s).
   - Avoid generic descriptions.
   - Do not use any special characters or numbers in the title.
   - Ensure the title is original and not repetitive.
   - The title provides a clear and complete description of the subject(s).

2.  Description: A detailed description of the main subject(s) of the image.
   - Minimum 6 words, maximum 160 characters.
   - Describe only the visible subject(s), ignore the transparent background.
   - Use detailed, descriptive sentences or phrases detailing the Who/What of the subject(s).
   - Create a description that uniquely identifies the subject(s).
   - Include helpful details about the subject's angle, focus, etc.
   - Avoid generic descriptions.
   - Do not merely list keywords as your description.
   - Avoid repeating words or phrases.
   - Do not include links, specific camera information, and trademarks (unless relevant for Editorial content).
   - Maximum 160 characters!

3.  Keywords: A list of SINGLE-WORD keywords only, related ONLY to the main subject(s), separated ONLY by commas.
   - Describe only the visible subject(s), ignore the transparent background.
   - Use specific and unique words (or compound words) describing the subject(s).
   - Stay between 50 and 60 keywords.
   - Each keyword must be just ONE word.
   - Keywords should be related to the subject(s) content.
   - DO NOT use multi-word phrases, only individual single words.
   - Ensure keywords are relevant to the subject(s) content.
   - Remember to include broader topics, feelings, concepts, or associations related to the subject(s).
   - Do not enter unrelated terms or concepts (especially background descriptions like 'isolated', 'white background', etc., unless the subject ITSELF is related to isolation).
   - Do not repeat the same words or compound words.
   - Do not include links, specific camera information, and trademarks (except for Editorial content).
   - All keywords need to be relevant and encompass various aspects of the subject(s) and ways to find it.


Ensure all outputs are in English.

Provide the output STRICTLY in the following format, with each item on a new line and no extra text before or after:

Title: [Generated Title Here]
Description: [Generated Description Here]
Keywords: [keyword1, keyword2, keyword3, ..., keywordN]
'''

PROMPT_TEXT_VIDEO = '''
Analyze the provided image frame from a video and generate the following metadata strictly in English:

1. Title: A unique, detailed and descriptive title for the video (minimum 6 words, maximum 160 characters).
   - Make each title unique with specific details from the visible content
   - Focus on distinctive features, unusual aspects, or specific details 
   - Include any unique visual elements, subjects, scene setting or context
   - Consider this is a video, not just a static image
   - Avoid generic descriptions that could apply to multiple similar videos
   - Do not use any special characters or numbers in the title
   - Ensure the title is original and not repetitive
   - The title should provide a clear and complete description of the video content

2. Description: A detailed description of the video content.
   - Minimum 6 words, maximum 160 characters
   - Describe the main subjects, actions, and setting visible in the video frames
   - Include helpful details about what is happening in the video
   - Consider the dynamic nature of video content (action, movement, etc.)
   - Avoid generic descriptions that could apply to multiple similar videos
   - Do not merely list keywords as your description
   - Avoid repeating words or phrases
   - Do not include links, specific camera information, and trademarks (unless it is relevant for Editorial content only).
   - Maximum 160 characters!

3. Keywords: A list of SINGLE-WORD keywords only, separated ONLY by commas.  
   - Use specific and unique words (or compound words)
   - Include keywords related to both static and dynamic video aspects
   - Stay between 50 and 60 keywords
   - Each keyword must be just ONE word 
   - Keywords should be related to the content of the video
   - DO NOT use multi-word phrases, only individual single words
   - Ensure keywords are relevant to the video content
   - Remember to include broader topics, feelings, concepts, or even associations
   - Include keywords related to video production, motion, action where appropriate
   - Do not enter unrelated terms or concepts
   - Do not repeat the same words or compound words
   - Do not include links, specific camera information, and trademarks (except for Editorial content)
   - All keywords need to be relevant and encompass various aspects of the video and ways to find it
    
Ensure all outputs are in English.

Provide the output STRICTLY in the following format, with each item on a new line and no extra text before or after:

Title: [Generated Title Here]
Description: [Generated Description Here]
Keywords: [keyword1, keyword2, keyword3, ..., keywordN]
'''

# Global state for stop flags
FORCE_STOP_FLAG = False

def is_stop_requested():
    global FORCE_STOP_FLAG
    return FORCE_STOP_FLAG

def set_force_stop():
    global FORCE_STOP_FLAG
    FORCE_STOP_FLAG = True

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
        selected_model = None
        max_tokens = -1
        for model in sorted_models:
            available_tokens = MODEL_RATE_LIMITERS[model].tokens
            if available_tokens > max_tokens:
                max_tokens = available_tokens
                selected_model = model
        if selected_model is None or max_tokens < 1:
            selected_model = sorted_models[0]
        MODEL_LAST_USED[selected_model] = time.time()
        return selected_model

def wait_for_model_cooldown(model_name, stop_event=None):
    wait_time = MODEL_RATE_LIMITERS[model_name].consume()
    if wait_time > 0:
        jitter = random.uniform(0, 0.5)
        total_wait = wait_time + jitter
        log_message(f"  Rate limit: Menunggu {total_wait:.2f}s untuk model {model_name}")
        if stop_event:
            interval = 0.1
            remaining = total_wait
            while remaining > 0 and not check_stop_event(stop_event):
                sleep_time = min(interval, remaining)
                time.sleep(sleep_time)
                remaining -= sleep_time
        else:
            time.sleep(total_wait)
    with MODEL_LOCK:
        MODEL_LAST_USED[model_name] = time.time()

def wait_for_api_key_cooldown(api_key, stop_event=None):
    wait_time = API_RATE_LIMITERS[api_key].consume()
    if wait_time > 0:
        jitter = random.uniform(0, 0.5)
        total_wait = wait_time + jitter
        log_message(f"  Rate limit: Menunggu {total_wait:.2f}s untuk API key")
        if stop_event:
            interval = 0.1
            remaining = total_wait
            while remaining > 0 and not check_stop_event(stop_event):
                sleep_time = min(interval, remaining)
                time.sleep(sleep_time)
                remaining -= sleep_time
        else:
            time.sleep(total_wait)
    with API_KEY_LOCK:
        API_KEY_LAST_USED[api_key] = time.time()

def get_gemini_metadata(image_path, api_key, stop_event, use_png_prompt=False, use_video_prompt=False):
    _, ext = os.path.splitext(image_path)
    allowed_api_ext = ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif')
    if not ext.lower() in allowed_api_ext:
        log_message(f"  Skipping API call for non-raster file type sent to API: {os.path.basename(image_path)}")
        return None
    retries = 0
    image_basename = os.path.basename(image_path)
    if check_stop_event(stop_event, f"  API request dibatalkan: {image_basename}"):
        return "stopped"
    wait_for_api_key_cooldown(api_key, stop_event)
    while retries < API_MAX_RETRIES:
        if check_stop_event(stop_event, f"  API request dibatalkan: {image_basename}"):
            return "stopped"
        if retries > 0:
            base_delay = API_RETRY_DELAY * (2 ** (retries - 1))
            jitter = random.uniform(0, 0.5 * base_delay)
            actual_delay = base_delay + jitter
            log_message(f"  Mencoba ulang API call ({retries+1}/{API_MAX_RETRIES}) untuk {image_basename} dalam {actual_delay:.1f} detik...")
            if stop_event:
                interval = 0.1
                remaining = actual_delay
                while remaining > 0 and not check_stop_event(stop_event):
                    sleep_time = min(interval, remaining)
                    time.sleep(sleep_time)
                    remaining -= sleep_time
                if check_stop_event(stop_event):
                    return "stopped"
            else:
                time.sleep(actual_delay)
        try:
            if check_stop_event(stop_event, f"  API request dibatalkan: {image_basename}"):
                return "stopped"
            selected_model = select_next_model()
            wait_for_model_cooldown(selected_model, stop_event)
            if check_stop_event(stop_event, f"  API request dibatalkan: {image_basename}"):
                return "stopped"
            api_endpoint = get_api_endpoint(selected_model)
            log_message(f"  Mengirim {image_basename} ke Gemini API menggunakan model {selected_model}...")
            try:
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode("utf-8")
            except Exception as e:
                log_message(f"  Error membaca file gambar: {e}")
                return {"error": f"File read error: {str(e)}"}
            mime_type = f"image/{ext.lower().replace('.', '')}"
            if mime_type == "image/jpg": mime_type = "image/jpeg"
            if mime_type not in ["image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"]:
                 mime_type = "image/jpeg"
            if use_video_prompt:
                selected_prompt = PROMPT_TEXT_VIDEO
                log_message(f"  Menggunakan prompt: Video")
            elif use_png_prompt:
                selected_prompt = PROMPT_TEXT_PNG
                log_message(f"  Menggunakan prompt: PNG/EPS Khusus")
            else:
                selected_prompt = PROMPT_TEXT
                log_message(f"  Menggunakan prompt: Standar")
            payload = {
                "contents": [{"parts": [{"text": selected_prompt}, {"inline_data": {"mime_type": mime_type, "data": image_data}}]}],
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 500,
                    "topP": 0.8,
                    "topK": 40
                }
            }
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "MetadataProcessor/1.0"
            }
            api_url = f"{api_endpoint}?key={api_key}"
            if check_stop_event(stop_event, f"  API request dibatalkan: {image_basename}"):
                return "stopped"
            session = requests.Session()
            session.mount('https://', requests.adapters.HTTPAdapter(
                max_retries=requests.adapters.Retry(
                    total=3,
                    backoff_factor=2.0,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["POST"],
                    respect_retry_after_header=True
                )
            ))
            timeout = API_TIMEOUT * 1.1
            response_event = threading.Event()
            response_container = {'response': None, 'error': None}
            def perform_api_request():
                try:
                    resp = session.post(api_url, headers=headers, json=payload, 
                                        timeout=API_TIMEOUT, verify=True)
                    response_container['response'] = resp
                except Exception as e:
                    response_container['error'] = e
                finally:
                    response_event.set()
            api_thread = threading.Thread(target=perform_api_request)
            api_thread.daemon = True
            api_thread.start()
            while not response_event.is_set():
                if check_stop_event(stop_event, f"  API request dibatalkan saat sedang berlangsung: {image_basename}"):
                    return "stopped"
                response_event.wait(0.1)
            if response_container['error']:
                raise response_container['error']
            response = response_container['response']
            if check_stop_event(stop_event, f"  API request dibatalkan: {image_basename}"):
                return "stopped"
            if response_container['error']:
                raise response_container['error']
            response = response_container['response']
            if stop_event.is_set(): 
                log_message(f"  API request dibatalkan: {image_basename}")
                return "stopped"
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                 log_message(f"  Error: Respons API bukan JSON valid (Status: {response.status_code}).")
                 log_message(f"  Respons mentah (awal): {response.text[:200]}...")
                 retries += 1
                 continue
            if response.status_code != 200:
                error_details = response_data.get("error", {})
                error_code = error_details.get("code", "UNKNOWN")
                error_message = error_details.get("message", "No error message")
                log_message(f"  API Error [{selected_model}]: {error_code} - {error_message}")
                if error_code == 429:
                    with MODEL_LOCK:
                        MODEL_RATE_LIMITERS[selected_model].tokens = max(0, MODEL_RATE_LIMITERS[selected_model].tokens - 5)
                    log_message("  Rate limit exceeded. Menunggu lebih lama...")
                    exponential_wait = 10 * (3 ** retries) 
                    jitter = random.uniform(0, exponential_wait * 0.3)  
                    wait_time = exponential_wait + jitter
                    if api_key in API_RATE_LIMITERS:
                        API_RATE_LIMITERS[api_key].tokens = max(0, API_RATE_LIMITERS[api_key].tokens - 5)
                    log_message(f"  !!! RATE LIMIT !!! Menunggu {wait_time:.1f} detik sebelum mencoba dengan model lain...")
                    time.sleep(wait_time)
                    retries += 1
                    continue
                elif error_code in [400, 401, 403]:
                    return {"error": f"{error_message} ({error_code})"}
                else:
                    retries += 1
                    continue
            if "candidates" in response_data and response_data["candidates"]:
                candidate = response_data["candidates"][0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                if parts and parts[0].get("text"):
                    generated_text = parts[0].get("text", "")
                    title = ""
                    description = ""
                    tags = []
                    title_match = re.search(r"^Title:\s*(.*)", generated_text, re.MULTILINE | re.IGNORECASE)
                    if title_match: title = title_match.group(1).strip()
                    desc_match = re.search(r"^Description:\s*(.*)", generated_text, re.MULTILINE | re.IGNORECASE)
                    if desc_match: description = desc_match.group(1).strip()
                    tags_match = re.search(r"^Keywords:\s*(.*)", generated_text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
                    if tags_match:
                        tags_raw = tags_match.group(1).strip()
                        tags = [tag.strip() for tag in tags_raw.split(',') if tag.strip()]
                        tags = tags[:50]
                    if title or description or tags:
                        with MODEL_LOCK:
                            MODEL_RATE_LIMITERS[selected_model].tokens = min(
                                MODEL_RATE_LIMITERS[selected_model].capacity,
                                MODEL_RATE_LIMITERS[selected_model].tokens + 0.5
                            )
                        return {"title": title, "description": description, "tags": tags}
                    else:
                        log_message("  Error: Gagal mengekstrak metadata dari respons Gemini.")
                        retries += 1
                        continue
                else:
                    log_message(f"  Error: Struktur respons Gemini tidak valid (tidak ada 'parts'/'text').")
                    retries += 1
                    continue
            elif "promptFeedback" in response_data:
                feedback = response_data.get('promptFeedback', {})
                block_reason = feedback.get('blockReason', 'UNKNOWN')
                log_message(f"  Error: Respons diblokir oleh Gemini. Alasan: {block_reason}")
                return {"error": f"Content blocked: {block_reason}"}
            else:
                log_message(f"  Error: Respons Gemini tidak berisi 'candidates'.")
                retries += 1
                continue
        except requests.exceptions.Timeout:
            log_message(f"  Error: Timeout API untuk {image_basename}. Mencoba lagi...")
            retries += 1
            continue
        except requests.exceptions.SSLError as e:
            log_message(f"  Error SSL: {e}")
            retries += 1
            time.sleep(2)
            continue
        except requests.exceptions.ConnectionError as e:
            log_message(f"  Error koneksi: {e}")
            retries += 1
            time.sleep(2)
            continue
        except requests.exceptions.RequestException as e:
            log_message(f"  Error request: {e}")
            retries += 1
            continue
        except Exception as e:
            log_message(f"  Error tak terduga: {e}")
            if "time" in str(e):
                log_message("  Error terkait variabel time. Pastikan modul time diimpor dengan benar.")
            retries += 1
            continue
    log_message(f"  Semua percobaan gagal untuk {image_basename} setelah {API_MAX_RETRIES} kali percobaan.")
    return {"error": "Maximum retries exceeded"}

def get_gemini_metadata_with_key_rotation(image_path, api_keys, stop_event: threading.Event):
    if not api_keys:
        return {"error": "No API keys available"}
    if not isinstance(api_keys, list):
        api_keys = [api_keys]
    shuffled_keys = api_keys.copy()
    random.shuffle(shuffled_keys)
    image_basename = os.path.basename(image_path)
    used_keys = set() 
    blacklisted_keys = set() 
    blacklisted_models = set()
    max_attempts = min(len(api_keys) * len(GEMINI_MODELS) * 2, 20)
    attempt = 0
    while attempt < max_attempts:
        if stop_event.is_set():
            return "stopped"
        available_keys = [k for k in shuffled_keys if k not in blacklisted_keys]
        if not available_keys:
            log_message(f"  Semua API key rate limited. Menunggu 10 detik sebelum mencoba lagi...")
            time.sleep(10)
            blacklisted_keys.clear()
            available_keys = shuffled_keys
        available_models = [m for m in GEMINI_MODELS if m not in blacklisted_models]
        if not available_models:
            log_message(f"  Semua model rate limited. Menunggu 5 detik sebelum mencoba lagi...")
            time.sleep(5)
            blacklisted_models.clear()
        api_key = available_keys[attempt % len(available_keys)]
        used_keys.add(api_key)
        log_message(f"  Mengirim {image_basename} ke Gemini API menggunakan key #{shuffled_keys.index(api_key)+1}...")
        wait_for_api_key_cooldown(api_key)
        try:
            result = _call_gemini_api_once(image_path, api_key, stop_event)
            if result != "error_429" and result != "error_other":
                return result
            if result == "error_429":
                log_message(f"  API key #{shuffled_keys.index(api_key)+1} rate limited. Mencoba kombinasi lain...")
                blacklisted_keys.add(api_key)
            if result == "error_other":
                log_message(f"  Error API dengan key #{shuffled_keys.index(api_key)+1}. Mencoba kombinasi lain...")
        except Exception as e:
            log_message(f"  Error tak terduga dengan API key #{shuffled_keys.index(api_key)+1}: {e}")
        attempt += 1
        if attempt > len(api_keys) and attempt < max_attempts:
            delay = 5 + (attempt - len(api_keys)) * 2 
            log_message(f"  Menunggu {delay} detik sebelum mencoba kombinasi API key berikutnya...")
            time.sleep(delay)
    log_message(f"  Semua percobaan kombinasi API key dan model gagal untuk {image_basename}")
    return {"error": "Maximum retries exceeded with all API keys and models"}

def _call_gemini_api_once(image_path, api_key, stop_event: threading.Event):
    _, ext = os.path.splitext(image_path)
    allowed_api_ext = ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif')
    if not ext.lower() in allowed_api_ext:
        return {"error": f"Unsupported file type: {ext}"}
    try:
        if stop_event.is_set():
            return "stopped"
        selected_model = select_next_model()
        wait_for_model_cooldown(selected_model)
        api_endpoint = get_api_endpoint(selected_model)
        log_message(f"  Menggunakan model: {selected_model}")
        try:
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            return {"error": f"File read error: {str(e)}"}
        mime_type = f"image/{ext.lower().replace('.', '')}"
        if mime_type == "image/jpg": mime_type = "image/jpeg"
        if mime_type not in ["image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"]:
            mime_type = "image/jpeg"
        payload = {
            "contents": [{"parts": [{"text": PROMPT_TEXT}, {"inline_data": {"mime_type": mime_type, "data": image_data}}]}],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 500,
                "topP": 0.8,
                "topK": 40
            }
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MetadataProcessor/1.0"
        }
        api_url = f"{api_endpoint}?key={api_key}"
        session = requests.Session()
        session.mount('https://', requests.adapters.HTTPAdapter(
            max_retries=requests.adapters.Retry(
                total=1,
                backoff_factor=1.0,
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=["POST"]
            )
        ))
        response = session.post(api_url, headers=headers, json=payload, timeout=API_TIMEOUT)
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            log_message(f"  Error: Respons API bukan JSON valid (Status: {response.status_code}).")
            with MODEL_LOCK:
                MODEL_RATE_LIMITERS[selected_model].tokens = max(0, MODEL_RATE_LIMITERS[selected_model].tokens - 2)
            return "error_other"
        if response.status_code != 200:
            error_details = response_data.get("error", {})
            error_code = error_details.get("code", "UNKNOWN")
            error_message = error_details.get("message", "No error message")
            log_message(f"  API Error [{selected_model}]: {error_code} - {error_message}")
            if error_code == 429:
                with MODEL_LOCK:
                    MODEL_RATE_LIMITERS[selected_model].tokens = max(0, MODEL_RATE_LIMITERS[selected_model].tokens - 5)
                log_message(f"  Model {selected_model} terkena rate limit, akan dirotasi ke model lain.")
                return "error_429"
            else:
                return "error_other"
        if "candidates" in response_data and response_data["candidates"]:
            candidate = response_data["candidates"][0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            if parts and parts[0].get("text"):
                generated_text = parts[0].get("text", "")
                title = ""
                description = ""
                tags = []
                title_match = re.search(r"^Title:\s*(.*)", generated_text, re.MULTILINE | re.IGNORECASE)
                if title_match: title = title_match.group(1).strip()
                desc_match = re.search(r"^Description:\s*(.*)", generated_text, re.MULTILINE | re.IGNORECASE)
                if desc_match: description = desc_match.group(1).strip()
                tags_match = re.search(r"^Keywords:\s*(.*)", generated_text, re.MULTILINE | re.IGNORECASE | re.DOTALL)
                if tags_match:
                    tags_raw = tags_match.group(1).strip()
                    tags = [tag.strip() for tag in tags_raw.split(',') if tag.strip()]
                    tags = tags[:49]
                if title or description or tags:
                    with MODEL_LOCK:
                        MODEL_RATE_LIMITERS[selected_model].tokens = min(
                            MODEL_RATE_LIMITERS[selected_model].capacity,
                            MODEL_RATE_LIMITERS[selected_model].tokens + 0.5
                        )
                    return {"title": title, "description": description, "tags": tags}
                else:
                    log_message(f"  Error: Gagal mengekstrak metadata dari respons {selected_model}.")
                    return "error_other"
            else:
                log_message(f"  Error: Struktur respons {selected_model} tidak valid (tidak ada 'parts'/'text').")
                return "error_other"
        elif "promptFeedback" in response_data:
            feedback = response_data.get('promptFeedback', {})
            block_reason = feedback.get('blockReason', 'UNKNOWN')
            log_message(f"  Error: Respons diblokir oleh {selected_model}. Alasan: {block_reason}")
            return {"error": f"Content blocked by {selected_model}: {block_reason}"}
        else:
            log_message(f"  Error: Respons {selected_model} tidak berisi 'candidates'.")
            return "error_other"
    except requests.exceptions.Timeout:
        log_message(f"  Error: Timeout API.")
        return "error_other"
    except requests.exceptions.ConnectionError:
        log_message(f"  Error koneksi.")
        return "error_other" 
    except Exception as e:
        log_message(f"  Error tak terduga: {e}")
        return "error_other"
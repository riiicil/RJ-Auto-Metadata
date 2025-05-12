import requests
from .gemini_api import get_api_endpoint, DEFAULT_MODEL

def check_api_keys_status(api_keys, model=None):
    """
    Mengecek status semua API key Gemini.
    Args:
        api_keys (list): List API key (string)
        model (str, optional): Model Gemini yang ingin dites. Default: DEFAULT_MODEL
    Returns:
        dict: {api_key: (status_code, pesan_singkat)}
    """
    results = {}
    model_to_use = model or DEFAULT_MODEL
    api_endpoint = get_api_endpoint(model_to_use)
    headers = {"Content-Type": "application/json", "User-Agent": "GeminiKeyChecker/1.0"}
    payload = {
        "contents": [
            {"parts": [
                {"text": "Test API key status only. Ignore this request."}
            ]}
        ],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8},
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]
    }
    for key in api_keys:
        api_url = f"{api_endpoint}?key={key}"
        try:
            resp = requests.post(api_url, headers=headers, json=payload, timeout=20)
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = resp.text
            if resp.status_code == 200:
                results[key] = (200, "OK")
            else:
                # Ambil pesan error singkat
                if isinstance(resp_json, dict):
                    msg = resp_json.get('error', resp_json)
                    if isinstance(msg, dict):
                        msg = msg.get('message', str(msg))
                else:
                    msg = str(resp_json)
                msg = str(msg)[:60]
                results[key] = (resp.status_code, msg)
        except Exception as e:
            results[key] = (-1, str(e)[:60])
    return results 
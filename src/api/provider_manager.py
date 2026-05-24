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

# src/api/provider_manager.py
from __future__ import annotations

from typing import Iterable, List, Optional
import re

from src.api import (
    gemini_api, openai_api, openrouter_api, groq_api, koboillm_api,
    mistral_api, blackbox_api,
)
from src.utils.logging import log_message
from src.utils import stop_flag as _stop_flag

PROVIDER_GEMINI = "Gemini"
PROVIDER_OPENAI = "OpenAI"
PROVIDER_OPENROUTER = "OpenRouter"
PROVIDER_GROQ = "Groq"
PROVIDER_KOBOILLM = "KoboiLLM"
PROVIDER_CUSTOM = "Custom"
PROVIDER_MISTRAL = "Mistral"
PROVIDER_BLACKBOX = "Blackbox"
_DEFAULT_PROVIDER = PROVIDER_GEMINI

PROVIDER_BASE_URLS = {
    PROVIDER_GEMINI: "https://generativelanguage.googleapis.com/v1beta/openai/",
    PROVIDER_OPENAI: "https://api.openai.com/v1",
    PROVIDER_OPENROUTER: "https://openrouter.ai/api/v1",
    PROVIDER_GROQ: "https://api.groq.com/openai/v1",
    PROVIDER_KOBOILLM: "https://litellm.koboi2026.biz.id",
    PROVIDER_MISTRAL: "https://api.mistral.ai/v1",
    PROVIDER_BLACKBOX: "https://api.blackbox.ai",
    PROVIDER_CUSTOM: "",
}

_PROVIDERS = {
    PROVIDER_GEMINI: {
        "module": gemini_api,
        "supports_auto_rotation": False,
    },
    PROVIDER_OPENAI: {
        "module": openai_api,
        "supports_auto_rotation": False,
    },
    PROVIDER_OPENROUTER: {
        "module": openrouter_api,
        "supports_auto_rotation": False,
    },
    PROVIDER_GROQ: {
        "module": groq_api,
        "supports_auto_rotation": False,
    },
    PROVIDER_KOBOILLM: {
        "module": koboillm_api,
        "supports_auto_rotation": False,
    },
    PROVIDER_MISTRAL: {
        "module": mistral_api,
        "supports_auto_rotation": False,
    },
    PROVIDER_BLACKBOX: {
        "module": blackbox_api,
        "supports_auto_rotation": False,
    },
    PROVIDER_CUSTOM: {
        "module": None,
        "supports_auto_rotation": False,
    },
}

_TITLE_HARD_MAX = 200  # Adobe Stock absolute maximum for title


def _sanitize_title_length(metadata: dict) -> dict:
    """Hard-truncate title to _TITLE_HARD_MAX chars if LLM exceeded the limit.

    Truncates at the last word boundary to avoid cutting mid-word.
    Only triggers when the LLM ignores the max_chars instruction.
    """
    title = metadata.get("title", "")
    if isinstance(title, str) and len(title) > _TITLE_HARD_MAX:
        truncated = title[:_TITLE_HARD_MAX].rsplit(" ", 1)[0]
        metadata["title"] = truncated
        from src.utils.logging import log_message
        log_message(
            f"Warning: Title truncated from {len(title)} to {len(truncated)} chars "
            f"(hard max {_TITLE_HARD_MAX})",
            "warning",
        )
    return metadata


def list_providers() -> List[str]:
    return list(_PROVIDERS.keys())


def get_default_provider() -> str:
    return _DEFAULT_PROVIDER


def get_provider_module(provider: str):
    provider_key = provider if provider in _PROVIDERS else _DEFAULT_PROVIDER
    return _PROVIDERS[provider_key]["module"], provider_key


def get_model_choices(provider: str) -> List[str]:
    """Stub kept for UI compatibility. Returns empty list (Phase 2 adds Fetch)."""
    return []


def get_default_model(provider: str) -> str:
    """Stub kept for UI compatibility. Returns empty string (Phase 2 adds Fetch)."""
    return ""


def fetch_models(provider: str, api_key: str, base_url: Optional[str] = None) -> list:
    """Fetch available model IDs from the provider's OpenAI-compatible /models endpoint."""
    from openai import OpenAI

    # Resolve endpoint URL
    if provider == PROVIDER_CUSTOM:
        url = (base_url or "").strip()
        if not url:
            log_message("Custom provider requires a Base URL to fetch models.", "warning")
            return []
    else:
        url = PROVIDER_BASE_URLS.get(provider, "")
        if not url:
            log_message(f"No base URL configured for provider: {provider}", "warning")
            return []

    try:
        client = OpenAI(api_key=api_key, base_url=url, timeout=15.0)
        response = client.models.list()
        all_ids = sorted(m.id for m in response.data)

        # Filter out non-generative models (embeddings, tts, whisper, image-gen, etc.)
        _SKIP_PREFIXES = (
            "text-embedding", "tts-", "whisper-", "dall-e",
            "omni-moderation", "text-moderation", "babbage",
            "davinci", "curie", "ada",
        )
        filtered = [m for m in all_ids if not any(m.startswith(p) for p in _SKIP_PREFIXES)]
        log_message(
            f"Fetched {len(filtered)} models for {provider} "
            f"(filtered from {len(all_ids)} total).",
            "info",
        )
        return filtered
    except Exception as exc:
        log_message(f"Failed to fetch models for {provider}: {exc}", "error")
        return []


def supports_auto_rotation(provider: str) -> bool:
    _, provider_key = get_provider_module(provider)
    return bool(_PROVIDERS[provider_key].get("supports_auto_rotation", False))


def select_api_key(provider: str, api_keys: Iterable[str]):
    module, provider_key = get_provider_module(provider)
    if module is None:
        keys = list(api_keys)
        return keys[0] if keys else None
    if hasattr(module, "select_api_key"):
        return module.select_api_key(list(api_keys))
    keys = list(api_keys)
    return keys[0] if keys else None


def get_metadata(
    provider: str,
    image_path,
    api_key: str,
    stop_event,
    use_png_prompt: bool = False,
    use_video_prompt: bool = False,
    selected_model: Optional[str] = None,
    keyword_count: str = "49",
    priority: str = "Detailed",
    is_vector_conversion: bool = False,
    base_url_override: Optional[str] = None,
):
    module, provider_key = get_provider_module(provider)

    def _fill_keywords_if_short(metadata: dict, keyword_count_value: str):
        try:
            limit = int(keyword_count_value)
            if limit < 1:
                limit = 49
            if limit > 100:
                limit = limit
        except Exception:
            limit = 49

        raw_tags = metadata.get("tags") or []
        title = metadata.get("title", "") or ""
        description = metadata.get("description", "") or ""

        seen = set()
        final_tags: List[str] = []

        def add_tag(tag_value):
            tag_text = str(tag_value).strip()
            if not tag_text:
                return
            tag_text = re.sub(r"[^\w\-]", " ", tag_text)
            tag_text = re.sub(r"\s+", " ", tag_text).strip()
            if not tag_text:
                return
            if " " in tag_text:
                tag_text = tag_text.replace(" ", "")
                if not tag_text:
                    return
            lower = tag_text.lower()
            if lower in seen:
                return
            seen.add(lower)
            final_tags.append(tag_text)

        for tag in raw_tags:
            add_tag(tag)

        if len(final_tags) >= limit:
            metadata["tags"] = final_tags[:limit]
            return metadata

        filler_words: List[str] = []

        def collect_words(text: str):
            for word in re.split(r"[^A-Za-z0-9]+", text or ""):
                if len(word) >= 3:
                    filler_words.append(word)

        collect_words(title)
        collect_words(description)

        for word in filler_words:
            if len(final_tags) >= limit:
                break
            add_tag(word)

        metadata["tags"] = final_tags[:limit]
        return metadata

    effective_model = selected_model

    if provider_key == PROVIDER_CUSTOM:
        effective_base_url = (base_url_override or "").strip()
        if not effective_base_url:
            log_message("Custom provider requires a base_url_override.", "error")
            return {"error": "custom_provider_no_base_url"}
        if not (effective_model or "").strip():
            log_message("Custom provider requires a model selection.", "error")
            return {"error": "custom_provider_no_model"}
        result = openrouter_api.get_openrouter_metadata(
            image_path,
            api_key,
            stop_event,
            use_png_prompt=use_png_prompt,
            use_video_prompt=use_video_prompt,
            selected_model_input=effective_model,
            keyword_count=keyword_count,
            priority=priority,
            is_vector_conversion=is_vector_conversion,
            base_url_override=effective_base_url,
        )
        if isinstance(result, dict) and "error" not in result:
            return _sanitize_title_length(_fill_keywords_if_short(result, keyword_count))
        return result

    if provider_key == PROVIDER_GEMINI:
        if selected_model in (None, "", "Auto Rotation"):
            effective_model = None
        result = module.get_gemini_metadata(
            image_path,
            api_key,
            stop_event,
            use_png_prompt=use_png_prompt,
            use_video_prompt=use_video_prompt,
            selected_model_input=effective_model,
            keyword_count=keyword_count,
            priority=priority,
            is_vector_conversion=is_vector_conversion,
        )
        if isinstance(result, dict) and "error" not in result:
            return _sanitize_title_length(_fill_keywords_if_short(result, keyword_count))
        return result
    if provider_key == PROVIDER_OPENROUTER:
        result = module.get_openrouter_metadata(
            image_path,
            api_key,
            stop_event,
            use_png_prompt=use_png_prompt,
            use_video_prompt=use_video_prompt,
            selected_model_input=effective_model,
            keyword_count=keyword_count,
            priority=priority,
            is_vector_conversion=is_vector_conversion,
        )
        if isinstance(result, dict) and "error" not in result:
            return _sanitize_title_length(_fill_keywords_if_short(result, keyword_count))
        return result
    if provider_key == PROVIDER_GROQ:
        result = module.get_groq_metadata(
            image_path,
            api_key,
            stop_event,
            use_png_prompt=use_png_prompt,
            use_video_prompt=use_video_prompt,
            selected_model_input=effective_model,
            keyword_count=keyword_count,
            priority=priority,
            is_vector_conversion=is_vector_conversion,
        )
        if isinstance(result, dict) and "error" not in result:
            return _sanitize_title_length(_fill_keywords_if_short(result, keyword_count))
        return result
    if provider_key == PROVIDER_KOBOILLM:
        result = module.get_koboillm_metadata(
            image_path,
            api_key,
            stop_event,
            use_png_prompt=use_png_prompt,
            use_video_prompt=use_video_prompt,
            selected_model_input=effective_model,
            keyword_count=keyword_count,
            priority=priority,
            is_vector_conversion=is_vector_conversion,
        )
        if isinstance(result, dict) and "error" not in result:
            return _sanitize_title_length(_fill_keywords_if_short(result, keyword_count))
        return result
    if provider_key == PROVIDER_MISTRAL:
        result = module.get_mistral_metadata(
            image_path,
            api_key,
            stop_event,
            use_png_prompt=use_png_prompt,
            use_video_prompt=use_video_prompt,
            selected_model_input=effective_model,
            keyword_count=keyword_count,
            priority=priority,
            is_vector_conversion=is_vector_conversion,
        )
        if isinstance(result, dict) and "error" not in result:
            return _sanitize_title_length(_fill_keywords_if_short(result, keyword_count))
        return result

    if provider_key == PROVIDER_BLACKBOX:
        result = module.get_blackbox_metadata(
            image_path,
            api_key,
            stop_event,
            use_png_prompt=use_png_prompt,
            use_video_prompt=use_video_prompt,
            selected_model_input=effective_model,
            keyword_count=keyword_count,
            priority=priority,
            is_vector_conversion=is_vector_conversion,
        )
        if isinstance(result, dict) and "error" not in result:
            return _sanitize_title_length(_fill_keywords_if_short(result, keyword_count))
        return result

    result = module.get_openai_metadata(
        image_path,
        api_key,
        stop_event,
        use_png_prompt=use_png_prompt,
        use_video_prompt=use_video_prompt,
        selected_model_input=effective_model,
        keyword_count=keyword_count,
        priority=priority,
        is_vector_conversion=is_vector_conversion,
    )
    if isinstance(result, dict) and "error" not in result:
        return _sanitize_title_length(_fill_keywords_if_short(result, keyword_count))
    return result


def check_api_keys_status(
    provider: str,
    api_keys: Iterable[str],
    model: Optional[str] = None,
    base_url_override: Optional[str] = None,
):
    module, provider_key = get_provider_module(provider)
    if module is None:
        return {k: (-1, "No module for this provider") for k in api_keys}
    if provider_key == PROVIDER_CUSTOM:
        effective_base_url = (base_url_override or "").strip()
        if not effective_base_url:
            return {k: (-1, "Custom provider requires a Base URL") for k in api_keys}
        return openrouter_api.check_api_keys_status(
            list(api_keys),
            model=model,
            base_url_override=effective_base_url,
        )
    return module.check_api_keys_status(list(api_keys), model=model)


def set_force_stop(provider: Optional[str] = None) -> None:
    """Activate the global stop flag. The provider argument is ignored (kept for
    backward compatibility with call sites that pass a provider name)."""
    _stop_flag.set_force_stop()
    log_message("Force stop flag has been activated. All processes will stop immediately.", "warning")


def reset_force_stop(provider: Optional[str] = None) -> None:
    """Clear the global stop flag. The provider argument is ignored."""
    _stop_flag.reset_force_stop()


def is_stop_requested(provider: Optional[str] = None) -> bool:
    """Return True if a stop has been requested. The provider argument is ignored."""
    return _stop_flag.is_stop_requested()


def check_stop_event(provider: str, stop_event, message: Optional[str] = None) -> bool:
    module, _ = get_provider_module(provider)
    if module is not None and hasattr(module, "check_stop_event"):
        return module.check_stop_event(stop_event, message)
    if stop_event is not None:
        try:
            if stop_event.is_set():
                if message:
                    log_message(message)
                return True
        except Exception:
            return False
    return False

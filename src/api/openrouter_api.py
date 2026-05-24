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

# src/api/openrouter_api.py
from __future__ import annotations

import base64
import json
import os
import threading
import time
from typing import Dict, Iterable, List, Optional, Tuple, Union
from urllib.parse import urlsplit, urlunsplit

import requests
import re

from src.api.prompts import select_prompt
from src.utils.logging import log_message
from src.utils.json_utils import _clean_json_text
from src.utils.stop_flag import is_stop_requested

API_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_CHAT_PATH = "/chat/completions"
API_TIMEOUT = 60
API_MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 8
MAX_OUTPUT_TOKENS: Optional[int] = None
OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER")
OPENROUTER_TITLE = os.getenv("OPENROUTER_APP_TITLE")


_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
_STRUCTURED_OUTPUT_MODEL_PREFIXES: Tuple[str, ...] = (
	"openai/gpt-5",
	"openai/gpt-4.1",
	"google/gemini-2.5",
	"google/gemini-2.0",
	"anthropic/claude",
	"x-ai/grok-4",
	"meta-llama/llama-4",
)

_JSON_SCHEMA = {
	"name": "metadata_response",
	"schema": {
		"type": "object",
		"properties": {
			"title": {"type": "string", "maxLength": 200},
			"description": {"type": "string", "maxLength": 200},
			"keywords": {
				"type": "array",
				"items": {"type": "string"},
				"maxItems": 60,
			},
			"adobe_stock_category": {"type": "string"},
			"shutterstock_category": {"type": "string"},
		},
		"required": [
			"title",
			"description",
			"keywords",
			"adobe_stock_category",
			"shutterstock_category",
		],
		"additionalProperties": False,
	},
}

_API_KEY_LOCK = threading.Lock()
_API_KEY_INDEX = 0
_WARNED_MODELS_FOR_SCHEMA: set[str] = set()


def _normalize_model_name(model: str) -> str:
	return (model or "").strip()


def _model_suffix(model: str) -> str:
	normalized = _normalize_model_name(model)
	if "/" in normalized:
		return normalized.split("/")[-1]
	return normalized


def _is_gpt5_model(model: str) -> bool:
	suffix = _model_suffix(model)
	return suffix.startswith("gpt-5")


def _model_supports_structured_outputs(model: str) -> bool:
	normalized = _normalize_model_name(model)
	return any(
		normalized == prefix or normalized.startswith(f"{prefix}-")
		for prefix in _STRUCTURED_OUTPUT_MODEL_PREFIXES
	)


def _normalize_keyword_count(keyword_count: Union[str, int]) -> int:
	try:
		value = int(keyword_count)
		if value <= 0:
			return 10
		return min(value, 60)
	except Exception:
		return 49


def select_api_key(api_keys: Iterable[str]) -> Optional[str]:
	keys = list(api_keys) if not isinstance(api_keys, list) else api_keys
	if not keys:
		return None
	global _API_KEY_INDEX
	with _API_KEY_LOCK:
		key = keys[_API_KEY_INDEX % len(keys)]
		_API_KEY_INDEX = (_API_KEY_INDEX + 1) % len(keys)
		return key


def check_stop_event(stop_event, message: Optional[str] = None) -> bool:
	if is_stop_requested():
		if message:
			log_message(message)
		return True
	if stop_event is None:
		return False
	try:
		is_set = stop_event.is_set()
		if is_set and message:
			log_message(message)
		return is_set
	except Exception as exc:
		log_message(f"Failed to inspect stop_event: {exc}")
	return False


def _encode_image(path: str) -> Tuple[str, str]:
	_, ext = os.path.splitext(path)
	mime_type = "image/jpeg"
	if ext.lower() == ".png":
		mime_type = "image/png"
	elif ext.lower() == ".webp":
		mime_type = "image/webp"
	elif ext.lower() in {".heic", ".heif"}:
		mime_type = "image/heic"
	with open(path, "rb") as image_file:
		encoded = base64.b64encode(image_file.read()).decode("utf-8")
	return encoded, mime_type


def _build_payload(
	images: List[str],
	prompt_text: str,
	keyword_count: Union[str, int],
	model: str,
	reasoning_effort: Optional[str],
	verbosity: Optional[str],
	max_output_tokens: Optional[int],
	temperature: Optional[float],
) -> dict:
	system_instruction = (
		"You generate stock photography metadata. Respond strictly with JSON that "
		"includes the keys 'title', 'description', 'keywords', 'adobe_stock_category', "
		"and 'shutterstock_category'. Limit text fields to 200 characters and keep the "
		"keywords array relevant. Do not include extra commentary."
	)

	user_content: List[dict] = []
	if prompt_text:
		user_content.append(
			{
				"type": "text",
				"text": (
					f"{prompt_text}\n"
					"Return 60 single-word keywords; ensure at least 55 are unique. "
					"If you generate more, keep the top 60 most relevant. No multi-word phrases."
				),
			}
		)

	for image_path in images:
		encoded, mime_type = _encode_image(image_path)
		data_url = f"data:{mime_type};base64,{encoded}"
		user_content.append(
			{
				"type": "image_url",
				"image_url": {
					"url": data_url,
				},
			}
		)

	messages: List[dict] = [
		{"role": "system", "content": system_instruction},
	]

	if user_content:
		messages.append({"role": "user", "content": user_content})

	payload = {
		"model": model,
		"messages": messages,
	}

	if max_output_tokens:
		payload["max_tokens"] = max_output_tokens

	if temperature is not None:
		payload["temperature"] = temperature
	else:
		payload["temperature"] = 0.2

	if _is_gpt5_model(model):
		payload["reasoning"] = {"effort": reasoning_effort or "medium"}

	if _model_supports_structured_outputs(model):
		payload["response_format"] = {
			"type": "json_object",
		}
	else:
		if model not in _WARNED_MODELS_FOR_SCHEMA:
			log_message(
				(
					"OpenRouter model %s does not advertise structured outputs; "
					"relying on instructions to keep JSON clean."
				)
				% model,
				"warning",
			)
			_WARNED_MODELS_FOR_SCHEMA.add(model)

	return payload


def _extract_metadata_from_json(raw_json: dict, keyword_count: Union[str, int]) -> dict:
	keyword_limit = 60
	keywords = raw_json.get("keywords") or []
	raw_keywords: List[str] = []
	if isinstance(keywords, list):
		raw_keywords = [str(item).strip() for item in keywords if str(item).strip()]
		tags = list(raw_keywords)
	elif isinstance(keywords, str):
		raw_keywords = [part.strip() for part in keywords.split(",") if part.strip()]
		tags = list(raw_keywords)
	else:
		tags = []
	tags = list(dict.fromkeys(tags))[:keyword_limit]
	return {
		"title": raw_json.get("title", ""),
		"description": raw_json.get("description", ""),
		"tags": tags,
		"as_category": raw_json.get("adobe_stock_category", ""),
		"ss_category": raw_json.get("shutterstock_category", ""),
	}


def _parse_openrouter_response(response_data: dict, keyword_count: Union[str, int]) -> Optional[dict]:
	choices = response_data.get("choices") or []
	observed_types: set[str] = set()

	for choice in choices:
		message = choice.get("message") or {}
		content = message.get("content")
		if isinstance(content, str):
			try:
				cleaned_content = _clean_json_text(content)
				raw_json = json.loads(cleaned_content)
				if isinstance(raw_json, dict):
					return _extract_metadata_from_json(raw_json, keyword_count)
			except (json.JSONDecodeError, TypeError) as e:
				log_message(f"Failed to parse JSON from OpenRouter content: {e}. Content: {content[:100]}...", "debug")
				continue
		elif isinstance(content, list):
			for item in content:
				if not isinstance(item, dict):
					continue
				item_type = item.get("type")
				if item_type:
					observed_types.add(str(item_type))

				if item_type in {"text", "output_text"}:
					text_value = item.get("text")
					if isinstance(text_value, str):
						try:
							cleaned_text = _clean_json_text(text_value)
							raw_json = json.loads(cleaned_text)
							if isinstance(raw_json, dict):
								return _extract_metadata_from_json(raw_json, keyword_count)
						except (json.JSONDecodeError, TypeError):
							continue
				elif item_type == "json_object":
					data = item.get("json_object")
					if isinstance(data, dict):
						return _extract_metadata_from_json(data, keyword_count)
					maybe_text = item.get("text")
					if isinstance(maybe_text, str):
						try:
							cleaned_text = _clean_json_text(maybe_text)
							raw_json = json.loads(cleaned_text)
							if isinstance(raw_json, dict):
								return _extract_metadata_from_json(raw_json, keyword_count)
						except (json.JSONDecodeError, TypeError):
							continue

		tool_calls = message.get("tool_calls") or []
		for tool_call in tool_calls:
			if not isinstance(tool_call, dict):
				continue
			function_block = tool_call.get("function") or {}
			arguments = function_block.get("arguments")
			if isinstance(arguments, str):
				try:
					cleaned_args = _clean_json_text(arguments)
					raw_json = json.loads(cleaned_args)
					if isinstance(raw_json, dict):
						return _extract_metadata_from_json(raw_json, keyword_count)
				except (json.JSONDecodeError, TypeError):
					continue

	if choices and observed_types:
		log_message(
			"OpenRouter response content types not parsed: %s"
			% ", ".join(sorted(observed_types)),
			"warning",
		)
	return None


def _validate_images(images: Iterable[str]) -> Tuple[bool, Optional[str]]:
	for image in images:
		_, ext = os.path.splitext(image)
		if ext.lower() not in _ALLOWED_EXTENSIONS:
			return False, f"File type {ext} not supported for OpenRouter: {os.path.basename(image)}"
		if not os.path.exists(image):
			return False, f"Image not found for OpenRouter request: {image}"
	return True, None


def _resolve_chat_endpoint(base_url_override: Optional[str]) -> str:
	"""Build the chat-completions URL for the active provider.

	When ``base_url_override`` is empty/None we fall back to the OpenRouter
	default. Otherwise we accept either a bare base URL (``https://host/v1``)
	or a fully-qualified chat endpoint (``https://host/v1/chat/completions``)
	and normalise to the latter while preserving query strings and fragments.
	"""
	candidate = (base_url_override or "").strip()
	if not candidate:
		return API_ENDPOINT
	parts = urlsplit(candidate)
	path = parts.path.rstrip("/")
	if not path.endswith(_DEFAULT_CHAT_PATH):
		path = f"{path}{_DEFAULT_CHAT_PATH}"
	return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def get_openrouter_metadata(
	image_path: Union[str, List[str]],
	api_key: str,
	stop_event,
	use_png_prompt: bool = False,
	use_video_prompt: bool = False,
	selected_model_input: Optional[str] = None,
	keyword_count: Union[str, int] = "49",
	priority: str = "Detailed",
	is_vector_conversion: bool = False,
	base_url_override: Optional[str] = None,
):
	images: List[str] = image_path if isinstance(image_path, list) else [image_path]
	is_valid, error_message = _validate_images(images)
	if not is_valid:
		log_message(error_message or "Invalid image for OpenRouter request", "warning")
		return {"error": error_message or "unsupported_image_format"}

	if check_stop_event(stop_event, "Metadata request cancelled before submission"):
		return "stopped"

	endpoint_url = _resolve_chat_endpoint(base_url_override)
	provider_label = "Custom" if base_url_override else "OpenRouter"
	default_model = "openai/gpt-4.1" if not base_url_override else ""
	model_to_use = (selected_model_input or default_model).strip()
	if not model_to_use:
		log_message(
			f"{provider_label} provider requires a model selection.",
			"error",
		)
		return {"error": "custom_provider_no_model" if base_url_override else "openrouter_no_model"}
	api_model = model_to_use
	reasoning_effort = None
	verbosity = None
	temperature = 0.2
	max_output_tokens = MAX_OUTPUT_TOKENS if MAX_OUTPUT_TOKENS is not None else 5120

	prompt_text = select_prompt(
		priority,
		use_png_prompt=use_png_prompt,
		use_video_prompt=use_video_prompt,
		provider="openrouter",
	)

	attempt = 0
	while attempt < API_MAX_RETRIES:
		if check_stop_event(stop_event, f"{provider_label} request cancelled during retries"):
			return "stopped"

		payload = _build_payload(
			images,
			prompt_text,
			keyword_count,
			api_model,
			reasoning_effort,
			verbosity,
			max_output_tokens,
			temperature,
		)

		headers = {
			"Authorization": f"Bearer {api_key}",
			"Content-Type": "application/json",
			"Accept": "application/json",
		}
		if not base_url_override and OPENROUTER_HTTP_REFERER:
			headers["HTTP-Referer"] = OPENROUTER_HTTP_REFERER
		if not base_url_override and OPENROUTER_TITLE:
			headers["X-Title"] = OPENROUTER_TITLE

		try:
			log_message(
				f"Sending metadata request to {provider_label} model {model_to_use} (key ...{api_key[-5:]})",
				"info",
			)
			response = requests.post(
				endpoint_url,
				headers=headers,
				json=payload,
				timeout=API_TIMEOUT,
			)
		except requests.RequestException as exc:
			if check_stop_event(stop_event):
				return "stopped"
			log_message(f"{provider_label} request failed: {exc}", "error")
			attempt += 1
			if attempt >= API_MAX_RETRIES:
				return {"error": str(exc)}
			sleep_duration = RETRY_DELAY_SECONDS * attempt
			sleep_start = time.time()
			while time.time() - sleep_start < sleep_duration:
				if check_stop_event(stop_event, f"{provider_label} retry sleep cancelled"):
					return "stopped"
				time.sleep(0.1)
			continue

		if response.status_code == 200:
			try:
				response_data = response.json()
			except json.JSONDecodeError as exc:
				log_message(f"Failed to decode {provider_label} response JSON: {exc}", "error")
				return {"error": "invalid_json"}

			usage_payload = response_data.get("usage") or {}
			output_tokens = (
				usage_payload.get("completion_tokens")
				or usage_payload.get("output_tokens")
			)


			metadata = _parse_openrouter_response(response_data, keyword_count)
			if metadata:
				log_message(f"Metadata successfully extracted from {provider_label} response", "success")
				return metadata

			log_message(f"{provider_label} response did not include usable metadata", "warning")
			return {"error": "empty_response"}

		if response.status_code in {401, 403}:
			log_message(f"{provider_label} authentication error - check API key permissions", "error")
			return {"error": f"Authentication failed ({response.status_code})"}

		if response.status_code == 429:
			if check_stop_event(stop_event):
				return "stopped"
			log_message(f"{provider_label} rate limit hit, backing off before retry", "warning")
			attempt += 1
			sleep_duration = RETRY_DELAY_SECONDS * attempt
			sleep_start = time.time()
			while time.time() - sleep_start < sleep_duration:
				if check_stop_event(stop_event, f"{provider_label} retry sleep cancelled"):
					return "stopped"
				time.sleep(0.1)
			continue

		if 500 <= response.status_code < 600:
			if check_stop_event(stop_event):
				return "stopped"
			log_message(f"{provider_label} server error {response.status_code}, retrying", "warning")
			attempt += 1
			sleep_duration = RETRY_DELAY_SECONDS * attempt
			sleep_start = time.time()
			while time.time() - sleep_start < sleep_duration:
				if check_stop_event(stop_event, f"{provider_label} retry sleep cancelled"):
					return "stopped"
				time.sleep(0.1)
			continue

		try:
			error_payload = response.json()
			error_block = error_payload.get("error") if isinstance(error_payload, dict) else None
			error_message = None
			if isinstance(error_block, dict):
				error_message = error_block.get("message") or error_block.get("code")
				if not error_message:
					details = error_block.get("metadata") or error_block.get("details")
					if isinstance(details, (list, dict)):
						error_message = json.dumps(details)[:200]
					elif isinstance(details, str):
						error_message = details
		except Exception:
			error_message = response.text[:200]
		else:
			if not error_message:
				fallback_text = response.text.strip()
				if fallback_text:
					error_message = fallback_text[:200]

		log_message(
			f"{provider_label} request failed (HTTP {response.status_code}): {error_message}",
			"error",
		)
		return {"error": error_message or f"http_{response.status_code}"}

	return {"error": "openrouter_max_retries"}


def check_api_keys_status(
	api_keys: Iterable[str],
	model: Optional[str] = None,
	base_url_override: Optional[str] = None,
) -> dict:
	results: Dict[str, Tuple[int, str]] = {}
	endpoint_url = _resolve_chat_endpoint(base_url_override)
	default_model = "openai/gpt-4.1" if not base_url_override else ""
	test_model = (model or default_model).strip()
	if not test_model:
		for key in api_keys:
			results[key] = (-1, "Model required for custom provider key check")
		return results
	api_model = test_model

	payload = {
		"model": api_model,
		"messages": [
			{
				"role": "system",
				"content": (
					"You generate stock photography metadata. Respond with a JSON object"
					" containing the required keys."
				),
			},
			{
				"role": "user",
				"content": [
					{
						"type": "text",
						"text": "Test connectivity only. Respond with any JSON matching the schema.",
					}
				],
			},
		],
	}

	if _model_supports_structured_outputs(api_model):
		payload["response_format"] = {"type": "json_object"}

	payload["temperature"] = 0.2
	payload["max_tokens"] = 5120

	for key in api_keys:
		headers = {
			"Authorization": f"Bearer {key}",
			"Content-Type": "application/json",
			"Accept": "application/json",
		}
		if not base_url_override and OPENROUTER_HTTP_REFERER:
			headers["HTTP-Referer"] = OPENROUTER_HTTP_REFERER
		if not base_url_override and OPENROUTER_TITLE:
			headers["X-Title"] = OPENROUTER_TITLE

		try:
			response = requests.post(
				endpoint_url,
				headers=headers,
				json=payload,
				timeout=20,
			)
			if response.status_code == 200:
				results[key] = (200, "OK")
			else:
				try:
					error_payload = response.json()
					status_message = error_payload.get("error", {}).get("message", "Unknown error")
				except Exception:
					status_message = response.text[:120]
				results[key] = (response.status_code, status_message)
		except Exception as exc:
			results[key] = (-1, str(exc)[:120])

	return results

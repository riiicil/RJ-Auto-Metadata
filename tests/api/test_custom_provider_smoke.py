# RJ Auto Metadata
# Copyright (C) 2026 Riiicil
#
# Smoke test for custom-provider base_url plumbing.
"""Verify that ``base_url_override`` is threaded end-to-end.

These tests do not hit the network. They monkeypatch the
``openrouter_api`` HTTP boundary to record what the rest of the system
sends down to it, and assert the dispatcher / URL / error-classification
behaviour stays correct as the contribution evolves.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.api import openrouter_api, provider_manager  # noqa: E402
from src.processing.error_classifier import classify_metadata_error  # noqa: E402


def test_resolve_chat_endpoint_basic_cases() -> None:
    resolve = openrouter_api._resolve_chat_endpoint
    assert resolve(None) == openrouter_api.API_ENDPOINT
    assert resolve("") == openrouter_api.API_ENDPOINT
    assert resolve("   ") == openrouter_api.API_ENDPOINT
    assert resolve("https://host/v1") == "https://host/v1/chat/completions"
    assert resolve("https://host/v1/") == "https://host/v1/chat/completions"
    assert resolve("https://host") == "https://host/chat/completions"
    assert (
        resolve("https://host/v1/chat/completions")
        == "https://host/v1/chat/completions"
    )
    assert (
        resolve("https://host/v1/chat/completions/")
        == "https://host/v1/chat/completions"
    )


def test_resolve_chat_endpoint_preserves_query_and_fragment() -> None:
    """Query strings and fragments must survive the normalisation step."""
    resolve = openrouter_api._resolve_chat_endpoint
    # Bare base URL with a key= query string (Azure-style auth via query)
    assert (
        resolve("https://host/v1?api-version=2024")
        == "https://host/v1/chat/completions?api-version=2024"
    )
    # Already-final chat URL with a query string
    assert (
        resolve("https://host/v1/chat/completions?api-version=2024")
        == "https://host/v1/chat/completions?api-version=2024"
    )
    # Path with fragment (rare but valid)
    assert (
        resolve("https://host/v1#frag")
        == "https://host/v1/chat/completions#frag"
    )


def test_resolve_chat_endpoint_does_not_match_chat_completions_in_middle() -> None:
    """``/chat/completions`` mid-path must NOT short-circuit normalisation."""
    resolve = openrouter_api._resolve_chat_endpoint
    # Hypothetical proxy that mounts the OpenAI surface under /api/.
    out = resolve("https://host/v1/chat/completions/extra")
    assert out == "https://host/v1/chat/completions/extra/chat/completions", out


def test_custom_provider_threads_base_url() -> None:
    """`provider_manager.get_metadata` must forward the override + model."""
    captured: dict = {}

    def fake_get_openrouter_metadata(image_path, api_key, stop_event, **kwargs):
        captured["image_path"] = image_path
        captured["api_key"] = api_key
        captured.update(kwargs)
        return {
            "title": "ok",
            "description": "ok",
            "tags": ["alpha", "beta"],
            "as_category": "",
            "ss_category": "",
        }

    original = openrouter_api.get_openrouter_metadata
    openrouter_api.get_openrouter_metadata = fake_get_openrouter_metadata
    try:
        result = provider_manager.get_metadata(
            provider=provider_manager.PROVIDER_CUSTOM,
            image_path="/tmp/dummy.jpg",
            api_key="sk-test",
            stop_event=threading.Event(),
            selected_model="my-org/my-model",
            base_url_override="https://example.test/v1",
        )
    finally:
        openrouter_api.get_openrouter_metadata = original

    assert isinstance(result, dict), result
    assert result.get("title") == "ok", result
    assert captured["base_url_override"] == "https://example.test/v1", captured
    assert captured["selected_model_input"] == "my-org/my-model", captured


def test_custom_provider_without_base_url_returns_error() -> None:
    result = provider_manager.get_metadata(
        provider=provider_manager.PROVIDER_CUSTOM,
        image_path="/tmp/dummy.jpg",
        api_key="sk-test",
        stop_event=threading.Event(),
        selected_model="my-org/my-model",
        base_url_override="",
    )
    assert isinstance(result, dict) and result.get("error") == "custom_provider_no_base_url", result


def test_custom_provider_without_model_returns_error() -> None:
    result = provider_manager.get_metadata(
        provider=provider_manager.PROVIDER_CUSTOM,
        image_path="/tmp/dummy.jpg",
        api_key="sk-test",
        stop_event=threading.Event(),
        selected_model="",
        base_url_override="https://example.test/v1",
    )
    assert isinstance(result, dict) and result.get("error") == "custom_provider_no_model", result


def test_check_api_keys_status_dispatches_custom_to_openrouter() -> None:
    """Dispatcher must call openrouter_api.check_api_keys_status with the
    override even though _PROVIDERS["Custom"]["module"] is None.

    This guards the previous regression where the ``module is None`` guard
    fired before the Custom branch and short-circuited every key to
    "No module for this provider".
    """
    captured: dict = {}

    def fake_check(api_keys, model=None, base_url_override=None):
        captured["api_keys"] = list(api_keys)
        captured["model"] = model
        captured["base_url_override"] = base_url_override
        return {key: (200, "OK") for key in api_keys}

    original = openrouter_api.check_api_keys_status
    openrouter_api.check_api_keys_status = fake_check
    try:
        result = provider_manager.check_api_keys_status(
            provider_manager.PROVIDER_CUSTOM,
            ["sk-test"],
            model="my-model",
            base_url_override="https://example.test/v1",
        )
    finally:
        openrouter_api.check_api_keys_status = original

    assert result == {"sk-test": (200, "OK")}, result
    assert captured["base_url_override"] == "https://example.test/v1", captured
    assert captured["model"] == "my-model", captured
    assert captured["api_keys"] == ["sk-test"], captured


def test_check_api_keys_status_custom_without_base_url_short_circuits() -> None:
    result = provider_manager.check_api_keys_status(
        provider_manager.PROVIDER_CUSTOM,
        ["sk-1", "sk-2"],
        model="my-model",
        base_url_override="",
    )
    assert all(status == -1 for status, _ in result.values()), result
    assert all("Base URL" in msg for _, msg in result.values()), result


def test_classify_metadata_error_demotes_config_errors() -> None:
    """Structural/config errors must not be classified as retryable failures.

    They map to the non-retryable ``failed_config`` status so the auto-retry
    loop does not burn 5 attempts on errors the user has to fix manually.
    """
    assert classify_metadata_error("custom_provider_no_base_url") == "failed_config"
    assert classify_metadata_error("custom_provider_no_model") == "failed_config"
    assert classify_metadata_error("openrouter_no_model") == "failed_config"
    # Non-structural errors keep retry semantics.
    assert classify_metadata_error("http_500") == "failed_api"
    assert classify_metadata_error("invalid_json") == "failed_api"
    assert classify_metadata_error("openrouter_max_retries") == "failed_api"


def test_failed_config_is_non_retryable() -> None:
    """``failed_config`` must be in NON_RETRYABLE_STATUSES.

    We don't import ``batch_processing`` directly because that module pulls
    runtime-only dependencies (cv2, portalocker, etc.). Instead we read the
    file and assert on the static set membership.
    """
    bp_path = PROJECT_ROOT / "src" / "processing" / "batch_processing.py"
    source = bp_path.read_text(encoding="utf-8")
    # Locate the NON_RETRYABLE_STATUSES literal and assert failed_config is in it.
    marker = "NON_RETRYABLE_STATUSES = {"
    idx = source.find(marker)
    assert idx != -1, "NON_RETRYABLE_STATUSES literal not found"
    end = source.find("}", idx)
    block = source[idx:end]
    assert '"failed_config"' in block, block


def test_openrouter_request_uses_override() -> None:
    """End-to-end smoke: HTTP call lands on the overridden host."""
    captured_url: list[str] = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"title":"t","description":"d",'
                                '"keywords":["k1","k2"],'
                                '"adobe_stock_category":"",'
                                '"shutterstock_category":""}'
                            )
                        }
                    }
                ]
            }

        @property
        def text(self):
            return ""

    def fake_post(url, headers=None, json=None, timeout=None, **_):
        captured_url.append(url)
        return FakeResponse()

    original_encode = openrouter_api._encode_image
    original_validate = openrouter_api._validate_images
    original_post = openrouter_api.requests.post
    openrouter_api._encode_image = lambda path: ("ZmFrZQ==", "image/jpeg")
    openrouter_api._validate_images = lambda images: (True, None)
    openrouter_api.requests.post = fake_post
    try:
        result = openrouter_api.get_openrouter_metadata(
            image_path="C:/fake/path.jpg",
            api_key="sk-test",
            stop_event=threading.Event(),
            selected_model_input="my-model",
            base_url_override="https://example.test/v1",
        )
    finally:
        openrouter_api._encode_image = original_encode
        openrouter_api._validate_images = original_validate
        openrouter_api.requests.post = original_post

    assert isinstance(result, dict) and "error" not in result, result
    assert captured_url, "no HTTP call captured"
    assert captured_url[0] == "https://example.test/v1/chat/completions", captured_url


# ---------------------------------------------------------------------------
# Direct-execution entrypoint (so this file works with both `pytest` and
# `python tests/api/test_custom_provider_smoke.py`). pytest picks up the
# `test_*` functions automatically.
# ---------------------------------------------------------------------------
def main() -> int:
    cases = [
        ("resolve_chat_endpoint basic", test_resolve_chat_endpoint_basic_cases),
        ("resolve_chat_endpoint preserves query/fragment", test_resolve_chat_endpoint_preserves_query_and_fragment),
        ("resolve_chat_endpoint mid-path", test_resolve_chat_endpoint_does_not_match_chat_completions_in_middle),
        ("custom provider threads base_url", test_custom_provider_threads_base_url),
        ("custom provider missing base_url", test_custom_provider_without_base_url_returns_error),
        ("custom provider missing model", test_custom_provider_without_model_returns_error),
        ("check_api_keys_status dispatches Custom", test_check_api_keys_status_dispatches_custom_to_openrouter),
        ("check_api_keys_status Custom missing URL", test_check_api_keys_status_custom_without_base_url_short_circuits),
        ("classify_metadata_error demotion", test_classify_metadata_error_demotes_config_errors),
        ("failed_config is non-retryable", test_failed_config_is_non_retryable),
        ("openrouter request uses override", test_openrouter_request_uses_override),
    ]
    for label, fn in cases:
        fn()
        print(f"PASS: {label}")
    print("\nAll custom-provider smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

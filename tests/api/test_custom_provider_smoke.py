# RJ Auto Metadata
# Copyright (C) 2026 Riiicil
#
# Smoke test for custom-provider base_url plumbing.
"""Verify that ``base_url_override`` is threaded end-to-end.

This test does not hit the network. It monkeypatches
``openrouter_api.get_openrouter_metadata`` to record the kwargs it receives
when invoked through ``provider_manager.get_metadata`` for the Custom
provider, and also asserts the openrouter request endpoint is rebuilt from
the override.
"""
from __future__ import annotations

import os
import sys
import threading
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.api import openrouter_api, provider_manager  # noqa: E402


def test_custom_provider_threads_base_url() -> None:
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
    print("PASS: custom provider forwards base_url_override and model")


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
    print("PASS: missing base_url short-circuits with custom_provider_no_base_url")


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
    print("PASS: missing model short-circuits with custom_provider_no_model")


def test_resolve_chat_endpoint() -> None:
    resolve = openrouter_api._resolve_chat_endpoint
    assert resolve(None) == openrouter_api.API_ENDPOINT
    assert resolve("") == openrouter_api.API_ENDPOINT
    assert resolve("   ") == openrouter_api.API_ENDPOINT
    assert resolve("https://host/v1") == "https://host/v1/chat/completions"
    assert resolve("https://host/v1/") == "https://host/v1/chat/completions"
    assert (
        resolve("https://host/v1/chat/completions")
        == "https://host/v1/chat/completions"
    )
    assert (
        resolve("https://host/v1/chat/completions/")
        == "https://host/v1/chat/completions"
    )
    print("PASS: _resolve_chat_endpoint normalises bare base URLs and full chat URLs")


def test_openrouter_request_uses_override(monkeypatch_dummy=None) -> None:
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

    # Patch encode + requests.post so we don't read disk or hit network.
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

    assert isinstance(result, dict), result
    assert "error" not in result, result
    assert captured_url, "no HTTP call captured"
    assert captured_url[0] == "https://example.test/v1/chat/completions", captured_url
    print(f"PASS: openrouter posted to overridden URL {captured_url[0]}")


def main() -> int:
    test_resolve_chat_endpoint()
    test_custom_provider_threads_base_url()
    test_custom_provider_without_base_url_returns_error()
    test_custom_provider_without_model_returns_error()
    test_openrouter_request_uses_override()
    print("\nAll custom-provider smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

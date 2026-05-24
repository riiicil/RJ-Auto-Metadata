# RJ Auto Metadata
# Copyright (C) 2026 Riiicil
"""Helpers for translating provider-level error codes into pipeline statuses.

Kept in a small dependency-free module so it can be imported from both the
batch orchestrator and the per-format workers without forming an import
cycle with ``src.processing.batch_processing``.
"""
from __future__ import annotations

# Provider-level error codes that mean "user/config mistake" rather than a
# transient API failure. Bursting through 5 retries on these only delays the
# inevitable failure and burns rate-limit / connection budget.
NON_RETRYABLE_ERROR_CODES = frozenset({
    "custom_provider_no_base_url",
    "custom_provider_no_model",
    "openrouter_no_model",
})


def classify_metadata_error(error_code: str) -> str:
    """Map an error code from ``provider_manager.get_metadata`` to a
    pipeline status string. Structural/config errors are demoted to
    ``failed_config`` (non-retryable); everything else is ``failed_api``.
    """
    if error_code in NON_RETRYABLE_ERROR_CODES:
        return "failed_config"
    return "failed_api"

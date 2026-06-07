# Current State — RJ Auto Metadata

> Snapshot at iLabs Integration & Space Preservation (v3.12.3) completion.

## Version

**3.12.3**

## Branch Structure

- `main` — stable release baseline (v3.11.3)
- `dev` — integration branch (Phase 4A complete at `115b3fd`)
- `task/docs-governance` — Phase 0 work branch (merged to dev)
- `task/refactor-backend` — Phase 1 work branch (merged to dev)
- `task/refactor-ui` — Phase 2 work branch (merged to dev)
- `task/add-providers` — Phase 4A work branch (merged to dev)
- `task/dynamic-prompt-builder` — Phase 4B work branch (merged to dev)
- `task/wire-advanced-params` — Phase 4C Step 3 work branch (merged to dev)
- `kaine-na:task/fix-custom-provider-base-url` — Phase 4E work branch (merged to main via PR #4)
- `task/integrate-ilabs-and-fix-spaces` — iLabs Integration and Spaces Fix (current work branch)

## Supported Providers

| Provider | Endpoint Type | Status |
|---|---|---|
| **Gemini** | OpenAI compat (`v1beta/openai/`) | Migrated in Phase 1 |
| **OpenAI** | Responses API (`/v1/responses`) | Unchanged |
| **OpenRouter** | Chat Completions | Unchanged |
| **Groq** | Chat Completions | Unchanged |
| **KoboiLLM** | Chat Completions | Unchanged |
| **Mistral** | OpenAI compat (`/v1`) | Added in Phase 4A |
| **Blackbox** | OpenAI compat (`/`) | Added in Phase 4A |
| **iLabs** | OpenAI compat (`/v1`) | Added in Phase 4F |
| **Custom** | User-defined base URL | Added in Phase 1, UI added in Phase 2, fully wired in Phase 4E |

## Technical Debt Resolved in Phase 1

- **Hardcoded model presets**: Removed from all 5 `*_api.py` files; `get_model_choices()` / `get_default_model()` stubbed for UI compat
- **Gemini native REST**: Replaced ~770-line SDK/REST dual path with ~300-line OpenAI SDK implementation
- **Duplicate `_clean_json_text()`**: Centralized to `src/utils/json_utils.py`; removed from `openai_api.py`, `openrouter_api.py`, `koboillm_api.py`
- **Gemini Auto Rotation**: Removed entirely (model rotation logic, cooldowns, locks)
- **Dead code**: Removed `calculate_smart_delay()`, `DEBUG_FORCE_FAILURE`, commented-out debug blocks
- **Noisy terminal output**: Added `_TERMINAL_PRINT_TAGS` filter — only warning/error/critical/success print to terminal
- **Duplicate `gpt-4o`**: Fixed in `_STRUCTURED_OUTPUT_MODEL_PREFIXES`
- **`PROVIDER_BASE_URLS`**: Added to `provider_manager.py` with all 6 provider URLs
- **Custom provider**: Added as 6th provider with `base_url_override` dispatch

## Changes in Phase 2

- **Load & Delete buttons**: Removed from UI; dead methods `_load_api_keys`, `_save_api_keys`, `_delete_selected_api_key`, `_toggle_api_key_visibility` removed
- **Auto Retry**: Switch removed from UI; `auto_retry_var` hardcoded to `True`
- **Save → Fetch**: Save button renamed to Fetch; wired to `_fetch_models()` with threaded model fetch
- **Base URL field**: Added, visible only when Custom provider is selected
- **Per-provider model state**: `_models_by_provider` dict tracks cached model lists per provider
- **Custom in dropdown**: "Custom" now appears in provider dropdown on startup
- **Settings persistence**: `models_by_provider` and `custom_base_url` saved/restored in config.json
- **`fetch_models()` stub**: Added to `provider_manager.py` — returns `[]`, real implementation deferred to Phase 3

## Changes in Phase 3

- **`fetch_models()` implemented**: Real implementation using OpenAI SDK `client.models.list()` for all providers; filters non-generative models (embeddings, tts, whisper, dall-e, legacy completions)
- **CTkScrollableDropdown**: Vendored Akascape/CTkScrollableDropdown (MIT) into `src/ui/CTkScrollableDropdown/`; attached to all 5 CTkComboBox dropdowns for scrollable popup behavior; `command` callbacks passed through for provider and theme
- **Per-provider key/model sync**: `_on_provider_change` now syncs textbox → `_actual_api_keys` before persisting; API keys, model list, URL field, and selected model all switch correctly when changing provider
- **Per-provider model selection**: `_selected_model_by_provider` dict tracks last-selected model per provider; persisted in `config.json`; restored on launch and provider switch
- **Readonly dropdowns**: All 5 CTkComboBox set to `state='readonly'` to prevent manual text entry
- **Auto-fetch models**: On app launch and provider switch, models are auto-fetched in background if API keys exist; silent skip when no keys (first use)

## Changes in Phase 4A

- **Model dropdown clear fix**: `_refresh_provider_models()` now clears `model_var` + dropdown display when the selected provider has no cached models
- **Mistral provider**: Added `src/api/mistral_api.py` using OpenAI-compatible endpoint `https://api.mistral.ai/v1`
- **Blackbox provider**: Added `src/api/blackbox_api.py` using OpenAI-compatible endpoint `https://api.blackbox.ai`
- **Provider registration**: Added Mistral + Blackbox to `provider_manager.py` constants, `PROVIDER_BASE_URLS`, `_PROVIDERS`, and `get_metadata()` dispatch

## Changes in Phase 4B

- **Dynamic prompt builder**: Refactored `src/api/prompts.py` from 18 hardcoded prompt strings to 2 builder functions (`_build_gemini_prompt()`, `_build_openai_prompt()`) plus `_PRIORITY_PARAMS`
- **`select_prompt()` extension**: Added `user_hint=""` and `custom_instruction=""` parameters while keeping existing `*_api.py` call sites unchanged (backward-compatible defaults)
- **Title safety net**: Added `_sanitize_title_length()` in `src/api/provider_manager.py` to hard-truncate overlong titles to 200 chars after keyword fill

## Changes in Phase 4B.5

- **Stop mechanism refactored**: Created `src/utils/stop_flag.py` as single source of truth for the global stop flag
- **Per-module flags removed**: Removed `FORCE_STOP_FLAG` / `_force_stop`, `set_force_stop()`, `reset_force_stop()`, `is_stop_requested()` from all 7 `*_api.py` files
- **Centralized import**: Each `*_api.py` now imports `is_stop_requested` from `stop_flag`; `check_stop_event()` kept per-module (uses `stop_event` threading.Event)
- **provider_manager delegation**: `set_force_stop()`, `reset_force_stop()`, `is_stop_requested()` now delegate directly to `stop_flag` module
- **Infrastructure imports**: `compression.py` and `exif_writer.py` import `is_stop_requested` from `stop_flag` instead of `gemini_api`
- **UI stop imports**: All `app.py` imports of `set_force_stop`/`reset_force_stop` from `gemini_api` replaced with `stop_flag` imports
- **Premature UI reset fix**: `_check_thread_ended()` timeout increased from 2.5s to 30s
- **Separated UI reset from stop flag reset**: Added `_reset_ui_buttons_only()` — resets UI without clearing stop flag; `reset_force_stop()`/`stop_event.clear()` only called when thread is confirmed dead

## Changes in Phase 4C (UI Tab Settings)

- **Section headers removed**: Removed "Folder Input/Output" header+tooltip, "Settings and API Keys" header+tooltip, and "Logs" label from the UI to reclaim vertical space
- **Settings tabview**: Replaced `settings_row` CTkFrame with `CTkTabview` containing "Settings" and "Advanced" tabs
- **Settings tab**: Existing 3×3 settings grid (Keywords/Workers/Delay, Theme/Quality/Embed, Rename/Category/Foldering) moved into "Settings" tab unchanged
- **Advanced tab**: Blank placeholder tab added with "coming soon" label for future prompt customization
- **Window size**: Default geometry reduced from 600×800 to 600×700

## Changes in Phase 4C Step 2 (Advanced Tab Content)

- **Advanced tab layout**: Replaced placeholder with Option B 3-column layout:
  - Col 0: Instructions textarea (CTkTextbox, full height via rowspan, stretches horizontally)
  - Col 1: Hint entry + Inject Keywords entry (sub-frame matching Settings tab style)
  - Col 2: Title min/max + Desc min/max limit entries (compact sub-frames)
- **New StringVars**: Added 7 variables — `hint_var`, `custom_instruction_var`, `inject_keywords_var`, `title_min_words_var`, `title_max_chars_var`, `desc_min_words_var`, `desc_max_chars_var`
- **Config persistence**: All 7 new vars saved/loaded in `_save_settings()`/`_load_settings()` with sensible Detailed-preset defaults
- **No backend wiring**: Values are UI-only; passing to `batch_processing` is Phase 4C Step 3

## Changes in Phase 4C Step 3 (Wire Advanced Params)

- **`select_prompt()` extension**: Added `min_words_override` and `max_chars_override` parameters; when > 0, override the preset values from `_PRIORITY_PARAMS`
- **Thread-local prompt overrides**: Added `_set_prompt_overrides()` / `_clear_prompt_overrides()` in `prompts.py` using `threading.local()`; allows `process_single_file()` to inject Advanced tab values into `select_prompt()` without modifying format processors or `*_api.py` callers
- **`prompt_config` dict**: Built in `app.py` `_run_processing()` from 7 Advanced tab StringVars; threaded through `batch_process_files()` → `process_single_file()` via executor.submit
- **Inject keywords post-processing**: User-specified keywords prepended to LLM result tags in `process_single_file()`, respecting `keyword_count` limit; affects CSV output
- **"Custom" Quality Dropdown Option**: Added `"Custom"` to `self.available_priorities` and the Settings tab Quality combobox.
- **Dynamic Advanced Tab Entry Sync and Locking**: Implemented dynamic synchronization (`_on_quality_change()`). Setting the Quality dropdown to `"Detailed"`, `"Balanced"`, or `"Less"` automatically overwrites the min/max limits in the Advanced tab with preset defaults and disables the entry fields (read-only). Selecting `"Custom"` unlocks the fields for direct editing, while preserving custom inputs.
- **Advanced Field Protection**: Updated `_disable_ui_during_processing()` and `_reset_ui_after_processing()` to lock all Advanced tab fields (textbox, entries) during processing and restore them properly afterwards.
- **Phase 4C fully complete**: All Advanced tab values now flow from UI to processing pipeline with full preset and custom sync.

## Changes in Phase 4D (Hotfix — Mistral & Blackbox Keyword Bug)

- **Mistral keyword bug fixed**: `get_mistral_metadata()` now sends a system message enforcing JSON-only output, appends an explicit keyword-count instruction to the user prompt, uses `response_format={"type": "json_object"}`, raises `max_tokens` from 1024 to 2048, and remaps `"keywords"` → `"tags"` in the returned dict so downstream consumers find the correct key.
- **Blackbox keyword bug fixed**: Same changes applied to `get_blackbox_metadata()`. The `response_format` parameter is wrapped in a try/except that retries without it if the provider does not support it.
- **Fallback no longer triggered**: Before this fix, `provider_manager._fill_keywords_if_short()` found zero tags and replaced them with words split from the title/description. After the fix, the correct array is returned under `"tags"` and the fallback is bypassed.
- **Version Bumped to 3.12.1**: Bumped version from 3.12.0 to 3.12.1 across the codebase.

## Changes in Phase 4E (Hotfix — Custom Provider End-to-End)

- **Root cause 1 fixed**: `app.py` `_custom_base_url_var` was never forwarded to the worker pipeline. The `base_url_override` value now threads through `batch_process_files()` → `process_single_file()` → all format processors (`format_jpg_jpeg_processing.py`, `format_png_processing.py`, `video_processing.py`, `batch_processing.py` vector path).
- **Root cause 2 fixed**: `openrouter_api.py` was hardcoded to `API_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"` even when a `base_url_override` was supplied. Added `_resolve_chat_endpoint()` helper using `urllib.parse.urlsplit` that normalises any base URL to the correct chat-completions endpoint.
- **API key check fixed**: `_cek_api_keys()` in `app.py` now reads `_custom_base_url_var` and passes it through `check_api_keys_status()` → `provider_manager.check_api_keys_status()` → `openrouter_api.check_api_keys_status()`.
- **Early model guard**: `provider_manager.get_metadata()` and `openrouter_api.get_openrouter_metadata()` now return `{"error": "custom_provider_no_model"}` immediately when no model is selected for Custom, instead of silently falling back to `openai/gpt-4.1`.
- **OpenRouter headers isolated**: `HTTP-Referer` and `X-Title` headers are skipped when `base_url_override` is active.
- **New `src/processing/error_classifier.py`**: Dependency-free helper mapping config error codes (`custom_provider_no_base_url`, `custom_provider_no_model`, `openrouter_no_model`) to `failed_config` non-retryable status; prevents burning 5 retry rounds on user config mistakes.
- **New `tests/api/test_custom_provider_smoke.py`**: 11 smoke tests covering endpoint resolution, threaded override, missing-URL/model guards, dispatcher routing, error-classifier demotion, and end-to-end URL correctness. No network required.
- **Version bumped to 3.12.2**.

## Changes in Phase 4F (iLabs & Keyword Spaces)

- **iLabs Provider Integration**: Integrated support for iLabs as a new OpenAI-compatible AI gateway provider. Created `src/api/ilabs_api.py` and registered it in `provider_manager.py`. It is automatically dynamically loaded into the UI dropdown.
- **Keyword Space Preservation**: Removed the space-stripping block inside `provider_manager.py`s `_fill_keywords_if_short()` -> `add_tag()`. Multi-word keywords (e.g., `"railway station"`) are now correctly preserved with spaces intact, affecting both EXIF and CSV output.
- **New `tests/api/test_ilabs_and_spaces.py`**: Added unit tests validating that iLabs is listed under registered providers, and asserting that spaces in multi-word keywords are not stripped during processing.
- **Version bumped to 3.12.3**.

## Remaining Technical Debt

- **Vision model filtering**: Basic prefix filter applied; no vision-specific detection yet
- **Live-provider validation**: Mistral and Blackbox routing is wired, but real-key verification depends on available API credits

## Pending Phases

- Final integration testing across all providers, merge `dev` → `main`, tag new release

## Last Verified Working

- **Version**: 3.11.3
- **Platform**: Windows
- **Entry point**: `python main.py`

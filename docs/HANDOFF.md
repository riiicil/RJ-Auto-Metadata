# Handoff — RJ Auto Metadata

> Continuity document for agent sessions. Read this to resume work without full chat history.

## Versioning Clarification — v3.12.1 vs "v4"

> **For future agent sessions:** The governance docs (ROADMAP.md, ARCHITECTURE.md, CURRENT_STATE.md) reference a "v4 refactor" milestone. This refers to the *architectural* refactoring described in docs/CODEBASE_ANALYSIS.md — splitting app.py, unifying the API base class, decoupling batch processing, etc.
>
> **It does NOT mean the next release is numbered v4.**
>
> The release shipped from the dev branch in May 2026 is **v3.12.1** — a significant feature and refactoring release (multi-provider, Advanced tab, stop mechanism, prompt system overhaul) but one that does not yet complete the full architectural normalization.
>
> **v3.12.2** (May 2026) is a hotfix release that makes the Custom provider fully functional end-to-end (PR #4 by `kaine-na`).
>
> **v3.12.3** (June 2026) is a feature and bugfix release integrating the iLabs OpenAI-compatible provider and resolving the keyword space-stripping bug in the metadata generation pipeline.
>
> The "v4" label in docs = future architectural goal, not the next version number on the release page.

## Phase 0 Status: Complete

### What Was Done

- Updated `.gitignore` — added `logs`, `api_jikaperlu/`, `*.env`, `.env*`, `.env.local`
- Created `dev` branch from `main` as integration baseline
- Created `task/docs-governance` branch from `dev`
- Created `AGENTS.md` at repository root
- Created documentation files in `docs/`

## Phase 1 Status: Complete

### What Was Done

- **B1+B5**: Rewrote `gemini_api.py` — replaced ~770-line SDK/REST dual path + auto-rotation with ~300-line OpenAI SDK implementation using `v1beta/openai/` compat endpoint
- **B2**: Removed commented-out debug blocks from `openai_api.py`, `openrouter_api.py`, `groq_api.py`
- **B3**: Removed all hardcoded model presets (`*_MODEL_PRESETS`, `*_MODELS`, `DEFAULT_MODEL`) from all 5 provider files
- **B4**: Centralized `_clean_json_text()` to `src/utils/json_utils.py`; replaced local copies in `openai_api.py`, `openrouter_api.py`, `koboillm_api.py`
- **B6**: Added `PROVIDER_BASE_URLS` dict to `provider_manager.py` with all 6 provider URLs
- **B7+B8**: Added `PROVIDER_CUSTOM` and Custom provider entry to `_PROVIDERS`; added `base_url_override` parameter to `get_metadata()` dispatch; guarded all module calls against `None` for Custom
- **B9**: Fixed duplicate `gpt-4o` in `_STRUCTURED_OUTPUT_MODEL_PREFIXES` in `openai_api.py`
- **U1**: Added `_TERMINAL_PRINT_TAGS` filter to `src/utils/logging.py` — only warning/error/critical/success print to terminal
- **U2**: Created `src/utils/json_utils.py` with shared `_clean_json_text()`

### What Is NOT Done / Deferred to Phase 2

- `get_model_choices()` and `get_default_model()` in `provider_manager.py` are **stubbed** (return empty list / empty string) to avoid breaking `app.py` — Phase 2 will add Fetch button and dynamic model loading
- `app.py` was **not modified** — UI still references old model dropdown flow
- Auto Retry toggle still exists in UI — Phase 2 will hardcode `True` and remove toggle

## Phase 2 Status: Complete

### What Was Done

- **UI-1**: Removed Load and Delete buttons; removed dead methods `_load_api_keys`, `_save_api_keys`, `_delete_selected_api_key`, `_toggle_api_key_visibility`
- **UI-2**: Hardcoded `auto_retry_var` to `True`; removed Auto Retry switch from layout
- **UI-3**: Renamed Save button → Fetch; added `_fetch_models()` with threaded model fetch and `_apply_fetched_models()`; added `fetch_models()` stub to `provider_manager.py`
- **UI-4**: Added Base URL entry field, visible only when Custom provider is selected; added `_update_base_url_visibility()` method
- **UI-5**: Added `_models_by_provider` dict for per-provider model state; updated `_refresh_provider_models()` to use cached models
- **UI-6**: Added "Custom" to `available_providers` list on startup
- **UI-7**: Persisted `models_by_provider` and `custom_base_url` in config.json via `_save_settings()` / `_load_settings()`

### What Is NOT Done / Deferred to Phase 3

- `fetch_models()` in `provider_manager.py` is a **stub** (returns `[]`) — Phase 3 implements real `GET /v1/models` API calls
- Vision model filtering not implemented — deferred to Phase 3

## Phase 3 Status: Complete

### What Was Done

- **fetch_models()**: Replaced stub with real implementation using OpenAI SDK `client.models.list()` endpoint; resolves base URL from `PROVIDER_BASE_URLS` for built-in providers or user-supplied URL for Custom; filters non-generative model IDs via `_SKIP_PREFIXES`
- **CTkScrollableDropdown**: Vendored Akascape/CTkScrollableDropdown (MIT) into `src/ui/CTkScrollableDropdown/`; attached to all 5 CTkComboBox dropdowns for scrollable popup behavior; `command` callbacks passed through for provider and theme
- **Per-provider key sync**: `_on_provider_change` now syncs textbox before persisting; API keys, model list, URL, and selected model all switch correctly on provider change
- **Per-provider model selection**: `_selected_model_by_provider` dict persisted in `config.json`; model restored on launch and provider switch
- **Readonly dropdowns**: All 5 CTkComboBox set to `state='readonly'`
- **Auto-fetch models**: `_auto_fetch_models()` runs on startup (500ms delay) and on provider switch; silently skips if no keys

### What Is NOT Done / Deferred

- Vision-specific model detection not implemented (basic prefix filter only)

## Phase 4A Status: Complete

### What Was Done

- **UI bug fix**: `_refresh_provider_models()` now clears the model display (`model_var` + dropdown text) when selected provider has no cached models
- **Provider add**: Created `src/api/mistral_api.py` (OpenAI-compatible, base URL `https://api.mistral.ai/v1`, public entry `get_mistral_metadata`)
- **Provider add**: Created `src/api/blackbox_api.py` (OpenAI-compatible, base URL `https://api.blackbox.ai`, public entry `get_blackbox_metadata`)
- **Provider registry**: Updated `src/api/provider_manager.py` with `PROVIDER_MISTRAL` and `PROVIDER_BLACKBOX` constants, added both to `PROVIDER_BASE_URLS`, `_PROVIDERS`, and `get_metadata()` dispatch routing

## Phase 4B Status: Complete

### What Was Done

- **Prompt refactor**: Replaced 18 hardcoded prompt string variants in `src/api/prompts.py` with dynamic builders (`_build_gemini_prompt()`, rewritten `_build_openai_prompt()`) and `_PRIORITY_PARAMS`
- **Prompt entry point update**: Extended `select_prompt()` signature with `user_hint=""` and `custom_instruction=""` while preserving existing `*_api.py` call compatibility
- **Provider safety guard**: Added `_sanitize_title_length()` in `src/api/provider_manager.py` and chained it after `_fill_keywords_if_short()` for all provider return paths

### Notes for Next Phase (4C)

- No UI changes in Phase 4B; `user_hint` and `custom_instruction` are wired at API prompt builder level but currently always empty (`""`) from existing UI flows
- Groundwork is ready for Phase 4C UI additions: Image Hint field, Custom Instructions field, Specific Keywords support, and Custom Quality settings

### Validation Notes

- Import and provider-list checks pass (`provider_manager.list_providers()` includes Mistral and Blackbox)
- UI launch/routing confirmed against provider docs and configured base URLs
- Real API-key execution for Mistral and Blackbox not validated due unavailable key credits in this session

## Phase 4B.5 Status: Complete

### What Was Done

- **Stop flag centralization**: Created `src/utils/stop_flag.py` as single source of truth for global stop flag (`_FORCE_STOP` bool with `is_stop_requested()`, `set_force_stop()`, `reset_force_stop()`)
- **Per-module flag removal**: Removed `FORCE_STOP_FLAG`/`_force_stop`, `set_force_stop()`, `reset_force_stop()`, `is_stop_requested()` from all 7 `*_api.py` files (gemini, openai, openrouter, groq, koboillm, mistral, blackbox)
- **Import update**: Each `*_api.py` now imports `is_stop_requested` from `stop_flag`; `check_stop_event()` kept in each module (uses threading.Event)
- **provider_manager simplification**: `set_force_stop()`, `reset_force_stop()`, `is_stop_requested()` now delegate to `stop_flag` directly instead of iterating all provider modules
- **Infrastructure import fix**: `compression.py` and `exif_writer.py` import `is_stop_requested` from `stop_flag` instead of `gemini_api`
- **app.py stop import fix**: All `gemini_api` stop imports replaced with `stop_flag` imports
- **Premature UI reset fix**: `_check_thread_ended()` timeout increased from 2.5s to 30s
- **UI/stop separation**: Added `_reset_ui_buttons_only()` — resets UI controls without clearing stop flag; `reset_force_stop()`/`stop_event.clear()` only happen when thread is confirmed dead

### Bug Fixed

The original stop mechanism had two bugs:
1. Each provider had its own independent stop flag — stopping one didn't affect others
2. `_check_thread_ended()` had a 2.5s timeout that reset the stop flag while threads were still alive, causing them to continue after the user clicked Stop

Both are now resolved by the single centralized flag and the separated UI/stop-state reset.

## Phase 4C Status: Complete (UI Tab Settings)

### What Was Done

- **Section header removal**: Removed "Folder Input/Output" header (tooltip + `_create_header_with_help` call + `.grid()`), "Settings and API Keys" header (same pattern), and "Logs" `CTkLabel` from `_create_log_frame()`
- **Log frame adjustment**: `log_text` promoted to row=0, `grid_rowconfigure` updated accordingly
- **Settings tabview**: Replaced `settings_row` CTkFrame with `self.settings_tabview` (`CTkTabview`) containing "Settings" and "Advanced" tabs
- **Reparenting**: Three settings column frames (`settings_col1`, `settings_col2`, `settings_col3`) reparented from `settings_row` to `settings_tabview.tab("Settings")`
- **Advanced tab placeholder**: Added "Advanced prompt settings — coming soon." label
- **Window size**: Default geometry reduced from 600×800 to 600×700

### Notes for Next Phase

- The `_create_header_with_help()` method itself was intentionally kept — only the two calls and their tooltip strings were removed
- The Advanced tab is ready for Phase 4C content: Image Hint field, Custom Instructions field, Specific Keywords, Custom Quality

## Phase 4C Step 2 Status: Complete (Advanced Tab Content)

### What Was Done

- **Advanced tab layout**: Replaced "coming soon" placeholder with Option B 3-column layout in `_create_combined_api_settings_frame()`
  - Col 0: `instruction_textbox` (CTkTextbox, rowspan=2, syncs to `custom_instruction_var` via KeyRelease/FocusOut)
  - Col 1: `hint_entry` + `inject_kw_entry` in `adv_col1` sub-frame (label+entry pattern matching Settings tab)
  - Col 2: Title min/max + Desc min/max entries in `adv_col2` sub-frame with compact `title_limit_frame`/`desc_limit_frame`
- **New StringVars**: 7 vars added in `__init__`: `hint_var`, `custom_instruction_var`, `inject_keywords_var`, `title_min_words_var`, `title_max_chars_var`, `desc_min_words_var`, `desc_max_chars_var`
- **Config persistence**: All 7 keys added to `_save_settings()` dict and `_load_settings()` with Detailed-preset defaults (min_words=6, max_chars=180)
- **Textbox restore**: `_load_settings()` populates `instruction_textbox` from saved `custom_instruction` value

### What Is NOT Done / Deferred to Phase 4C Step 3

- Backend wiring: passing `hint_var`, `custom_instruction_var`, `inject_keywords_var`, and limit vars to `batch_processing` / `provider_manager.get_metadata()` → `select_prompt()`
- No "Custom" quality option in dropdown (not adding yet)
- No read-only mode for limit fields when a preset quality is selected

## Phase 4C Step 3 Status: Complete (Wire Advanced Params)

### What Was Done

- **`select_prompt()` extension**: Added `min_words_override: int = 0` and `max_chars_override: int = 0` parameters; when > 0, override preset `_PRIORITY_PARAMS` values
- **Thread-local prompt overrides**: Added `threading.local()` based `_set_prompt_overrides()` / `_clear_prompt_overrides()` in `prompts.py`; `select_prompt()` merges thread-local values when explicit params are at defaults — avoids modifying format processors or `*_api.py` callers
- **`prompt_config` dict**: Built in `app.py` `_run_processing()` from 7 Advanced tab StringVars (hint, custom_instruction, inject_keywords, title_min/max, desc_min/max); passed as kwarg through `batch_process_files()` → `process_single_file()` via executor.submit
- **Thread-local set in worker**: `process_single_file()` calls `_set_prompt_overrides(prompt_config)` at entry; format processors → `provider_manager.get_metadata()` → `*_api.get_*_metadata()` → `select_prompt()` picks up overrides via thread-local
- **Inject keywords**: After format processor returns metadata, `process_single_file()` prepends user-specified keywords to `processed_metadata["tags"]`, deduplicates, and respects `keyword_count` limit; affects CSV output
- **"Custom" Quality Option in Settings**: Added `"Custom"` quality option to the Settings tab Quality combobox.
- **Dynamic Advanced Tab Field Sync and Locking**: Implemented an automated hook (`_on_quality_change()`) so that switching between presets ("Detailed", "Balanced", "Less") automatically sets the appropriate min/max limits in the Advanced tab and disables/locks the fields (read-only mode), preventing out-of-sync states. Selecting "Custom" unlocks the fields for user modification.
- **Advanced Field Protection during processing**: Disabled Advanced tab input textboxes, inject keywords entry, and Title/Desc min/max fields during batch processing and fully restored them afterwards with proper locking based on current quality selection.

### What Is NOT Done / Deferred

- Injected keywords do NOT affect EXIF (already written inside format processors before return); only CSV and returned metadata benefit

- `desc_min_words` and `desc_max_chars` are captured in `prompt_config` but not wired to `select_prompt()` (prompt builder uses single min/max for both title and desc)

## Phase 4D Status: Complete (Hotfix — Mistral & Blackbox Keyword Bug)

### What Was Done

- **Root cause confirmed**: Live API test proved that `mistral_api.py` and `blackbox_api.py` 
  shared two bugs: (A) no system message causing the model to respond in Markdown prose instead
  of JSON, and (B) returning the keyword array under the key `"keywords"` instead of `"tags"`,
  causing `provider_manager._fill_keywords_if_short()` to fall back to splitting title/description
  words into keywords — producing 12–15 low-quality keywords instead of the 49–60 expected.
- **Mistral fix**: Added system message enforcing JSON-only output; injected keyword-count
  instruction into user prompt; added `response_format={"type": "json_object"}`; raised
  `max_tokens` from 1024 to 2048; remapped `"keywords"` → `"tags"` in parsed result.
- **Blackbox fix**: Applied same fixes; wrapped `response_format` in try/except with fallback
  retry because Blackbox may not support the parameter.
- **Version Bump**: Bumped application version from `3.12.0` to `3.12.1` in all required locations
  (`src/ui/app.py`, `setup.iss`, `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/HANDOFF.md`, `docs/CURRENT_STATE.md`).

### Validation Notes

- Tested live against Mistral API (`pixtral-12b-2409`) with real key — fixed payload produced
  78 proper AI-generated keywords; `"tags"` key correctly populated; no fallback triggered.
- Blackbox fix is structurally identical; live validation depends on available key credits.

## Phase 4E Status: Complete (Hotfix — Custom Provider End-to-End)

### What Was Done

- **Root cause 1**: `app.py` never forwarded `_custom_base_url_var` to the worker pipeline. `base_url_override` now threads end-to-end through `batch_process_files()` → `process_single_file()` → all format processors.
- **Root cause 2**: `openrouter_api.py` was hardcoded to the OpenRouter endpoint. Added `_resolve_chat_endpoint()` helper that builds the correct chat-completions URL from the user-supplied base URL, using `urllib.parse.urlsplit` (preserves query strings and fragments).
- **API key check**: `_cek_api_keys()` in `app.py` now passes `base_url_override` through the full `check_api_keys_status()` chain for Custom.
- **Early model guard**: Returns `{"error": "custom_provider_no_model"}` immediately when no model is selected, instead of silently falling back to `openai/gpt-4.1`.
- **OpenRouter headers isolated**: `HTTP-Referer` / `X-Title` headers skipped when override is active.
- **New `src/processing/error_classifier.py`**: Maps config error codes to `failed_config` non-retryable status.
- **New `tests/api/test_custom_provider_smoke.py`**: 11 smoke tests (no network).
- **Version bumped to 3.12.2**.

## Phase 4F Status: Complete (iLabs & Keyword Spaces)

### What Was Done

- **iLabs Provider Integration**: Integrated support for iLabs as a new OpenAI-compatible AI gateway provider. Created `src/api/ilabs_api.py` and registered it in `provider_manager.py`. The provider is loaded dynamically into the UI dropdown.
- **Keyword Space Preservation**: Removed the space-stripping block inside `provider_manager.py`'s `_fill_keywords_if_short()` -> `add_tag()`. Multi-word keywords (e.g. `"railway station"`) are now correctly preserved with spaces intact, affecting both EXIF and CSV output.
- **New `tests/api/test_ilabs_and_spaces.py`**: Added unit tests validating that iLabs is listed under registered providers, and asserting that spaces in multi-word keywords are not stripped during processing.
- **Version bumped to 3.12.3**.

## Next Phase

Dev branch has been merged to main and released as **v3.12.0** and hotfixed as **v3.12.1**, **v3.12.2** (May 2026), and **v3.12.3** (June 2026). The next work is the architectural refactoring described in docs/CODEBASE_ANALYSIS.md: splitting app.py into focused modules, creating a unified API base class, decoupling batch processing, and completing the normalization described in docs/ANALISYS_REFACTORING.md.

## Key Decisions Already Made

These decisions are final. Do not re-discuss or change them.

| Decision | Resolution |
|---|---|
| Gemini endpoint | Migrated to OpenAI compat (`v1beta/openai/`) |
| OpenAI endpoint | Stays on Responses API (`/v1/responses`) |
| Model filtering | No filter — fetch all, user decides |
| Gemini Auto Rotation | Removed entirely |
| Custom provider | Added as 6th option; dispatches via openrouter-style handler |
| Auto Retry | Hardcoded `True` in Phase 2, UI toggle removed |
| `_clean_json_text()` | Centralized to `src/utils/json_utils.py` |
| Load/Delete/Save buttons | Removed in Phase 2; replaced with Check + Fetch |
| CTkScrollableDropdown | Vendored (MIT); replaces native CTkComboBox popup |
| fetch_models() | OpenAI SDK `client.models.list()` with prefix filter |

## Important Files

1. `AGENTS.md`
2. `docs/CURRENT_STATE.md`
3. `docs/ARCHITECTURE.md`
4. `src/ui/CTkScrollableDropdown/` — vendored scrollable dropdown widget
5. `src/api/provider_manager.py` — fetch_models() implementation

# Architecture — RJ Auto Metadata

## Application Type

Standalone Python desktop application. No server, no frontend build step. Single-process with threaded batch processing. Launched via `python main.py`.

## Layer Overview

### UI Layer

- **File**: `src/ui/app.py` (~1738 lines)
- **Framework**: CustomTkinter
- **Role**: Single-file GUI — folder selection, API key input, provider/model dropdowns, processing controls, real-time log display
- **Entry class**: `MetadataApp(ctk.CTk)`

### API Layer

- **Directory**: `src/api/`
- **Dispatcher**: `provider_manager.py` — routes requests to the correct provider module, fills keywords if short, handles stop events
- **Provider modules**: One file per provider (`gemini_api.py`, `openai_api.py`, `openrouter_api.py`, `groq_api.py`, `koboillm_api.py`, `mistral_api.py`, `blackbox_api.py`); Custom provider dispatches via `openrouter_api.py` with `base_url_override`

### Processing Layer

- **Directory**: `src/processing/`
- **File**: `src/processing/batch_processing.py`
- **Role**: Threaded batch processor using `concurrent.futures.ThreadPoolExecutor`
- **Sub-processors**: `image_processing/`, `vector_processing/`, `video_processing.py` — format-specific preprocessing before API calls
- **Error classification**: `src/processing/error_classifier.py` — maps provider error codes to non-retryable `failed_config` pipeline status

### Utils

- **Directory**: `src/utils/`
- `logging.py` — log message routing (UI + terminal)
- `file_utils.py` — file discovery, API key reading, directory validation
- `system_checks.py` — ExifTool/Ghostscript/FFmpeg/GTK3 availability checks
- `analytics.py` — anonymous usage analytics via GA Measurement Protocol
- `compression.py` — image compression before API upload

### Config

- **Directory**: `src/config/`
- `config.py` — measurement IDs, API secrets, analytics URL constants
- `constants.py` — app-wide constants

### Metadata

- **Directory**: `src/metadata/`
- `exif_writer.py` — ExifTool integration for embedding metadata into files
- `categories/` — platform-specific category mapping (Adobe Stock, Shutterstock, etc.)

## Provider Table

| Provider | Endpoint | Format |
|---|---|---|
| **Gemini** | `v1beta/openai/` (compat) | OpenAI SDK |
| **OpenAI** | `api.openai.com/v1/responses` | Responses API |
| **OpenRouter** | `openrouter.ai/api/v1/chat/completions` | Chat Completions |
| **Groq** | `api.groq.com/openai/v1/chat/completions` | Chat Completions |
| **KoboiLLM** | `litellm.koboi2026.biz.id/chat/completions` | Chat Completions |
| **Mistral** | `api.mistral.ai/v1` | OpenAI compat |
| **Blackbox** | `api.blackbox.ai` | OpenAI compat |
| **Custom** | User-defined base URL | OpenAI compat (via `openrouter_api` + `base_url_override`) |

## Request Flow

```
User
  │
  ▼
UI (app.py)
  │  _run_processing() → batch_process_files()
  ▼
batch_processing.py
  │  ThreadPoolExecutor → per-file worker
  ▼
provider_manager.py
  │  get_metadata() → dispatch by provider_key
  ▼
*_api.py (provider module)
  │  Build request → POST to API endpoint
  ▼
AI API Endpoint
  │  Response JSON
  ▼
*_api.py
  │  Parse response → extract title/description/tags
  ▼
provider_manager.py
  │  _fill_keywords_if_short() → return metadata dict
  ▼
batch_processing.py
  │  Copy file → exif_writer.py → write metadata → CSV export
  ▼
Output folder + CSV files
```

## Config Storage

**Location**: `config.json` in Windows `Documents/RJ Auto Metadata/`

**Current fields**:
- `input_dir`, `output_dir` — folder paths
- `delay`, `workers` — performance settings
- `rename`, `auto_kategori`, `auto_foldering` — file handling toggles
- `api_keys` — per-provider key storage
- `provider` — last used provider name
- `model` — last selected model ID
- `priority` — prompt detail level (Detailed/Balanced/Less/Custom)
- `keyword_count` — max keywords (8–49)
- `theme` — light/dark/system
- `installation_id`, `analytics_enabled` — anonymous analytics
- `models_by_provider` — cached model lists per provider `{provider: [model_ids]}`
- `selected_model_by_provider` — last selected model per provider `{provider: model_id}`
- `custom_base_url` — Custom provider base URL

## Planned Changes Summary

See `docs/ANALISYS_REFACTORING.md` for full details. High-level:

1. **OpenAI compat migration** — Gemini moves from native REST to OpenAI-compatible endpoint (`v1beta/openai/`), unifying request/response format across all providers
2. **Dynamic model fetch** — Replace hardcoded model presets with `GET /v1/models` calls; models cached per-provider in config
3. **UI restructure** — Remove Load/Delete/Save buttons, add Fetch button, add Custom URL field, restructure provider/model dropdown layout
4. **Dead code removal** — ~600 lines from Gemini alone (SDK/REST dual path, auto rotation, thinking config)
5. **Shared utilities** — Centralize `_clean_json_text()` to `src/utils/json_utils.py`

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
-

### Changed
-

### Fixed
-

## [3.4.0] - 2025-05-25

### Fixed
- **API Key Distribution:** Resolved an issue where API requests were not properly distributed across all available free API keys, often causing requests to concentrate on a single key (typically the first one in the list). The system now correctly rotates through all provided API keys based on their last used time, ensuring more balanced utilization and reducing premature rate limit errors on individual keys.
- **Premature Rate Limiting:** Addressed an issue where the internal rate limiter could incorrectly flag API keys or models as rate-limited sooner than the actual limits imposed by the Gemini API.

### Changed
- **Rate Limiting Strategy:** The internal token bucket-based rate limiting mechanism has been significantly revised. The program now primarily relies on the actual rate limits enforced by the Gemini API, with internal selection logic for keys and models now prioritizing the least recently used ones. Active cooldowns and token-based selection/penalties from the local rate limiter have been disabled to prevent premature limiting and to better align with Gemini's own quota management.
- **"Auto Rotasi" Model Selection:** Simplified the model selection logic when "Auto Rotasi" is active. It now solely relies on selecting the model least recently used from the `GEMINI_MODELS` list, removing dependency on internal token counts.
- **Fallback Strategy Overhaul:** The fallback mechanism, triggered when a primary model encounters a rate limit (HTTP 429) after all retries, has been enhanced:
    - It now iteratively attempts each model from the predefined `FALLBACK_MODELS` list sequentially if the prior fallback attempt also fails.
    - The primary model that initially failed due to the rate limit is automatically excluded from these fallback attempts.
    - This replaces the previous logic of selecting and trying only a single 'best' fallback model, increasing the chances of finding an available model.
---
## [3.3.2] - 2025-05-20

### Changed
- **Keyword Handling Optimized:** All keyword outputs are now always deduplicated and strictly limited to the user-specified maximum. This ensures no more over-limit or duplicate keywords, regardless of API response or file type.

### Fixed
- **Keyword Limit Bug:** Fixed an issue where the number of keywords could exceed the user-set limit (sometimes over 100) or contain duplicates, especially for vector and video files. Now, the keyword count is always enforced as intended.
---
## [3.3.1] - 2025-05-19

### Added
- **Enhanced Metadata Extraction:** Updated `_extract_metadata_from_text` function in `gemini_api.py` to include AdobeStockCategory and ShutterstockCategory in the output.

### Changed
- **Improved Keyword Handling:** Modified keyword extraction logic to exclude categories during the extraction process.
- **Enhanced CSV Export:** Improved `write_to_platform_csvs` function to better support metadata from AI results, including proper category extraction.

### Fixed
- **EXIF Writing Stability:** Fixed issues in `exif_writer.py` to enhance stability when writing metadata to different file formats.
---
## [3.3.0] - 2025-05-15 Feature Release

### Added
- **API Key Paid Option:** New checkbox in the API Key section of the UI. If enabled, users with a paid Gemini API key can use more workers than the number of API keys (removes the usual worker limit for free users). The state of this option is saved in the configuration file (`config.json`). **Note: Even with this option enabled, the maximum allowed workers is 100 for stability.**

### Changed
- **Worker Validation Logic:** When the 'API key paid?' option is enabled, the application no longer limits the number of workers to the number of API keys. This allows paid users to fully utilize their API quota and hardware, up to a maximum of 100 workers.
- **Configuration:** The state of the 'API key paid?' option is now saved and loaded automatically from `config.json` like other settings.
---
## [3.2.1] - 2025-05-13 Optimize Feature Release

### Fixed
- **API Key Checker Button:** Disable the 'Check API' button when processing starts, and reset it to enable it when the process stops or completes.
- **Log Messages:** Adjusted log messages in batch processing to reflect the current batch count accurately.
- **Log Messages:** Modified regex patterns for log message validation to align with recent changes.

---
## [3.2.0] - 2025-05-13 Optimize & Feature Release

### Added
- **API Key Checker Button:** New 'Cek API' button in the GUI to check all entered API keys at once. Results are shown in the log area, with clear OK/error summary per key.

### Changed
- **Log Filtering:** Log output from the API key checker is now visible in the GUI log (regex filter updated).

### Fixed
- **False API Limit Errors:** Removed internal rate limiter (TokenBucket) logic that was causing premature/fake API limit errors. Now, the app relies solely on Google-side quota enforcement.

### Removed
- **Internal Rate Limiter:** All TokenBucket and related cooldown logic have been removed from the codebase.

---
## [3.1.0] - 2025-05-08 Feature & BugFix Release

### Added
- **Smart API Key Selection:** Implemented logic to select the "most ready" API key based on its token bucket wait time and last usage time, replacing the previous random selection. This involves new helper functions `get_potential_wait_time` in `TokenBucket` and `select_smart_api_key` in `gemini_api.py`.
- **Fallback Model Mechanism:** If the user-selected or auto-selected API model fails due to rate limits (429) after all main retries, the system attempts one additional call using the "most ready" model from a predefined fallback list (`FALLBACK_MODELS`). This does not apply when "Auto Rotasi" mode is active. Logic handled by `select_best_fallback_model` and integrated into `_attempt_gemini_request` and `get_gemini_metadata` in `gemini_api.py`.
- **Adaptive Inter-Batch Cooldown:** The delay between processing batches now dynamically adjusts. If a high percentage (e.g., >90%) of API calls failed in the preceding batch, the next inter-batch delay is automatically set to 60 seconds to allow API RPM to recover. Otherwise, the user-defined delay is used. The delay reverts to the user-defined value if the subsequent batch (after a 60s cooldown) is successful (failure rate <90%). (`batch_processing.py`)

### Changed
- **Metadata Extraction Refactor:** The logic for extracting Title, Description, and Keywords from the API's text response has been centralized into a new helper function `_extract_metadata_from_text` within `get_gemini_metadata` (`gemini_api.py`). This eliminates code duplication for handling both primary and fallback API call results, leading to cleaner and more maintainable code.
- **API Call Logic Refactor:** The core logic for making a single attempt to the Gemini API, including error handling for specific HTTP status codes (429, 500, 503), has been refactored into the `_attempt_gemini_request` function in `gemini_api.py`.
- **`get_gemini_metadata` Overhaul:** This main function in `gemini_api.py` has been significantly reworked to utilize `_attempt_gemini_request`, manage the primary retry loop, and implement the new fallback model logic after the main loop fails due to a 429 error (only if not in "Auto Rotasi" mode).
- **API Key Handling in Processing:** `process_single_file` in `batch_processing.py` was updated to call `select_smart_api_key`. All specific file processing functions (for JPG, PNG, Video, Vector) were modified to accept a single pre-selected API key instead of a list of keys.

### Fixed
- Fixed a logical error in `wait_for_model_cooldown` (`rate_limiter.py`) where `time.time()` was incorrectly used in a `time.sleep()` context, ensuring cooldowns are applied correctly.

### Removed
- Deleted unused functions `get_gemini_metadata_with_key_rotation` and `_call_gemini_api_once` from `gemini_api.py` as their functionalities are now covered by the refactored API calling logic.

---
## [3.0.0] - 2025-05-05 Major Refactor & Feature Release

### Added
- **Model Selection:** Dropdown UI to select specific Gemini API models (e.g., `gemini-1.5-flash`, `gemini-1.5-pro`) or use "Auto Rotasi". (`src/ui/app.py`, `src/api/gemini_api.py`)
- **Keyword Count Input:** UI entry field to specify the maximum number of keywords (tags) to request from the API (min 8, max 49). (`src/ui/app.py`, `src/api/gemini_api.py`)
- **Prompt Priority:** Dropdown UI to select processing priority ("Kualitas", "Seimbang", "Cepat"). (`src/ui/app.py`)
- **Dynamic Prompts:** Implemented distinct API prompts for each priority level (Kualitas, Seimbang, Cepat) and file type (Standard, PNG/Vector, Video). (`src/api/gemini_prompts.py`, `src/api/gemini_api.py`)
- **Centralized Prompts:** Created `src/api/gemini_prompts.py` to store all prompt variations, improving maintainability.
- **Priority Logging:** Added log message to indicate which prompt priority is being used for each API request. (`src/api/gemini_api.py`)
- **UI Spacing:** Added empty labels to ensure correct visual row spacing in center/right columns. (`src/ui/app.py`)

### Changed
- **Major UI Refactor:** Removed status bar, progress bar, and associated status labels. Reorganized settings/options into a cleaner 3-column layout (Inputs Left, Dropdowns Middle, Toggles Right). (`src/ui/app.py`)
- **Prompt Management Refactor:** Moved all prompt definitions from `gemini_api.py` to the new `gemini_prompts.py` and updated imports/logic. (`src/api/gemini_api.py`, `src/api/gemini_prompts.py`)
- **Log Output:** Moved batch progress count `(x/x)` directly into the batch log message in the GUI. (`src/processing/batch_processing.py`, `src/ui/app.py`)
- **Keyword Validation:** Changed minimum allowed keyword input from 1 to 8. (`src/ui/app.py`)
- **UI Element Disabling:** Ensured new UI controls (Theme, Model, Priority dropdowns; Keyword input) are correctly disabled/enabled during processing. (`src/ui/app.py`)

### Fixed
- `NameError: name 'settings_header_tooltip' is not defined` after UI refactoring. (`src/ui/app.py`)
- UI layout not visually shifting down rows as intended (fixed by adding empty labels). (`src/ui/app.py`)

### Removed
- Status bar, progress bar, and associated UI variables (`progress_text_var`, etc.) from the main application UI. (`src/ui/app.py`)
- Redundant "Menggunakan prompt: ..." log messages for "Kualitas" priority to reduce log noise. (`src/api/gemini_api.py`)
- Old prompt definitions directly within `gemini_api.py`.

---
## [2.1.0] - 2025-05-02 Feature & BugFix Release

### Added
- **ShutterStock CSV:** Automatically set "illustration" column to "yes" for vector files (EPS, AI, SVG). (`src/metadata/csv_exporter.py`, `src/processing/batch_processing.py`)

### Changed
- **EXIF Failure Logging:** Changed log message for EXIF write failures from error (✗) to warning (⚠) and added clarification that processing continues. (`src/processing/batch_processing.py`)

### Fixed
- **EXIF Failure Handling:** Ensured processing (CSV writing, file moving) continues even if writing EXIF metadata directly to the file fails. (`src/metadata/exif_writer.py`, `src/processing/image_processing/format_jpg_jpeg_processing.py`, `src/processing/video_processing.py`)
- **Input File Deletion:** Ensured original input file is deleted after successful processing even if EXIF writing failed (consistent with normal processing). (`src/processing/batch_processing.py`)

---
## [2.0.1] - 2025-05-01 Bug Fix Release

### Fixed
- **Cropped EPS/AI Conversion:** Fixed an issue where EPS/AI files converted to JPG were getting cropped. This was resolved by adding the `-dEPSCrop` parameter to the Ghostscript command in `src/processing/vector_processing/format_eps_ai_processing.py`, ensuring Ghostscript uses the source file's BoundingBox.
- **Oversized EPS/AI Conversion Dimensions:** Fixed an issue where EPS/AI files converted to JPG resulted in pixel dimensions significantly larger than the original artboard size. This was addressed by removing the `-r300` parameter (which enforced a high DPI) from the Ghostscript command, allowing it to use the default resolution based on the BoundingBox.
- **Application Version:** Updated `APP_VERSION` constant and watermark text in `src/ui/app.py` to `2.0.1`.

---
## [2.0.0] - 2025-04-13 Major Refactor & Feature Release

This version represents a significant overhaul and feature expansion from v1.

### Added
- **Project Structure:** Reorganized into a modular `src/` directory (api, config, metadata, processing, ui, utils) for better maintainability.
- **GUI Implementation:** Introduced a user-friendly graphical interface using CustomTkinter (`src/ui/app.py`).
    - Includes folder selection, API key management (load/save/delete/hide), options (workers, delay, rename, etc.), status display, logging area, theme selection, tooltips, and completion dialog.
- **Enhanced API Integration (`src/api/`):**
    - Integrated `google-generativeai` client.
    - Implemented multi-API key rotation and multi-model rotation (e.g., `gemini-1.5-flash`, `gemini-1.5-pro`).
    - Added `TokenBucket` rate limiting for keys and models.
    - Improved API call retry logic.
- **Expanded File Processing (`src/processing/`):**
    - Added support for vectors (AI, EPS, SVG) via Ghostscript.
    - Added support for videos (MP4, MKV, AVI, MOV, MPEG, etc) via OpenCV/FFmpeg frame extraction.
- **Platform-Specific CSV Export (`src/metadata/`):**
    - Implemented category mapping for Adobe Stock & Shutterstock.
    - Generates separate, formatted CSV files.
- **Startup Dependency Checks:** Verifies ExifTool, Ghostscript, FFmpeg, GTK/cairocffi on launch with GUI logging/warnings.
- **Utility Modules (`src/utils/`):** Created helpers for system checks, analytics, file operations, etc.
- **Documentation:** Added `README.md`, `quick_guide.txt`, and this `CHANGELOG.md`.
- **Configuration:** Persistent settings saved to `config.json`.
- **Licensing Info:** Added main `LICENSE` (AGPLv3) and dependency licenses in `licenses/`.
- **Console Toggle (Windows Only):** Added UI switch and functionality to show/hide the console window.
- **Basic `.gitignore`**.

### Changed
- **Code Organization:** Major refactoring separating UI, API, processing logic.
- **Main Entry Point:** Shifted to `main.py` launching `MetadataApp`.
- **Logging:** Integrated with GUI text area.
- **Stop Handling:** Refined process interruption logic.
- **UI Switches:** Removed text labels from API Key/Console switches, added tooltips.
- **`.gitignore`:** Updated (later simplified).

### Fixed
- **Ghostscript Path Resolution:** Corrected issue where AI/EPS conversion failed in packaged builds due to worker threads not accessing the correct Ghostscript path. Implemented parameter passing for the path.
- **Logging:** Cleaned up verbose stdout debug logging from the initial Ghostscript check.

### Removed
- Removed hardcoded application expiry date check from v1.
- Removed initial mandatory Terms & Conditions dialog from v1.
- Removed standalone execution capability from `core_logic.py`.

---
## [1.0.0] - 2025-04-05 (Approximate Date) Initial Version

### Added
- First functional version combining UI (`RJ_Auto_Metadata.py`) and logic (`core_logic.py`).
- Basic image processing (JPG/PNG) with Gemini API.
- ExifTool integration for metadata writing.
- Simple UI for core functions (folders, keys, basic options).
- Basic `config.json` saving.
- Bundled ExifTool.



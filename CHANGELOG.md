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

---
## [3.0.0] - 2025-05-13

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

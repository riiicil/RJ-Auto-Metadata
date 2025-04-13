# Changelog 📜

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] 🚧

### Added
-

### Changed
-

### Fixed
-

---
## [2.0.0] - 2025-04-13 🎉 Major Refactor & Feature Release

This version represents a significant overhaul and feature expansion from v1.

### Added ✨
- **Project Structure:** Reorganized into a modular `src/` directory (api, config, metadata, processing, ui, utils) for better maintainability. 🏗️
- **GUI Implementation:** Introduced a user-friendly graphical interface using CustomTkinter (`src/ui/app.py`). 🎨
    - Includes folder selection, API key management (load/save/delete/hide), options (workers, delay, rename, etc.), status display, logging area, theme selection, tooltips, and completion dialog.
- **Enhanced API Integration (`src/api/`):**
    - Integrated `google-generativeai` client. 🧠
    - Implemented multi-API key rotation and multi-model rotation (e.g., `gemini-1.5-flash`, `gemini-1.5-pro`). 🔄
    - Added `TokenBucket` rate limiting for keys and models. ⏳
    - Improved API call retry logic.
- **Expanded File Processing (`src/processing/`):**
    - Added support for vectors (AI, EPS, SVG) via external tools.
    - Added support for videos (MP4, MKV) via OpenCV/FFmpeg frame extraction. 📹
- **Platform-Specific CSV Export (`src/metadata/`):**
    - Implemented category mapping for Adobe Stock & Shutterstock. 📊
    - Generates separate, formatted CSV files.
- **Startup Dependency Checks:** Verifies ExifTool, Ghostscript, FFmpeg, GTK/cairocffi on launch with GUI logging/warnings. ✅
- **Utility Modules (`src/utils/`):** Created helpers for system checks, analytics, file operations, etc. 🛠️
- **Documentation:** Added `README.md`, `quick_guide.txt`, and this `CHANGELOG.md`. 📚
- **Configuration:** Persistent settings saved to `config.json`. 💾
- **Licensing Info:** Added main `LICENSE` (AGPLv3) and dependency licenses in `licenses/`. 📜
- **Basic `.gitignore`**.

### Changed 🔄
- **Code Organization:** Major refactoring separating UI, API, processing logic.
- **Main Entry Point:** Shifted to `main.py` launching `MetadataApp`.
- **Logging:** Integrated with GUI text area.
- **Stop Handling:** Refined process interruption logic.
- **`.gitignore`:** Updated (later simplified).

### Removed ❌
- Removed hardcoded application expiry date check from v1.
- Removed initial mandatory Terms & Conditions dialog from v1.
- Removed standalone execution capability from `core_logic.py`.

---
## [1.0.0] - 2025-04-05 (Approximate Date) 🌱 Initial Version

### Added
- First functional version combining UI (`RJ_Auto_Metadata.py`) and logic (`core_logic.py`).
- Basic image processing (JPG/PNG) with Gemini API.
- ExifTool integration for metadata writing.
- Simple UI for core functions (folders, keys, basic options).
- Basic `config.json` saving.
- Bundled ExifTool.

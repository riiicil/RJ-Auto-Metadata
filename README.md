# RJ Auto Metadata ✨ (v2.0)

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://example.com/build-status) <!-- Placeholder -->
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) <!-- Placeholder -->

**© Riiicil 2025**

## 1. 🚀 Introduction

RJ Auto Metadata is a powerful desktop application built with Python and CustomTkinter 🎨, designed to streamline the process of adding descriptive metadata (titles, descriptions, keywords) to various media files 🖼️📹. It leverages the capabilities of the Google Gemini generative AI model 🧠 to analyze file content and suggest relevant metadata, which is then embedded directly into the files using the industry-standard ExifTool utility 🛠️. This tool is particularly useful for photographers, videographers, graphic designers, and stock media contributors who need to manage and enrich large collections of digital assets efficiently.

## 2. 🌟 Core Features Detailed

*   **🤖 AI-Powered Metadata Generation:**
    *   Utilizes the Google Gemini API for content analysis and metadata suggestion.
    *   Extracts meaningful titles, detailed descriptions, and relevant keywords based on visual or content analysis.
    *   Handles API communication, including request formatting and response parsing (`src/api/gemini_api.py`).
*   **⚡ Efficient Batch Processing:**
    *   Processes entire folders of files automatically.
    *   Uses a configurable number of parallel worker threads (`concurrent.futures.ThreadPoolExecutor`) for faster throughput (`src/processing/batch_processing.py`).
    *   Implements API key rotation 🔄 to distribute load and potentially bypass rate limits when multiple keys are provided.
    *   Includes configurable delays ⏳ between API requests per worker to manage API usage quotas (`src/api/rate_limiter.py`).
*   **📁 Broad File Format Compatibility:**
    *   **Images:** Processes standard formats like `.jpg`, `.jpeg`, `.png` directly (`src/processing/image_processing/`).
    *   **Vectors:** Handles `.ai`, `.eps`, and `.svg` files. Requires external tools (Ghostscript, GTK3 Runtime) for rendering/conversion before analysis (`src/processing/vector_processing/`).
    *   **Videos:** Supports `.mp4` and `.mkv`. Extracts representative frames using OpenCV and FFmpeg for analysis (`src/processing/video_processing.py`).
*   **✍️ Direct Metadata Embedding:**
    *   Integrates with the external **ExifTool** command-line utility (`tools/exiftool/`) to write standardized metadata fields (e.g., XMP:Title, XMP:Description, IPTC:Keywords) into the output files (`src/metadata/exif_writer.py`).
*   **⚙️ Extensive Customization & Configuration:**
    *   **Folder Selection:** Dedicated input and output folder paths. Ensures input/output are distinct.
    *   **API Key Management:** Text area for multiple Gemini API keys (one per line). Supports loading/saving keys 🔑 to/from `.txt` files. Option to show/hide keys in the UI.
    *   **Performance Tuning:** Adjust the number of `Workers` and `Delay (s)` between API calls.
    *   **File Handling Options:**
        *   `Rename File?`: Automatically renames output files using the generated title.
        *   `Auto Kategori?`: (Experimental) Attempts to assign categories based on API results (`src/metadata/categories/`).
        *   `Auto Foldering?`: Automatically organizes output files into subdirectories (`Images`, `Vectors`, `Videos`) based on their type.
    *   **Appearance:** Choose between `Light` 💡, `Dark` 🌙, or `System` 💻 themes, powered by CustomTkinter.
*   **🖥️ Intuitive User Interface (`src/ui/app.py`):**
    *   Built with CustomTkinter for a modern look and feel.
    *   Clear sections for folder selection, API keys, options, status, and logging.
    *   Real-time progress bar 📊 and status updates during processing.
    *   Detailed logging area 📜 showing processing steps, successes, failures, and warnings.
    *   Tooltips (?) provide help for various settings and buttons.
    *   Completion dialog ✅ summarizes the results after processing.
*   **💾 Persistent Settings:**
    *   Automatically saves user configuration (folders, keys, options, theme) to `config.json` upon closing or successful processing. Typically located in `Documents/RJAutoMetadata` on Windows (`src/config/config.py`).
    *   Maintains a `processed_cache.json` to potentially track processed files (current usage might be limited).
*   **⚠️ Robust Error Handling & Logging:**
    *   Provides informative messages in the log for various events, including API errors, file processing issues, and missing dependencies.
    *   Graceful handling of process interruption (`Stop` button 🛑).
    *   Logs messages with timestamps and severity tags (Info, Warning, Error, Success).
*   **📈 Optional Usage Analytics:**
    *   Can send anonymous data (like OS version, event counts, success rates) using Google Analytics Measurement Protocol to help the developer improve the application (`src/utils/analytics.py`). Associated with a unique, anonymous `installation_id`. Can be implicitly disabled by not having Measurement ID/API Secret configured at build time (or potentially via a future setting).

## 3. 🔄 Workflow Overview

The application follows these general steps during processing:

1.  **Initialization:** User launches the application (`main.py`), initializing the UI (`src/ui/app.py`). Settings load from `config.json`.
2.  **Configuration:** User selects Input/Output folders, provides Gemini API keys, and adjusts processing options.
3.  **Start Process:** User clicks "Mulai Proses".
4.  **Validation:** Application validates inputs (folders, keys, settings).
5.  **File Discovery:** Scans the Input Folder for supported file types (`src/utils/file_utils.py`).
6.  **Batch Processing (`src/processing/batch_processing.py`):**
    *   Creates a thread pool (`Workers`).
    *   Distributes files to worker threads.
    *   Each worker:
        *   **Preprocessing:** Converts/extracts data (video frames, vector rendering). Handles compression (`src/utils/compression.py`).
        *   **API Call:** Sends data to Gemini API (respecting `Delay`, rotating keys) (`src/api/gemini_api.py`, `src/api/rate_limiter.py`).
        *   **Metadata Extraction:** Parses Gemini response.
        *   **File Copying:** Copies original to Output Folder (optional subfolders).
        *   **Metadata Writing:** Calls ExifTool to embed metadata (`src/metadata/exif_writer.py`).
        *   **Renaming (Optional):** Renames output file.
        *   **Categorization (Optional):** Applies category logic (`src/metadata/categories/`).
        *   **Logging & Progress:** Reports status to UI.
7.  **Completion:** Summary message displayed, UI re-enabled. Settings/cache saved.

## 4. 💻 System Requirements

### 4.1. Python Environment 🐍

*   **Python 3.x:** (Recommended: 3.9 or newer)
*   **pip:** For installing dependencies.
*   **Required Python Packages:** Install via `pip install -r requirements.txt`. Key packages:
    *   `customtkinter>=5.2.2` (GUI)
    *   `Pillow>=11.1.0` (Images)
    *   `google-generativeai>=0.8.4` (Gemini API)
    *   `requests>=2.32.3` (HTTP)
    *   `opencv-python>=4.11.0.86` (Video Frames - needs FFmpeg)
    *   `svglib>=1.5.1`, `reportlab>=4.3.1`, `CairoSVG>=2.7.1` (SVG - needs GTK3)
    *   `portalocker>=3.1.1` (Optional File Locking)
    *   *Plus other dependencies.*

### 4.2. External Tools & Libraries (❗ CRITICAL ❗)

These **must be installed manually** and accessible (ideally in system PATH):

1.  **ExifTool:**
    *   **Purpose:** Reads/writes metadata (EXIF, IPTC, XMP). Essential!
    *   **License:** Artistic / GPL
    *   **Download:** [https://exiftool.org/](https://exiftool.org/)
    *   **Note:** Version included in `tools/`, but system install preferred.
2.  **Ghostscript:**
    *   **Purpose:** Needed for `.eps` and `.ai` file analysis/conversion.
    *   **License:** AGPLv3
    *   **Download:** [https://www.ghostscript.com/releases/gsdnld.html](https://www.ghostscript.com/releases/gsdnld.html)
3.  **FFmpeg:**
    *   **Purpose:** Needed by OpenCV for `.mp4`, `.mkv` frame reading.
    *   **License:** LGPL / GPL
    *   **Download:** [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
4.  **GTK3 Runtime:**
    *   **Purpose:** Needed by CairoSVG for SVG rendering (especially on Windows).
    *   **License:** LGPL
    *   **Download (Windows):** [GTK for Windows Runtime Installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases) or via MSYS2/Chocolatey.

**Failure to install these external tools WILL cause errors for vector/video files!** 🚫

## 5. 🛠️ Installation Guide

1.  **Clone Repository (Optional):**
    ```bash
    git clone https://github.com/riiicil/RJ-Auto-Metadata-v.2.0.git
    cd RJ_Auto_metadata
    ```
    (Or download & extract ZIP)
2.  **Setup Python Environment (Recommended):**
    ```bash
    python -m venv venv
    # Windows: .\venv\Scripts\activate
    # macOS/Linux: source venv/bin/activate
    ```
3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Install External Tool: ExifTool:**
    *   Download & follow OS-specific instructions from [exiftool.org](https://exiftool.org/).
    *   Verify: `exiftool -ver` in terminal.
5.  **Install External Tool: Ghostscript:**
    *   Download & run installer from [ghostscript.com](https://www.ghostscript.com/releases/gsdnld.html).
    *   Ensure installation dir is in PATH.
    *   Verify: `gswin64c -version` (or similar) in terminal.
6.  **Install External Tool: FFmpeg:**
    *   Download build from [ffmpeg.org](https://ffmpeg.org/download.html).
    *   Extract & add the `bin` directory to PATH.
    *   Verify: `ffmpeg -version` in terminal.
7.  **Install External Tool: GTK3 Runtime (Windows):**
    *   Download & run installer from [GTK for Windows Runtime Installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases).
    *   (Or use MSYS2/Chocolatey).

## 6. ⚙️ Configuration Details

### 6.1. `config.json` 📄

Stores settings automatically (usually in `Documents/RJAutoMetadata` on Windows).
*   `input_dir`, `output_dir`: Folder paths.
*   `delay`, `workers`: Performance settings.
*   `rename`, `auto_kategori`, `auto_foldering`: File handling toggles (booleans).
*   `api_keys`: List of your Gemini API keys.
*   `show_api_keys`: UI visibility state (boolean).
*   `theme`: "light", "dark", or "system".
*   `installation_id`: Anonymous analytics ID.
*   `analytics_enabled`: Analytics toggle state.

### 6.2. UI Settings 🖱️

*   **Input/Output Folders:** Must be valid, different directories.
*   **API Keys:** One key per line. Load/Save/Delete/Show-Hide options available.
*   **Workers:** Threads (1-10+). More workers = faster, but more API usage.
*   **Delay (s):** Pause between API calls per worker (avoids rate limits).
*   **Rename File?:** ✅ Renames output file to `Generated Title.ext`.
*   **Auto Kategori?:** ✅ Applies experimental categories.
*   **Auto Foldering?:** ✅ Sorts output into `Images/`, `Vectors/`, `Videos/`.
*   **Theme:** Visual style selection.

### 6.3. Analytics 📊

*   Uses Google Analytics (Measurement Protocol) for anonymous usage stats if configured at build time (`src/config/config.py`).
*   Helps improve the app. Sends OS info, event counts, success rates. **No personal data or file content is sent.**

## 7. ▶️ Usage Guide

1.  **Launch:** Run `python main.py` or the executable.
2.  **Set Folders:** Use "Browse" for **Input** & **Output** directories (must be different!).
3.  **Enter API Keys:** Paste keys (one per line) or use "Load". Manage with Save/Delete/Show-Hide.
4.  **Adjust Settings (Optional):** Tune `Workers`, `Delay`, Toggles (`Rename?`, etc.), `Theme`.
5.  **Initiate Processing:** Click **"Mulai Proses"**. Buttons will update state.
6.  **Monitor:** Watch "Status" (progress bar/text) & "Log" (details, ✓ success, ✗ failure).
7.  **Interrupt (Optional):** Click **"Hentikan"** 🛑 to stop gracefully (may take a moment).
8.  **Review Results:** Check summary dialog & Output Folder for processed files.
9.  **Clear Log (Optional):** Click **"Clear Log"** for a clean slate.
10. **Exit:** Close window (settings save automatically).

## 8. ✅ Supported File Formats

*   **Images:** `.jpg`, `.jpeg`, `.png`
*   **Vectors:** `.ai`, `.eps` (Need Ghostscript), `.svg` (Need Ghostscript & GTK3)
*   **Videos:** `.mp4`, `.mkv` (Need FFmpeg)

*Processing vectors/videos WILL FAIL without the required external tools!*

## 9. ❓ Troubleshooting Common Issues

*   **"Exiftool not found":** ExifTool not installed or not in PATH. 👉 Reinstall/check PATH.
*   **Errors on `.ai`/`.eps`:** Ghostscript missing or not in PATH. 👉 Install/check PATH.
*   **Errors on `.svg` (Windows):** GTK3 Runtime missing/misconfigured. 👉 Install GTK3.
*   **Errors on `.mp4`/`.mkv`:** FFmpeg missing or not in PATH. 👉 Install/check PATH.
*   **API Errors (429, Auth):** Incorrect/inactive API key? Hitting rate limits? 👉 Check keys, increase `Delay`, reduce `Workers`, add more keys. Check internet.
*   **Permission Errors:** Cannot write to Output Folder or config location? 👉 Choose different folder, check permissions.
*   **Freezes/Crashes:** Review the GUI log carefully for any error messages. Since the terminal output is suppressed, the GUI log is the primary source of information. Ensure all dependencies (Python and external) are correctly installed. If the log provides no clues, consider system resource issues or try reducing the number of `Workers`.

## 10. 🏗️ Project Structure Deep Dive

*   `main.py`: Entry point.
*   `src/`: Core logic.
    *   `api/`: Gemini API interaction, rate limiting.
    *   `config/`: Settings load/save.
    *   `metadata/`: ExifTool writing, categories.
    *   `processing/`: Batch logic, format handlers.
    *   `ui/`: CustomTkinter GUI (`app.py`).
    *   `utils/`: Helpers (files, logging, analytics).
*   `tools/`: Bundled tools (ExifTool).
*   `assets/`: Icons, etc.
*   `licenses/`: Dependency licenses.
*   `sample_files/`: Test files.

## 11. 📜 License Information

Licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See `LICENSE` file.

*   **Freedom:** Use, modify, distribute.
*   **Share Alike:** Modified source code must also be AGPLv3.
*   **Network Use:** If run modified on a server, users interacting remotely must get source code access.

Dependencies have their own licenses (MIT, Apache, LGPL, etc.). See `licenses/` folder. Comply with all, especially for external tools (ExifTool, Ghostscript, FFmpeg, GTK3).

## 12. 🤝 Contributing

This is currently a solo project and my first one! 🎉 As such, I'm focusing on learning and building. While I'm not set up for formal contributions right now, I'm always open to hearing feedback or suggestions. You can reach out via the contact details below (if provided).

## 13. 📞 Contact & Support

You can find me and discuss this project (or others) at: https://s.id/rj_auto_metadata

## 14. 💖 Support the Project

If you find this application helpful and would like to support its continued development, you can do so via the QR code below. Thank you for your support!

![Support QR Code](assets/qr.jpg)

---

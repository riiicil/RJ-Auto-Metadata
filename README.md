# RJ Auto Metadata

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://example.com/build-status) <!-- Placeholder -->
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) <!-- Placeholder -->

**© Riiicil 2025**

## 1. Introduction

RJ Auto Metadata is a powerful desktop application built with Python and CustomTkinter, designed to streamline the process of adding descriptive metadata (titles, descriptions, keywords) to various media files. It leverages the capabilities of the Google Gemini generative AI model to analyze file content and suggest relevant metadata, which is then embedded directly into the files using the industry-standard ExifTool utility. This tool is particularly useful for photographers, videographers, graphic designers, and stock media contributors who need to manage and enrich large collections of digital assets efficiently.

## 2. Core Features Detailed

*   **AI-Powered Metadata Generation:**
    *   Utilizes the Google Gemini API for content analysis and metadata suggestion.
    *   Extracts meaningful titles, detailed descriptions, and relevant keywords based on visual or content analysis.
    *   Handles API communication, including request formatting and response parsing (`src/api/gemini_api.py`).
*   **Efficient Batch Processing:**
    *   Processes entire folders of files automatically.
    *   Uses a configurable number of parallel worker threads (`concurrent.futures.ThreadPoolExecutor`) for faster throughput (`src/processing/batch_processing.py`).
    *   Smart API Key Selection. Intelligently selects the "most ready" API key for each request based on its current token bucket wait time and last usage, optimizing throughput and reducing immediate rate limit errors, rather than simple rotation. (`src/api/gemini_api.py`)
    *   Adaptive Inter-Batch Cooldown. Automatically adjusts the delay between processing batches. If a high percentage of API calls failed in the previous batch, the delay is temporarily increased (e.g., to 60 seconds) to allow API RPM to recover. Otherwise, the user-defined delay is used. (`src/processing/batch_processing.py`)
    *   Fallback Model Mechanism. If an API call fails due to rate limits (429) after all main retries with the selected model, the application attempts one final call using the "most ready" model from a predefined fallback list, increasing the chances of successful metadata generation. This does not apply if "Auto Rotasi" is active for model selection. (`src/api/gemini_api.py`)
    *   Includes configurable base delays between API requests per worker to manage API usage quotas (`src/api/rate_limiter.py`).
*   **Broad File Format Compatibility:**
    *   **Images:** Processes standard formats like `.jpg`, `.jpeg`, `.png` directly (`src/processing/image_processing/`).
    *   **Vectors:** Handles `.ai`, `.eps`, and `.svg` files. Requires external tools (Ghostscript, GTK3 Runtime) for rendering/conversion before analysis (`src/processing/vector_processing/`).
    *   **Videos:** Supports `.mp4`, `.mkv`, `avi`, `mov`, `mpeg`, etc. Extracts representative frames using OpenCV and FFmpeg for analysis (`src/processing/video_processing.py`).
*   **Direct Metadata Embedding:**
    *   Integrates with the external **ExifTool** command-line utility (`tools/exiftool/`) to write standardized metadata fields (e.g., XMP:Title, XMP:Description, IPTC:Keywords) into the output files (`src/metadata/exif_writer.py`).
*   **Extensive Customization & Configuration:**
    *   **Folder Selection:** Dedicated input and output folder paths. Ensures input/output are distinct.
    *   **API Key Management:** Text area for multiple Gemini API keys (one per line). Supports loading/saving keys to/from `.txt` files. Option to show/hide keys in the UI.
    *   **API Key Paid Option:** New checkbox in the API Key section. If you have a paid Gemini API key, enable this option to allow the use of more workers than the number of API keys (removes the usual worker limit for free users). For free users, leave this unchecked to avoid hitting rate limits. **Note: Even with this option enabled, the maximum allowed workers is 100 for stability.**
    *   **API Model Selection:** Choose a specific Gemini model (e.g., `gemini-1.5-flash`, `gemini-1.5-pro`) or use automatic rotation (`Auto Rotasi`) via a dropdown.
    *   **Prompt Priority:** Select the desired trade-off between result detail and speed (`Kualitas`, `Seimbang`, `Cepat`) via a dropdown, using different underlying prompts.
        *   _Note:_ Prompt length affects API token usage. Longer prompts (`Kualitas`) consume more input tokens per request, potentially hitting token limits (TPM/TPD) faster. Shorter prompts (`Cepat`) are more token-efficient.
    *   **Keyword Count:** Specify the maximum number of keywords to request from the API (min 8, max 49).
    *   **Performance Tuning:** Adjust the number of `Workers` and `Delay (s)` between API calls.
    *   **File Handling Options:**
        *   `Rename File?`: Automatically renames output files using the generated title.
        *   `Auto Kategori?`: (Experimental) Attempts to assign categories based on API results (`src/metadata/categories/`).
        *   `Auto Foldering?`: Automatically organizes output files into subdirectories (`Images`, `Vectors`, `Videos`) based on their type.
    *   **Appearance:** Choose between `Light`, `Dark`, or `System` themes, powered by CustomTkinter.
*   **Intuitive User Interface (`src/ui/app.py`):**
    *   Built with CustomTkinter for a modern look and feel.
    *   Clear sections for folder selection, API keys, and a refined 3-column layout for options (Inputs Left, Dropdowns Middle, Toggles Right).
    *   Real-time detailed logging area showing processing steps, successes, failures, warnings, and batch progress `(x/x)`.
    *   Removed visual status bar; all progress feedback is now in the log.
    *   Tooltips (?) provide help for various settings and buttons.
    *   Completion dialog summarizes the results after processing.
*   **Persistent Settings:**
    *   Automatically saves user configuration (folders, keys, options, theme) to `config.json` upon closing or successful processing. Typically located in `Documents/RJAutoMetadata` on Windows (`src/config/config.py`).
    *   Maintains a `processed_cache.json` to potentially track processed files (current usage might be limited).
*   **Robust Error Handling & Logging:**
    *   Provides informative messages in the log for various events, including API errors, file processing issues, and missing dependencies.
    *   Graceful handling of process interruption (`Stop` button).
    *   Logs messages with timestamps and severity tags (Info, Warning, Error, Success).

*   **Optional Usage Analytics:**
      Can send anonymous data (like OS version, event counts, success rates) using Google Analytics Measurement Protocol to help the developer improve the application (`src/utils/analytics.py`). Associated with a unique, anonymous `installation_id`. Can be implicitly disabled by not having Measurement ID/API Secret configured at build time (or potentially via a future setting).
*   **Console Visibility Toggle (Windows Only):**
      Provides a switch in the UI to **minimize/restore** the underlying console window (`RJ Auto Metadata.exe`). This is useful for temporarily hiding the console while keeping detailed logs accessible. Visibility state is saved in the configuration.
   *   **Alternative No-Console Executable:** For users who prefer **no console window at all**, a second executable (`RJ Auto Metadata No Console.exe`) is included in the installation directory (e.g., `C:\Program Files (x86)\RJ Auto Metadata`). Running this file directly will launch the application without an initial console window.
## 3. Workflow Overview

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
        *   **API Call:** Selects the smartest API key, sends data to Gemini API (respecting base `Delay` and adaptive cooldowns, utilizing fallback models if necessary) (`src/api/gemini_api.py`, `src/api/rate_limiter.py`).
        *   **Metadata Extraction:** Parses Gemini response.
        *   **File Copying:** Copies original to Output Folder (optional subfolders).
        *   **Metadata Writing:** Calls ExifTool to embed metadata (`src/metadata/exif_writer.py`).
        *   **Renaming (Optional):** Renames output file.
        *   **Categorization (Optional):** Applies category logic (`src/metadata/categories/`).
        *   **Logging & Progress:** Reports status to UI.
7.  **Completion:** Summary message displayed, UI re-enabled. Settings/cache saved.


## 4. System Requirements

### 4.1. Python Environment

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

### 4.2. External Tools & Libraries Dependencies

The application relies on several external command-line tools for full functionality:

1.  **ExifTool:** Reads/writes metadata (EXIF, IPTC, XMP). **(Bundled)**
2.  **Ghostscript:** Needed for `.eps` and `.ai` file analysis/conversion. **(Bundled)**
3.  **FFmpeg:** Needed by OpenCV for `.mp4`, `.mkv`, `avi`, `mov`, `mpeg`, `etc` frame reading. **(Bundled)**
4.  **GTK3 Runtime (Windows Only):** Needed by CairoSVG for SVG rendering. **(Handled by Installer)**

*   **For users of the provided `.exe` installer:**
    *   ExifTool, Ghostscript, and FFmpeg are **included** within the `tools/` directory of the installation and should work automatically.
    *   The installer will attempt to run the **GTK3 Runtime installer** separately during setup. You need to accept its installation for SVG support.
*   **For users running from source code:**
    *   You **must install ExifTool, Ghostscript, FFmpeg, and GTK3 Runtime manually** and ensure they are accessible in your system's PATH.
    *   Download links:
        *   ExifTool: [https://exiftool.org/](https://exiftool.org/)
        *   Ghostscript: [https://www.ghostscript.com/releases/gsdnld.html](https://www.ghostscript.com/releases/gsdnld.html)
        *   FFmpeg: [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
        *   GTK3 (Win): [GTK for Windows Runtime Installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)

**Failure of these tools WILL cause errors for vector/video files!**

## 5. Installation Guide

There are two main ways to install and run RJ Auto Metadata: using the provided installer or running directly from the source code.

### 5.1. Using the Installer (.exe) (Recommended for most users)

This is the easiest way to get started on Windows.

1.  **Download Installer:** Go to the [Releases page](https://github.com/riiicil/RJ-Auto-Metadata/releases) on GitHub. Download the `v3.x.x.zip` file from the latest release assets.
2.  **Extract and run Installer:** Double-click the downloaded `setup.exe`.
3.  **Follow Prompts:** Follow the on-screen instructions provided by the installer. It will guide you through the process, including installing necessary components like the GTK3 Runtime (required for SVG files). Accept the prompts to install these components when asked.
4.  **Launch:** Once installation is complete, you can launch RJ Auto Metadata from the Start Menu shortcut or the optional desktop icon.

### 5.2. Running from Source Code (For developers or advanced users)
Follow these steps if you want to run the application directly using Python:

1.  **Clone Repository (Optional):**
    ```bash
    git clone https://github.com/riiicil/RJ-Auto-Metadata.git
    cd RJ_Auto_metadata
    ```
    (Or download & extract the source code ZIP from the repository page).
2.  **Setup Python Environment (Recommended):** Create and activate a virtual environment.
    ```bash
    python -m venv venv
    # Windows: .\venv\Scripts\activate
    # macOS/Linux: source venv/bin/activate
    ```
3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Install ALL External Tools Manually:** You **must** install ExifTool, Ghostscript, FFmpeg, and (on Windows) GTK3 Runtime yourself and ensure they are correctly added to your system's PATH. Refer to the download links in section [4.2. External Tools & Libraries Dependencies](#42-external-tools--libraries-dependencies). Verify each tool is working via your terminal (e.g., `exiftool -ver`, `gswin64c -version`, `ffmpeg -version`).
5.  **Run the Application:**
    ```bash
    python main.py
    ```

## 6. Configuration Details

### 6.1. `config.json`

Stores settings automatically (usually in `Documents/RJAutoMetadata` on Windows).
*   `input_dir`, `output_dir`: Folder paths.
*   `delay`, `workers`: Performance settings.
*   `rename`, `auto_kategori`, `auto_foldering`: File handling toggles (booleans).
*   `api_keys`: List of your Gemini API keys.
*   `show_api_keys`: UI visibility state (boolean).
*   `model`: Selected API model (e.g., "gemini-1.5-flash", "Auto Rotasi").
*   `priority`: Selected prompt priority ("Kualitas", "Seimbang", "Cepat").
*   `keyword_count`: Maximum keywords requested (string, e.g., "49").
*   `theme`: "light", "dark", or "system".
*   `installation_id`: Anonymous analytics ID.
*   `analytics_enabled`: Analytics toggle state.
*   `api_key_paid`: (boolean) If true, disables the worker limit based on API key count (for paid API key users). **Maximum allowed workers is 100.**

### 6.2. UI Settings

*   **Input/Output Folders:** Must be valid, different directories.
*   **API Keys:** One key per line. Load/Save/Delete/Show-Hide options available.
*   **API Key Paid?:** (Checkbox) If you have a paid Gemini API key, enable this to use more workers than the number of API keys. For free users, leave unchecked to avoid rate limits. **Maximum allowed workers is 100.**
*   **Keyword:** Max keywords from API (8-49).
*   **Workers:** Threads (1-10+). More workers = faster, but more API usage. (Paid users can use more workers by enabling the checkbox above, up to a maximum of 100.)
*   **Delay (s):** Pause between API calls per worker (avoids rate limits).
*   **Theme:** Visual style selection.
*   **Model:** Select specific Gemini model or Auto Rotasi.
*   **Prioritas:** Choose prompt detail level (Kualitas/Seimbang/Cepat).
*   **Rename File?:** Renames output file to `Generated Title.ext`.
*   **Auto Kategori?:** Applies experimental categories.
*   **Auto Foldering?:** Sorts output into `Images/`, `Vectors/`, `Videos/`.

### 6.3. Analytics

*   Uses Google Analytics (Measurement Protocol) for anonymous usage stats if configured at build time (`src/config/config.py`).
*   Helps improve the app. Sends OS info, event counts, success rates. **No personal data or file content is sent.**

## 7. Usage Guide

1.  **Launch:**
    *   Run `python main.py` (if running from source).
    *   Use the desktop/start menu shortcut, which points to `RJ Auto Metadata.exe` (includes a console window that can be minimized/restored via the UI toggle).
    *   *Optional:* If you prefer no console window, navigate to the installation directory and run `RJ Auto Metadata No Console.exe` directly.
2.  **Set Folders:** Use "Browse" for **Input** & **Output** directories (must be different!).
3.  **Enter API Keys:** Paste keys (one per line) or use "Load". Manage with Save/Delete/Show-Hide.
4.  **Adjust Settings (Optional):** Tune `Keyword`, `Workers`, `Delay`, `Theme`, `Model`, `Prioritas`, Toggles (`Rename?`, etc.).
5.  **Initiate Processing:** Click **"Mulai Proses"**. Buttons will update state.
6.  **Monitor:** Watch the **"Log"** area for detailed steps, batch progress `(x/x)`, success/failure messages.
7.  **Interrupt (Optional):** Click **"Hentikan"** to stop gracefully (may take a moment).
8.  **Review Results:** Check summary dialog & Output Folder for processed files.
9.  **Clear Log (Optional):** Click **"Clear Log"** for a clean slate.
10. **Exit:** Close window (settings save automatically).

## 8. Gemini API Rate Limits (Free User)

When using the Google Gemini API, your usage is subject to several rate limits to ensure fair and stable access for all users. Exceeding any of these limits will result in a rate limit error from the API.

**Rate limits are measured across four main dimensions:**

- **Requests per minute (RPM):** Maximum number of API requests allowed per minute.
- **Requests per day (RPD):** Maximum number of API requests allowed per day.
- **Tokens per minute (TPM):** Maximum number of tokens processed per minute.
- **Tokens per day (TPD):** Maximum number of tokens processed per day.

Your usage is evaluated against each limit independently. If you exceed any one of them (for example, RPM), further requests will be blocked until your usage drops below the threshold, even if you have not reached the other limits. These limits are applied per project, not per API key.

**Limits vary by model and may change over time.** Here are some example limits:

| Model                              | RPM | TPM      | RPD  |
|-------------------------------------|-----|----------|------|
| Gemini 2.5 Flash Preview 04-17      | 10  | 250,000  | 500  |
| Gemini 2.5 Pro Experimental 03-25   | 5   | 250,000  | 25   |
| Gemini 2.0 Flash                    | 15  | 1,000,000| 1,500|
| Gemini 2.0 Flash-Lite               | 30  | 1,000,000| 1,500|
| Gemini 1.5 Pro                      | 2   | 250,000  |  50  |
| Gemini 1.5 Flash                    | 15  | 250,000  | 500  |
| Gemini 1.5 Flash-8b                 | 15  | 250,000  | 500  |

> **Note:** Rate limits are more restrictive for experimental and preview models. Always refer to the [official Gemini API documentation](https://ai.google.dev/gemini-api/docs/rate-limits) for the most up-to-date information.
> RJ Auto Metadata v3.1.0 and later include several internal mechanisms like Smart API Key Selection, Adaptive Inter-Batch Cooldown, and a Fallback Model system to help navigate these limits more effectively and improve processing resilience. However, respecting these limits by configuring appropriate worker counts and base delays remains crucial for sustained operation.

## 9. Supported File Formats

*   **Images:** `.jpg`, `.jpeg`, `.png`
*   **Vectors:** `.ai`, `.eps` (Need Ghostscript), `.svg` (Need Ghostscript & GTK3)
*   **Videos:** `.mp4`, `.mkv`, `avi`, `mov`, `mpeg`, `etc` (Need FFmpeg)

*Processing vectors/videos WILL FAIL without the required external tools!*

## 10. Troubleshooting Common Issues

*   **"Exiftool not found" / Errors on `.ai`/`.eps` / Errors on `.mp4`/`.mkv`:**
    *   **Using Installer:** These tools should be bundled. Ensure the installation completed without errors and the `tools/` subfolder exists with content. Check the application log for specific errors during execution.
    *   **Running from Source:** The respective tool (ExifTool, Ghostscript, FFmpeg) is likely not installed correctly or its location is not included in the system's PATH environment variable. Reinstall the tool or add it to your PATH.
*   **Errors on `.svg` (Windows):**
    *   **Using Installer:** The GTK3 Runtime installation might have failed or been skipped during setup. Try running the GTK3 installer found within the application's temporary setup files (if available) or download and install it manually.
    *   **Running from Source:** GTK3 Runtime is missing or misconfigured. Install GTK3 Runtime.
*   **API Errors (429, Auth):** Incorrect/inactive API key? Hitting rate limits? Check keys, increase `Delay`, reduce `Workers`, add more keys. Check internet.
    *   *Note:* Version 3.1.0+ includes enhanced internal handling for rate limits (smart key selection, adaptive cooldown, fallback models), but user configuration for workers and base delay is still important.
*   **Permission Errors:** Cannot write to Output Folder or config location? Choose different folder, check permissions.
*   **Freezes/Crashes:** Review the GUI log carefully for any error messages. Since the terminal output is suppressed, the GUI log is the primary source of information. Ensure all dependencies (Python and external) are correctly installed. If the log provides no clues, consider system resource issues or try reducing the number of `Workers`.

## 11. Project Structure Deep Dive

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

## 12. License Information

Licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See `LICENSE` file.

*   **Freedom:** Use, modify, distribute.
*   **Share Alike:** Modified source code must also be AGPLv3.
*   **Network Use:** If run modified on a server, users interacting remotely must get source code access.

Dependencies have their own licenses (MIT, Apache, LGPL, etc.). See `licenses/` folder. Comply with all, especially for external tools (ExifTool, Ghostscript, FFmpeg, GTK3).

## 13. Contributing

This is currently a solo project and my first one! As such, I'm focusing on learning and building. While I'm not set up for formal contributions right now, I'm always open to hearing feedback or suggestions. You can reach out via the contact details below (if provided).

## 14. Contact & Support

You can find me and discuss this project (or others) at: https://s.id/rj_auto_metadata

## 15. Support the Project

If you find this application helpful and would like to support its continued development, you can do so via the QR code below. Thanks!

![Support QR Code](assets/qr.jpg)

---

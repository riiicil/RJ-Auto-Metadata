# RJ Auto Metadata
# Copyright (C) 2025 Riiicil
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# src/utils/system_checks.py
import subprocess
import platform
import shutil
import os
import sys
from .logging import log_message 
GHOSTSCRIPT_PATH = None
FFMPEG_PATH = None

def _get_base_dir():
    executable_path = sys.executable
    base_dir = os.path.dirname(executable_path)
    if "python.exe" in executable_path.lower() or "python3" in executable_path.lower():
         try:
             script_dir = os.path.dirname(os.path.abspath(__file__))
             project_root = os.path.dirname(os.path.dirname(script_dir))
             log_message(f"Detected script mode (python executable). Base dir set relative to __file__: {project_root}", "info")
             return project_root
         except NameError:
              log_message("Could not determine script path using __file__, falling back to executable dir.", "warning")
              return base_dir # Fallback to executable dir
    else:
         # Likely running as a bundled executable
         log_message(f"Detected bundled mode. Base dir set relative to sys.executable: {base_dir}", "info")
         return base_dir

def _run_command(command_parts):
    """
    Helper function to run a command and check its success.
    Expects the full path to the executable as the first element.
    """
    executable = command_parts[0]
    if not os.path.exists(executable) or not os.path.isfile(executable):
         log_message(f"Executable '{executable}' does not exist or is not a file.")
         return False
    try:
        process = subprocess.run(
            command_parts, # command_parts[0] should be the full path now
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False, # Don't raise exception on non-zero exit
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0 # Hide console window on Windows
        )
        log_message(f"Ran command: {' '.join(command_parts)}, Return Code: {process.returncode}")
        if process.returncode != 0:
             # Log stderr specifically on failure
             stderr_output = process.stderr.strip()
             if stderr_output:
                 log_message(f"Command stderr: {stderr_output}", "error")
             else:
                 log_message(f"Command failed with no stderr output.", "warning")
        # Check if return code is 0 (success)
        return process.returncode == 0
    except FileNotFoundError: # Should ideally not happen if we check os.path.exists first
        log_message(f"Command '{executable}' not found, although it existed? Check permissions.")
        return False
    except Exception as e:
        log_message(f"Error running command {' '.join(command_parts)}: {e}")
        return False

def check_ghostscript():
    """Checks if Ghostscript is installed and accessible, prioritizing bundled version."""
    global GHOSTSCRIPT_PATH
    log_message("Checking for Ghostscript...")
    base_dir = _get_base_dir()
    gs_executable = None
    potential_names = []

    if platform.system() == "Windows":
        potential_names = ["gswin64c.exe", "gswin32c.exe", "gs.exe"]
        # Check bundled path first
        for name in potential_names:
            bundled_path = os.path.join(base_dir, "tools", "ghostscript", "bin", name)
            log_message(f"Checking bundled Ghostscript at: {bundled_path}")
            if os.path.exists(bundled_path):
                gs_executable = bundled_path
                log_message(f"Ghostscript found in bundled path!")
                break
    else: # Linux/macOS
        potential_names = ["gs"]
        # Check bundled path first (adjust path separators if needed for non-Windows)
        bundled_path = os.path.join(base_dir, "tools", "ghostscript", "bin", "gs")
        log_message(f"Checking bundled Ghostscript at: {bundled_path}")
        if os.path.exists(bundled_path):
             gs_executable = bundled_path
             log_message(f"Ghostscript found in bundled path!")

    # If not found bundled, check PATH
    if not gs_executable:
        log_message("Bundled Ghostscript not found, checking PATH...")
        for name in potential_names:
            path_executable = shutil.which(name)
            if path_executable:
                gs_executable = path_executable
                log_message(f"Ghostscript found in PATH!")
                break

    if gs_executable:
        GHOSTSCRIPT_PATH = gs_executable
        # log_message(f"Attempting to run: {GHOSTSCRIPT_PATH} -h")
        try:
            process = subprocess.run(
                [GHOSTSCRIPT_PATH, "-h"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            stdout_output = process.stdout.strip()
            stderr_output = process.stderr.strip()
            # log_message(f"Ghostscript check ('{GHOSTSCRIPT_PATH} -h') returned code: {process.returncode}")
            if stderr_output:
                log_message(f"Ghostscript check stderr: {stderr_output}")
            if process.returncode == 0 or "ghostscript" in stdout_output.lower() or "ghostscript" in stderr_output.lower():
                #  log_message(f"Ghostscript found at {gs_executable} and seems operational based on '-h' output.")
                 return True
            else:
                #  log_message(f"Ghostscript found at {gs_executable} but check command failed or output was unexpected (return code {process.returncode}). Might indicate missing dependencies.")
                 GHOSTSCRIPT_PATH = None # Clear path as it's unusable
                 return False
        except Exception as e:
            # log_message(f"Error running Ghostscript check command {GHOSTSCRIPT_PATH} -h: {e}")
            GHOSTSCRIPT_PATH = None # Clear path as it's unusable
            return False
    else:
        log_message("Could not find Ghostscript executable in bundled path or system PATH.")
        return False


def check_ffmpeg():
    global FFMPEG_PATH
    log_message("Checking for FFmpeg...")
    base_dir = _get_base_dir()
    ffmpeg_executable = None
    ffmpeg_name = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"

    # Check bundled path first
    bundled_path = os.path.join(base_dir, "tools", "ffmpeg", "bin", ffmpeg_name)
    log_message(f"Checking bundled FFmpeg at: {bundled_path}")
    if os.path.exists(bundled_path):
        ffmpeg_executable = bundled_path
        log_message(f"FFmpeg found in bundled path!")

    # If not found bundled, check PATH
    if not ffmpeg_executable:
        log_message("Bundled FFmpeg not found, checking PATH...")
        path_executable = shutil.which("ffmpeg")
        if path_executable:
            ffmpeg_executable = path_executable
            log_message(f"FFmpeg found in PATH!")

    if ffmpeg_executable:
        FFMPEG_PATH = ffmpeg_executable
        try:
            process = subprocess.run(
                [FFMPEG_PATH, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            # log_message(f"Ran command: {FFMPEG_PATH} -version, Return Code: {process.returncode}")
            if "ffmpeg version" in process.stderr.lower() or "ffmpeg version" in process.stdout.lower():
                 # log_message("FFmpeg version check successful (found version string).")
                 return True
            else:
                 # log_message(f"FFmpeg found at {FFMPEG_PATH} but version check failed (output didn't contain 'ffmpeg version').")
                 FFMPEG_PATH = None
                 return False
        except Exception as e:
            # log_message(f"Error running FFmpeg version check: {e}")
            FFMPEG_PATH = None
            return False
    else:
        log_message("Could not find FFmpeg executable in bundled path or system PATH.")
        return False

def check_gtk_dependencies():
    log_message("Checking for GTK dependencies (via cairocffi import)...")
    try:
        import cairocffi
        log_message("cairocffi imported successfully!")
        return True
    except ImportError as e:
        log_message(f"Failed to import cairocffi: {e}")
        log_message("This might indicate missing GTK3 runtime libraries, which are needed for SVG processing.")
        return False
    except Exception as e: # Catch potential DLLNotFoundErrors on Windows etc.
         log_message(f"An error occurred during cairocffi import check: {e}")
         log_message("This might indicate missing GTK3 runtime libraries (DLLs/SOs), needed for SVG processing.")
         return False

# --- Console Visibility (Windows Only) ---

def set_console_visibility(show):
    if platform.system() != "Windows":
        log_message("Console visibility control is only available on Windows.", "warning")
        return # Only works on Windows

    try:
        import ctypes
        SW_HIDE = 0
        SW_SHOW = 5

        console_wnd = ctypes.windll.kernel32.GetConsoleWindow()
        if console_wnd == 0:
            log_message("Could not get console window handle (maybe already hidden or no console?).", "warning")
            return # No console window found

        if show:
            ctypes.windll.user32.ShowWindow(console_wnd, SW_SHOW)
            log_message("Showing console window.", "info")
        else:
            ctypes.windll.user32.ShowWindow(console_wnd, SW_HIDE)
            log_message("Hiding console window.", "info")

    except ImportError:
         log_message("Could not import ctypes. Console visibility control unavailable.", "error")
    except AttributeError:
         log_message("Could not find necessary Windows API functions via ctypes.", "error")
    except Exception as e:
        log_message(f"Error controlling console visibility: {e}", "error")

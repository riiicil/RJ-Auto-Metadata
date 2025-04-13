# src/utils/system_checks.py
import subprocess
import platform
import shutil
import os
import sys
from .logging import log_message # Assuming log_message is in logging.py

# Global paths to store found executables
GHOSTSCRIPT_PATH = None
FFMPEG_PATH = None

def _get_base_dir():
    """
    Gets the base directory of the application.
    Prioritizes sys.executable for standalone builds, as sys.frozen seems unreliable here.
    """
    # For standalone executables (Nuitka/PyInstaller), sys.executable is the path to the exe
    # For scripts, it's the path to the python interpreter.
    executable_path = sys.executable
    base_dir = os.path.dirname(executable_path)

    # Simple check: If the base_dir looks like a Python installation folder,
    # we are likely running as a script, so revert to __file__ based path.
    # This is a heuristic and might need adjustment.
    if "python.exe" in executable_path.lower() or "python3" in executable_path.lower():
         try:
             # Running as a script - calculate path relative to this file
             script_dir = os.path.dirname(os.path.abspath(__file__))
             # Go up two levels from src/utils to the project root
             project_root = os.path.dirname(os.path.dirname(script_dir))
             log_message(f"Detected script mode (python executable). Base dir set relative to __file__: {project_root}", "info")
             return project_root
         except NameError:
              # __file__ might not be defined in some contexts (e.g., interactive)
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
                log_message(f"Found bundled Ghostscript: {gs_executable}")
                break
    else: # Linux/macOS
        potential_names = ["gs"]
        # Check bundled path first (adjust path separators if needed for non-Windows)
        bundled_path = os.path.join(base_dir, "tools", "ghostscript", "bin", "gs")
        log_message(f"Checking bundled Ghostscript at: {bundled_path}")
        if os.path.exists(bundled_path):
             gs_executable = bundled_path
             log_message(f"Found bundled Ghostscript: {gs_executable}")

    # If not found bundled, check PATH
    if not gs_executable:
        log_message("Bundled Ghostscript not found, checking PATH...")
        for name in potential_names:
            path_executable = shutil.which(name)
            if path_executable:
                gs_executable = path_executable
                log_message(f"Found Ghostscript in PATH: {gs_executable}")
                break

    if gs_executable:
        GHOSTSCRIPT_PATH = gs_executable
        # Try using '-h' which might be more robust than '--version' if dependencies are missing
        if _run_command([GHOSTSCRIPT_PATH, "-h"]):
             log_message(f"Ghostscript found at {gs_executable} and responded to '-h'.")
             return True
        else:
             # Found but command failed, clear the path
             GHOSTSCRIPT_PATH = None
             log_message(f"Ghostscript found at {gs_executable} but version check failed.")
             return False
    else:
        log_message("Could not find Ghostscript executable in bundled path or system PATH.")
        return False


def check_ffmpeg():
    """Checks if FFmpeg is installed and accessible, prioritizing bundled version."""
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
        log_message(f"Found bundled FFmpeg: {ffmpeg_executable}")

    # If not found bundled, check PATH
    if not ffmpeg_executable:
        log_message("Bundled FFmpeg not found, checking PATH...")
        path_executable = shutil.which("ffmpeg")
        if path_executable:
            ffmpeg_executable = path_executable
            log_message(f"Found FFmpeg in PATH: {ffmpeg_executable}")

    if ffmpeg_executable:
        FFMPEG_PATH = ffmpeg_executable
        # FFmpeg returns non-zero for -version, check stderr for version string instead
        try:
            process = subprocess.run(
                [FFMPEG_PATH, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            log_message(f"Ran command: {FFMPEG_PATH} -version, Return Code: {process.returncode}")
            if "ffmpeg version" in process.stderr.lower() or "ffmpeg version" in process.stdout.lower():
                 log_message("FFmpeg version check successful (found version string).")
                 return True
            else:
                 log_message(f"FFmpeg found at {FFMPEG_PATH} but version check failed (output didn't contain 'ffmpeg version').")
                 FFMPEG_PATH = None
                 return False
        except Exception as e:
            log_message(f"Error running FFmpeg version check: {e}")
            FFMPEG_PATH = None
            return False
    else:
        log_message("Could not find FFmpeg executable in bundled path or system PATH.")
        return False

def check_gtk_dependencies():
    """
    Checks for GTK dependencies by trying to import cairocffi.
    This is an indirect check, primarily for SVG processing.
    Returns True if import succeeds, False otherwise.
    """
    print("Checking for GTK dependencies (via cairocffi import)...")
    try:
        import cairocffi
        print("cairocffi imported successfully.")
        # You could potentially add more checks here if needed,
        # like trying to create a simple surface, but import is often sufficient.
        return True
    except ImportError as e:
        print(f"Failed to import cairocffi: {e}")
        print("This might indicate missing GTK3 runtime libraries, which are needed for SVG processing.")
        return False
    except Exception as e: # Catch potential DLLNotFoundErrors on Windows etc.
         log_message(f"An error occurred during cairocffi import check: {e}")
         log_message("This might indicate missing GTK3 runtime libraries (DLLs/SOs), needed for SVG processing.")
         return False

# src/utils/system_checks.py
import subprocess
import platform
import shutil

def _run_command(command_parts):
    """Helper function to run a command and check its success."""
    try:
        # Use shell=True cautiously, ensure command_parts are safe
        # For simple version checks like this, it's generally okay.
        # On Windows, find executable using shutil.which
        executable = shutil.which(command_parts[0])
        if not executable:
             print(f"Executable '{command_parts[0]}' not found in PATH.")
             return False

        process = subprocess.run(
            [executable] + command_parts[1:],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False, # Don't raise exception on non-zero exit
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0 # Hide console window on Windows
        )
        print(f"Ran command: {' '.join([executable] + command_parts[1:])}, Return Code: {process.returncode}")
        # Check if return code is 0 (success)
        return process.returncode == 0
    except FileNotFoundError:
        print(f"Command '{command_parts[0]}' not found. Is it installed and in PATH?")
        return False
    except Exception as e:
        print(f"Error running command {' '.join(command_parts)}: {e}")
        return False

def check_ghostscript():
    """Checks if Ghostscript is installed and accessible."""
    print("Checking for Ghostscript...")
    command = "gs"
    if platform.system() == "Windows":
        # Try common Windows executable names
        if shutil.which("gswin64c"):
            command = "gswin64c"
        elif shutil.which("gswin32c"):
            command = "gswin32c"
        elif shutil.which("gs"):
             command = "gs" # Fallback if others aren't found
        else:
             print("Could not find Ghostscript executable (gswin64c, gswin32c, gs) in PATH.")
             return False

    return _run_command([command, "--version"])

def check_ffmpeg():
    """Checks if FFmpeg is installed and accessible."""
    print("Checking for FFmpeg...")
    return _run_command(["ffmpeg", "-version"])

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
         print(f"An error occurred during cairocffi import check: {e}")
         print("This might indicate missing GTK3 runtime libraries (DLLs/SOs), needed for SVG processing.")
         return False

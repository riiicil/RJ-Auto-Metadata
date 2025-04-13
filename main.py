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

# main.py
import os
import sys
import tkinter as tk
# import tkinter.messagebox # No longer needed here
import traceback
# from src.utils.system_checks import check_ghostscript, check_ffmpeg, check_gtk_dependencies # Moved to app.py

def main():
    try:
        # Import modul setelah folder root ditambahkan ke path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        # NOTE: Dependency checks (Exiftool, Ghostscript, FFmpeg, GTK)
        # are now performed inside MetadataApp.__init__ in src/ui/app.py

        # Tandai jika berjalan sebagai executable
        # Import IS_NUITKA_EXECUTABLE only if needed here, otherwise handled in app.py?
        # Let's assume it might still be useful for other logic here or future expansion.
        from src.utils.file_utils import IS_NUITKA_EXECUTABLE # Keep for now
        if getattr(sys, 'frozen', False):
            print("Terdeteksi running sebagai executable.")
            IS_NUITKA_EXECUTABLE = True
            
        # Mulai aplikasi
        from src.ui.app import MetadataApp
        app = MetadataApp()
        app.mainloop()
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()
        
        try:
            tk.messagebox.showerror("Fatal Error", 
                f"Terjadi error fatal:\n{e}\nAplikasi akan ditutup.")
        except:
            pass
            
        sys.exit(1)

if __name__ == "__main__":
    main()

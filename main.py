# main.py
import os
import sys
print("Python path sebelum:", sys.path)
import tkinter as tk
import traceback

def main():
    try:
        # Import modul setelah folder root ditambahkan ke path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Check eksiftool
        from src.metadata.exif_writer import check_exiftool_exists
        print("Memeriksa ketersediaan Exiftool...")
        exiftool_ok = check_exiftool_exists()
        
        if not exiftool_ok:
            tk.messagebox.showerror("Error", 
                "Exiftool tidak ditemukan.\nPastikan sudah terinstal dan ada di PATH.")
            sys.exit(1)
            
        print("Exiftool ditemukan, memulai aplikasi...")
        
        # Tandai jika berjalan sebagai executable
        from src.utils.file_utils import IS_NUITKA_EXECUTABLE
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
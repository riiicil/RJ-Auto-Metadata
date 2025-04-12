# src/processing/vector_processing/format_svg_processing.py
import os
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from src.utils.logging import log_message
from src.api.gemini_api import check_stop_event

def convert_svg_to_jpg(svg_path, output_jpg_path, stop_event=None):
    """
    Mengkonversi file SVG ke JPG.
    
    Args:
        svg_path: Path file SVG sumber
        output_jpg_path: Path file JPG tujuan
        stop_event: Event threading untuk menghentikan proses
        
    Returns:
        Tuple (success, error_message): 
            - success: Boolean yang menunjukkan keberhasilan konversi
            - error_message: String pesan error (None jika sukses)
    """
    filename = os.path.basename(svg_path)
    log_message(f"  Mencoba konversi SVG ke JPG: {filename}")
    
    if check_stop_event(stop_event, f"  Konversi SVG dibatalkan: {filename}"):
        return False, f"Konversi dibatalkan: {filename}"
    
    try:
        # Konversi SVG ke ReportLab Graphics
        drawing = svg2rlg(svg_path)
        if drawing is None:
             return False, f"Gagal membaca atau parse SVG: {filename}"
        
        if check_stop_event(stop_event, f"  Konversi SVG dibatalkan setelah parse: {filename}"):
            return False, f"Konversi dibatalkan setelah parse: {filename}"
        
        # Render ReportLab Graphics ke file JPG
        renderPM.drawToFile(drawing, output_jpg_path, fmt="JPEG", bg=0xFFFFFF)
        
        if os.path.exists(output_jpg_path) and os.path.getsize(output_jpg_path) > 0:
            log_message(f"  Konversi SVG ke JPG berhasil: {os.path.basename(output_jpg_path)}")
            return True, None
        else:
            return False, f"Gagal render SVG ke JPG atau file output kosong: {filename}"
    except FileNotFoundError:
        return False, f"File SVG tidak ditemukan: {svg_path}"
    except Exception as e:
        error_type = type(e).__name__
        return False, f"Error saat konversi SVG ({error_type}): {e}"
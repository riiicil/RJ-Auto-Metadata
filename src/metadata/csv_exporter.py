# src/metadata/csv_exporter.py
import os
from src.utils.logging import log_message
from src.utils.file_utils import sanitize_csv_field, write_to_csv
from src.metadata.categories.for_adobestock import map_to_adobe_stock_category
from src.metadata.categories.for_shutterstock import map_to_shutterstock_category

def write_to_platform_csvs(csv_dir, filename, title, description, keywords, auto_kategori_enabled=True):
    """
    Menulis metadata ke file CSV untuk AdobeStock dan ShutterStock.
    
    Args:
        csv_dir: Direktori untuk menyimpan file CSV
        filename: Nama file gambar/video yang diproses
        title: Judul metadata
        description: Deskripsi metadata
        keywords: List keyword/tag
        auto_kategori_enabled: Flag untuk mengaktifkan penentuan kategori otomatis
        
    Returns:
        Boolean: True jika berhasil, False jika gagal
    """
    try:
        if not os.path.exists(csv_dir):
            os.makedirs(csv_dir, exist_ok=True)
        
        # Sanitasi data
        safe_filename = sanitize_csv_field(filename)
        safe_title = sanitize_csv_field(title)
        safe_description = sanitize_csv_field(description)
        
        if isinstance(keywords, list):
            ss_keywords = ', '.join([sanitize_csv_field(k) for k in keywords if k])
            as_keywords = ', '.join([sanitize_csv_field(k) for k in keywords if k])
        else:
            ss_keywords = sanitize_csv_field(keywords)
            as_keywords = sanitize_csv_field(keywords)
        
        # Tentukan kategori jika auto_kategori diaktifkan
        if auto_kategori_enabled:
            as_category = map_to_adobe_stock_category(safe_title, safe_description, keywords if isinstance(keywords, list) else [])
            ss_category = map_to_shutterstock_category(safe_title, safe_description, keywords if isinstance(keywords, list) else [])
            log_message(f"  Auto Kategori: Aktif (AS: {as_category}, SS: {ss_category})")
        else:
            as_category = ""
            ss_category = ""
            log_message(f"  Auto Kategori: Tidak Aktif")
        
        # Tulis data ke CSV AdobeStock
        as_csv_path = os.path.join(csv_dir, "adobe_stock_export.csv")
        as_header = ["Filename", "Title", "Keywords", "Category", "Releases"]
        as_data_row = [safe_filename, safe_title, as_keywords, as_category, ""]
        import time
        time.sleep(0.5)  # Jeda kecil untuk menghindari konflik file
        as_success = write_to_csv(as_csv_path, as_header, as_data_row)
        
        # Tulis data ke CSV ShutterStock
        ss_csv_path = os.path.join(csv_dir, "shutterstock_export.csv")
        ss_header = ["Filename", "Description", "Keywords", "Categories", "Editorial", "Mature content", "illustration"]
        ss_data_row = [safe_filename, safe_description or safe_title, ss_keywords, ss_category, "no", "", ""]
        time.sleep(0.5)  # Jeda kecil untuk menghindari konflik file
        ss_success = write_to_csv(ss_csv_path, ss_header, ss_data_row)
        
        return as_success and ss_success
    except Exception as e:
        log_message(f"  Error menulis ke CSV platform: {e}")
        return False
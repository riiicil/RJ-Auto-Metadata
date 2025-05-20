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

# src/metadata/csv_exporter.py
import os
import re
from src.utils.logging import log_message
from src.utils.file_utils import sanitize_csv_field, write_to_csv
from src.metadata.categories.for_adobestock import map_to_adobe_stock_category
from src.metadata.categories.for_shutterstock import map_to_shutterstock_category

def write_to_platform_csvs(csv_dir, filename, title, description, keywords, auto_kategori_enabled=True, is_vector=False, max_keywords=49):
    """
    Menulis metadata ke file CSV untuk AdobeStock dan ShutterStock.
    
    Args:
        csv_dir: Direktori untuk menyimpan file CSV
        filename: Nama file gambar/video yang diproses
        title: Judul metadata
        description: Deskripsi metadata
        keywords: List keyword/tag
        auto_kategori_enabled: Flag untuk mengaktifkan penentuan kategori otomatis
        is_vector: Boolean, True jika file asli adalah vektor (eps, ai, svg)
        max_keywords: Maximum number of keywords to include
        
    Returns:
        Boolean: True jika berhasil, False jika gagal
    """
    try:
        if not os.path.exists(csv_dir):
            os.makedirs(csv_dir, exist_ok=True)
        
        # Sanitasi data
        safe_filename = sanitize_csv_field(filename)
        # Jika title/dll dict hasil AI, ambil fieldnya
        as_category = ""
        ss_category = ""
        if isinstance(title, dict):
            meta = title
            safe_title = sanitize_csv_field(meta.get("title", ""))
            safe_description = sanitize_csv_field(meta.get("description", ""))
            keywords_val = meta.get("tags", [])
            if isinstance(keywords_val, list):
                ss_keywords = ', '.join([sanitize_csv_field(k) for k in keywords_val if k])
                as_keywords = ', '.join([sanitize_csv_field(k) for k in keywords_val if k])
            else:
                ss_keywords = sanitize_csv_field(keywords_val)
                as_keywords = sanitize_csv_field(keywords_val)
            # Ambil kategori dari hasil AI jika ada
            as_cat_ai = meta.get("as_category", "")
            ss_cat_ai = meta.get("ss_category", "")
            # Untuk AS, ambil hanya angka di depan (misal '5. The Environment' -> '5')
            if as_cat_ai:
                match = re.match(r"(\d+)", as_cat_ai)
                if match:
                    as_category = match.group(1)
            if ss_cat_ai:
                ss_category = sanitize_csv_field(ss_cat_ai)
        else:
            safe_title = sanitize_csv_field(title)
            safe_description = sanitize_csv_field(description)
            if isinstance(keywords, list):
                ss_keywords = ', '.join([sanitize_csv_field(k) for k in keywords if k])
                as_keywords = ', '.join([sanitize_csv_field(k) for k in keywords if k])
            else:
                ss_keywords = sanitize_csv_field(keywords)
                as_keywords = sanitize_csv_field(keywords)
        
        # --- Tambahan: deduplikasi dan limit keyword ---
        if isinstance(keywords, list):
            keywords = list(dict.fromkeys(keywords))
            keywords = keywords[:max_keywords]
        # --- END tambahan ---
        
        # Tentukan kategori jika auto_kategori diaktifkan
        if auto_kategori_enabled:
            # Jika hasil AI tidak ada, fallback ke rule-based
            if not as_category:
                as_category = map_to_adobe_stock_category(safe_title, safe_description, keywords if isinstance(keywords, list) else [])
            if not ss_category:
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
        # Set illustration to "yes" if is_vector is True, otherwise empty string
        illustration_value = "yes" if is_vector else ""
        ss_data_row = [safe_filename, safe_description or safe_title, ss_keywords, ss_category, "no", "", illustration_value]
        time.sleep(0.5)  # Jeda kecil untuk menghindari konflik file
        ss_success = write_to_csv(ss_csv_path, ss_header, ss_data_row)
        
        return as_success and ss_success
    except Exception as e:
        log_message(f"  Error menulis ke CSV platform: {e}")
        return False

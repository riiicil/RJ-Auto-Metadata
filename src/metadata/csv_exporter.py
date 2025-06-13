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

def sanitize_adobe_stock_title(title):
    """
    Sanitize title untuk Adobe Stock:
    - Tambah titik di akhir
    - Colon (:) boleh tetap
    - Sanitize karakter selain hyphen (-) dan colon (:)
    """
    if not title:
        return ""
    
    # Basic cleanup
    sanitized = re.sub(r'[\r\n\t]+', ' ', str(title))
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    # Remove special characters except hyphen and colon
    sanitized = re.sub(r'[^\w\s\-:]', '', sanitized)
    
    # Add period at the end if not already there
    if sanitized and not sanitized.endswith('.'):
        sanitized += '.'
    
    return sanitized

def sanitize_adobe_stock_keywords(keywords):
    """
    Sanitize keywords untuk Adobe Stock:
    - Hyphen (-) boleh tetap
    - Sanitize karakter selain hyphen
    """
    if isinstance(keywords, list):
        sanitized_list = []
        for keyword in keywords:
            if keyword:
                # Basic cleanup
                clean_kw = re.sub(r'[\r\n\t]+', ' ', str(keyword))
                clean_kw = re.sub(r'\s+', ' ', clean_kw).strip()
                # Remove special characters except hyphen
                clean_kw = re.sub(r'[^\w\s\-]', '', clean_kw)
                if clean_kw:
                    sanitized_list.append(clean_kw)
        return ', '.join(sanitized_list)
    else:
        # String keywords
        clean_kw = re.sub(r'[\r\n\t]+', ' ', str(keywords))
        clean_kw = re.sub(r'\s+', ' ', clean_kw).strip()
        clean_kw = re.sub(r'[^\w\s\-,]', '', clean_kw)
        return clean_kw

def sanitize_vecteezy_title(title):
    """
    Sanitize title untuk Vecteezy:
    - Tambah titik di akhir
    - Colon (:) ganti jadi hyphen (-)
    - Sanitize karakter selain hyphen (-)
    """
    if not title:
        return ""
    
    # Basic cleanup
    sanitized = re.sub(r'[\r\n\t]+', ' ', str(title))
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    # Replace colon with hyphen
    sanitized = sanitized.replace(':', ' -')
    
    # Remove special characters except hyphen
    sanitized = re.sub(r'[^\w\s\-]', '', sanitized)
    
    # Add period at the end if not already there
    if sanitized and not sanitized.endswith('.'):
        sanitized += '.'
    
    return sanitized

def sanitize_vecteezy_keywords(keywords):
    """
    Sanitize keywords untuk Vecteezy:
    - Sanitize SEMUA karakter khusus
    - Hapus kata "vector"
    """
    if isinstance(keywords, list):
        sanitized_list = []
        for keyword in keywords:
            if keyword:
                # Basic cleanup
                clean_kw = re.sub(r'[\r\n\t]+', ' ', str(keyword))
                clean_kw = re.sub(r'\s+', ' ', clean_kw).strip().lower()
                # Remove ALL special characters
                clean_kw = re.sub(r'[^\w\s]', '', clean_kw)
                # Remove "vector" word (including compound words)
                clean_kw = re.sub(r'\bvector\b', '', clean_kw, flags=re.IGNORECASE)
                clean_kw = re.sub(r'vector', '', clean_kw, flags=re.IGNORECASE)  # Remove vector from compound words
                clean_kw = re.sub(r'\s+', ' ', clean_kw).strip()
                if clean_kw:
                    sanitized_list.append(clean_kw)
        return ', '.join(sanitized_list)
    else:
        # String keywords
        clean_kw = re.sub(r'[\r\n\t]+', ' ', str(keywords))
        clean_kw = re.sub(r'\s+', ' ', clean_kw).strip()
        # Remove ALL special characters
        clean_kw = re.sub(r'[^\w\s,]', '', clean_kw)
        # Remove "vector" word (including compound words)
        clean_kw = re.sub(r'\bvector\b', '', clean_kw, flags=re.IGNORECASE)
        clean_kw = re.sub(r'vector', '', clean_kw, flags=re.IGNORECASE)  # Remove vector from compound words
        clean_kw = re.sub(r'\s+', ' ', clean_kw).strip()
        return clean_kw

def write_123rf_csv(csv_path, filename, description, keywords):
    """
    Menulis CSV khusus untuk 123RF dengan format header yang tepat.
    Header: oldfilename,"123rf_filename","description","keywords","country"
    """
    csv_dir = os.path.dirname(csv_path)
    if not os.path.exists(csv_dir):
        try:
            os.makedirs(csv_dir)
        except Exception as e:
            log_message(f"Error: Gagal membuat direktori CSV untuk 123RF: {e}")
            return False
    
    file_exists = os.path.isfile(csv_path)
    try:
        with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            if not file_exists or os.path.getsize(csv_path) == 0:
                # Header khusus dengan format yang diinginkan
                csvfile.write('oldfilename,"123rf_filename","description","keywords","country"\n')
            
            # Data row - escape quotes dalam data jika ada
            safe_filename = filename.replace('"', '""')
            safe_description = description.replace('"', '""')
            safe_keywords = keywords.replace('"', '""')
            
            csvfile.write(f'{safe_filename},"","{safe_description}","{safe_keywords}","ID"\n')
        return True
    except Exception as e:
        log_message(f"Error menulis ke CSV 123RF: {e}")
        return False

def write_vecteezy_csv(csv_path, filename, title, description, keywords):
    """
    Menulis CSV khusus untuk Vecteezy dengan filename tanpa quotes.
    Format: filename,title,"description","keywords",pro,
    """
    csv_dir = os.path.dirname(csv_path)
    if not os.path.exists(csv_dir):
        try:
            os.makedirs(csv_dir)
        except Exception as e:
            log_message(f"Error: Gagal membuat direktori CSV untuk Vecteezy: {e}")
            return False
    
    file_exists = os.path.isfile(csv_path)
    try:
        with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            if not file_exists or os.path.getsize(csv_path) == 0:
                # Header standard
                csvfile.write('Filename,Title,Description,Keywords,License,Id\n')
            
            # Data row - filename tanpa quotes, lainnya dengan quotes jika perlu
            safe_filename = filename.replace('"', '""')
            safe_title = title.replace('"', '""')
            safe_description = description.replace('"', '""')
            safe_keywords = keywords.replace('"', '""')
            
            csvfile.write(f'{safe_filename},{safe_title},"{safe_description}","{safe_keywords}",pro,\n')
        return True
    except Exception as e:
        log_message(f"Error menulis ke CSV Vecteezy: {e}")
        return False

def write_to_platform_csvs(csv_dir, filename, title, description, keywords, auto_kategori_enabled=True, is_vector=False, max_keywords=49):
    """
    Menulis metadata ke file CSV untuk semua platform yang didukung.
    Platform yang didukung: AdobeStock, ShutterStock, 123RF, Vecteezy, Depositphotos
    
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
        
        # Tulis data ke CSV AdobeStock (dengan sanitization khusus)
        as_csv_path = os.path.join(csv_dir, "adobe_stock_export.csv")
        as_header = ["Filename", "Title", "Keywords", "Category", "Releases"]
        # Apply Adobe Stock specific sanitization
        as_title_clean = sanitize_adobe_stock_title(safe_title)
        as_keywords_clean = sanitize_adobe_stock_keywords(keywords if isinstance(keywords, list) else as_keywords)
        as_data_row = [safe_filename, as_title_clean, as_keywords_clean, as_category, ""]
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
        
        # Tulis data ke CSV 123RF (dengan format header khusus)
        rf_csv_path = os.path.join(csv_dir, "123rf_export.csv")
        rf_success = write_123rf_csv(rf_csv_path, safe_filename, safe_description or safe_title, as_keywords)
        time.sleep(0.5)  # Jeda kecil untuk menghindari konflik file
        
        # Tulis data ke CSV Vecteezy (dengan format khusus tanpa quotes di filename)
        vz_csv_path = os.path.join(csv_dir, "vecteezy_export.csv")
        # Apply Vecteezy specific sanitization
        vz_title_clean = sanitize_vecteezy_title(safe_title)
        vz_keywords_clean = sanitize_vecteezy_keywords(keywords if isinstance(keywords, list) else as_keywords)
        vz_success = write_vecteezy_csv(vz_csv_path, safe_filename, vz_title_clean, safe_description or safe_title, vz_keywords_clean)
        time.sleep(0.5)  # Jeda kecil untuk menghindari konflik file
        
        # Tulis data ke CSV Depositphotos
        dp_csv_path = os.path.join(csv_dir, "depositphotos_export.csv")
        dp_header = ["Filename", "description", "Keywords", "Nudity", "Editorial"]
        dp_data_row = [safe_filename, safe_description or safe_title, as_keywords, "no", "no"]
        time.sleep(0.5)  # Jeda kecil untuk menghindari konflik file
        dp_success = write_to_csv(dp_csv_path, dp_header, dp_data_row)
        
        # Return True jika semua platform berhasil
        all_success = as_success and ss_success and rf_success and vz_success and dp_success
        
        # Log status untuk platform baru
        if rf_success and vz_success and dp_success:
            log_message(f"  CSV Export: Berhasil untuk semua 5 platform (AS, SS, 123RF, Vecteezy, Depositphotos)")
        else:
            failed_platforms = []
            if not rf_success: failed_platforms.append("123RF")
            if not vz_success: failed_platforms.append("Vecteezy") 
            if not dp_success: failed_platforms.append("Depositphotos")
            if failed_platforms:
                log_message(f"  CSV Export: Gagal untuk platform: {', '.join(failed_platforms)}")
        
        return all_success
    except Exception as e:
        log_message(f"  Error menulis ke CSV platform: {e}")
        return False

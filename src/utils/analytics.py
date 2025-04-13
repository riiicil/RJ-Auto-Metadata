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

# src/utils/analytics.py
import threading
import requests
from src.config.config import ANALYTICS_URL
from src.utils.logging import log_message

def send_analytics_event(installation_id, event_name, app_version, params={}):
    """
    Fungsi untuk mengirim event analytics ke Firebase.
    
    Args:
        installation_id: ID unik instalasi
        event_name: Nama event yang akan dikirim
        app_version: Versi aplikasi saat ini
        params: Parameter tambahan untuk event
    """
    if not installation_id or not ANALYTICS_URL:
        return False
    
    # Siapkan payload event
    payload = {
        "client_id": installation_id,
        "non_personalized_ads": False,
        "events": [{
            "name": event_name,
            "params": {
                # Parameter standar yang berguna
                "app_version": app_version,
                "engagement_time_msec": "100", 
                # Menggabungkan parameter tambahan
                **params 
            }
        }]
    }

    # Kirim dalam thread terpisah
    thread = threading.Thread(target=_do_send_analytics, args=(payload,), daemon=True)
    thread.start()
    return True

def _do_send_analytics(payload):
    """
    Implementasi internal untuk mengirim data analytics.
    """
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            ANALYTICS_URL,
            headers=headers,
            json=payload,
            timeout=10
        )
        
        # Cek status respons (opsional)
        if response.status_code != 204:
            log_message(f"Analytics send failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        log_message(f"Gagal mengirim analytics (network error): {e}")
    except Exception as e:
        log_message(f"Gagal mengirim analytics (unexpected error): {e}")
        
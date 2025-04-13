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

# src/config/config.py

# Default values (kosong untuk keamanan)
MEASUREMENT_ID = ""
API_SECRET = ""
ANALYTICS_URL = ""

try:
    from src.config.firebase_config import MEASUREMENT_ID, API_SECRET
    if MEASUREMENT_ID and API_SECRET:
        ANALYTICS_URL = f"https://www.google-analytics.com/mp/collect?measurement_id={MEASUREMENT_ID}&api_secret={API_SECRET}"
except ImportError:
    print("Firebase config tidak ditemukan, analytics tidak akan berfungsi")

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

# src/utils/logging.py

# Global handler untuk fungsi log
_log_handler = None

def set_log_handler(handler):
    """
    Mengatur handler untuk log messages
    Handler harus menerima dua parameter: message dan tag
    """
    global _log_handler
    _log_handler = handler

def log_message(message, tag=None):
    """
    Fungsi dasar untuk logging pesan.
    Jika handler tersedia, pesan diteruskan ke handler.
    Jika tidak, pesan hanya dicetak ke konsol.
    
    Args:
        message: Pesan yang akan dilog
        tag: Tag opsional untuk kategori pesan (info, warning, error, dll.)
    """
    # Cetak ke terminal
    print(message)
    
    # Teruskan ke handler jika tersedia
    if _log_handler is not None:
        _log_handler(message, tag)
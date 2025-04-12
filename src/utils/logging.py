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
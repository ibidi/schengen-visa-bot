import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logger(name):
    # Log dosyası için klasör oluştur
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Log dosyası adını tarih ile oluştur
    log_file = os.path.join(log_dir, f'visa_bot_{datetime.now().strftime("%Y%m%d")}.log')

    # Logger'ı yapılandır
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Dosyaya yazma için handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Konsola yazma için handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Format belirle
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(message)s'
        '\nFile "%(pathname)s", line %(lineno)d'
        '\n-------------------'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Handler'ları logger'a ekle
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

import os
from dotenv import load_dotenv
from pathlib import Path

# .env dosyasını yükle
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Telegram Bot Token'ı
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# VFS Global hesap bilgileri
USER_EMAIL = os.getenv('USER_EMAIL')
USER_PASSWORD = os.getenv('USER_PASSWORD')

# İzin verilen kullanıcılar
ALLOWED_USERS = {int(user_id.strip()) for user_id in os.getenv('ALLOWED_USERS', '').split(',')}
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID'))

# URL'ler
BASE_URL = "https://visa.vfsglobal.com/tur/tr/pol"
LOGIN_URL = f"{BASE_URL}/login"
DASHBOARD_URL = f"{BASE_URL}/dashboard"
APPOINTMENT_URL = f"{BASE_URL}/book-appointment"

# Randevu kontrol aralığı (saniye)
CHECK_INTERVAL = 60  # Her dakika kontrol et

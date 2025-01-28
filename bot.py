import os
import logging
import asyncio
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import json

# Loglama ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# .env dosyasını yükle
from dotenv import load_dotenv
load_dotenv()

# Telegram bot token'ı
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')  # Admin kullanıcı ID'si

# Global değişkenler
USERS = set()
VFS_URL = "https://visa.vfsglobal.com/tur/tr/pol/login"
CHECK_INTERVAL = 300  # 5 dakika

# Session objesi
session = requests.Session()

async def login_vfs():
    """VFS Global'e giriş yapar"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        
        # Login sayfasını yükle
        logging.info("Login sayfası yükleniyor...")
        response = session.get(VFS_URL, headers=headers)
        
        if response.status_code != 200:
            logging.error(f"Login sayfası yüklenemedi. Status code: {response.status_code}")
            logging.error(f"Response: {response.text[:500]}...")  # İlk 500 karakteri logla
            return False, "Login sayfası yüklenemedi"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Sayfanın HTML yapısını logla
        logging.info("Sayfa yapısı analiz ediliyor...")
        forms = soup.find_all('form')
        logging.info(f"Bulunan form sayısı: {len(forms)}")
        
        # CSRF token'ı bul
        csrf_token = None
        csrf_input = soup.find('input', {'name': '_csrf'})
        if csrf_input:
            csrf_token = csrf_input.get('value')
        else:
            # Alternatif CSRF token arama yöntemleri
            meta_csrf = soup.find('meta', {'name': 'csrf-token'})
            if meta_csrf:
                csrf_token = meta_csrf.get('content')
            else:
                # JavaScript içinde CSRF token'ı ara
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'csrf' in script.string.lower():
                        logging.info(f"CSRF içeren script bulundu: {script.string[:200]}...")
        
        if not csrf_token:
            logging.error("CSRF token bulunamadı. Sayfa yapısı:")
            logging.error(f"Form içeriği: {forms[0].prettify() if forms else 'Form bulunamadı'}")
            return False, "CSRF token bulunamadı"
            
        logging.info(f"CSRF token bulundu: {csrf_token[:10]}...")
            
        # Login bilgileri
        login_data = {
            '_csrf': csrf_token,
            'username': os.getenv('VFS_USERNAME'),
            'password': os.getenv('VFS_PASSWORD'),
            'rememberMe': 'true'
        }
        
        # Login isteği gönder
        logging.info("Login isteği gönderiliyor...")
        login_response = session.post(VFS_URL, headers=headers, data=login_data)
        
        if login_response.status_code != 200:
            logging.error(f"Login başarısız. Status code: {login_response.status_code}")
            logging.error(f"Response: {login_response.text[:500]}...")
            return False, "Login başarısız"
            
        # Login başarısını kontrol et
        if "Hoş geldiniz" in login_response.text or "Welcome" in login_response.text:
            logging.info("Login işlemi başarılı!")
            return True, "Login başarılı"
        else:
            logging.error("Login başarısız - yanlış kullanıcı adı/şifre olabilir")
            return False, "Login başarısız - yanlış kullanıcı adı/şifre olabilir"
        
    except Exception as e:
        logging.error(f"Login sırasında hata oluştu: {str(e)}")
        import traceback
        logging.error(f"Hata detayı: {traceback.format_exc()}")
        return False, f"Login sırasında hata: {str(e)}"

async def test_vfs_connection(context: ContextTypes.DEFAULT_TYPE = None):
    """VFS bağlantısını test eder"""
    success, message = await login_vfs()
    status_message = f"🔄 VFS Bağlantı Testi:\n\n"
    status_message += f"✅ Başarılı\n" if success else f"❌ Başarısız\n"
    status_message += f"📝 Detay: {message}"
    
    if context and ADMIN_USER_ID:
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=status_message)
    return success, status_message

async def check_appointments(context: ContextTypes.DEFAULT_TYPE) -> None:
    """VFS Global'den randevuları kontrol eden fonksiyon"""
    try:
        # Önce login ol
        success, message = await login_vfs()
        if not success:
            logging.error(f"VFS Global'e giriş yapılamadı: {message}")
            return
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'tr,en-US;q=0.7,en;q=0.3',
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        # Randevu sayfasına git
        appointment_url = "https://visa.vfsglobal.com/tur/tr/pol/book-appointment"
        response = session.get(appointment_url, headers=headers)
        
        if response.status_code != 200:
            logging.error(f"Randevu sayfası yüklenemedi: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Mevcut randevuları kontrol et
        available_dates = soup.find_all('td', {'class': 'day available'})
        
        if available_dates:
            message = "🎉 Yeni randevular bulundu!\n\n"
            for date in available_dates:
                message += f"📅 Tarih: {date.text}\n"
            
            # Tüm kayıtlı kullanıcılara bildirim gönder
            for user_id in USERS:
                await context.bot.send_message(chat_id=user_id, text=message)
        else:
            logging.info("Uygun randevu bulunamadı")
    
    except Exception as e:
        logging.error(f"Randevu kontrolü sırasında hata oluştu: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot başlatıldığında çalışacak komut"""
    user_id = update.effective_user.id
    USERS.add(user_id)
    
    # VFS bağlantısını test et
    success, message = await test_vfs_connection()
    
    welcome_message = (
        "Merhaba! VFS Global vize randevu takip botuna hoş geldiniz.\n"
        "Size uygun randevular bulunduğunda bildirim alacaksınız.\n\n"
    )
    
    # VFS test sonucunu ekle
    welcome_message += message
    
    await update.message.reply_text(welcome_message)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kullanıcıyı takip listesinden çıkaran komut"""
    user_id = update.effective_user.id
    if user_id in USERS:
        USERS.remove(user_id)
    await update.message.reply_text("Randevu takibi durduruldu.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Yardım komutu"""
    help_text = """
    📌 Mevcut komutlar:
    /start - Botu başlat ve randevu takibini aktifleştir
    /stop - Randevu takibini durdur
    /help - Bu yardım mesajını göster
    /test - VFS bağlantısını test et
    
    ⚠️ Not: Bot çalışmaya başlamadan önce VFS Global hesap bilgilerinizi .env dosyasına eklemelisiniz.
    """
    await update.message.reply_text(help_text)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """VFS bağlantısını test etmek için komut"""
    await update.message.reply_text("🔄 VFS bağlantısı test ediliyor...")
    success, message = await test_vfs_connection()
    await update.message.reply_text(message)

def main() -> None:
    """Bot'un ana fonksiyonu"""
    # Initialize bot and application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("test", test_command))

    # Add job queue
    job_queue = application.job_queue
    job_queue.run_repeating(check_appointments, interval=CHECK_INTERVAL, first=0)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 
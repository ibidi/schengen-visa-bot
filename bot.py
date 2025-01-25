import logging
import asyncio
import json
import os
import ssl
import certifi
import platform
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from config import (
    TELEGRAM_TOKEN, CHECK_INTERVAL,
    USER_EMAIL, USER_PASSWORD, ALLOWED_USERS, ADMIN_USER_ID,
    BASE_URL, LOGIN_URL, DASHBOARD_URL, APPOINTMENT_URL
)
from logger import setup_logger

# SSL sertifika doğrulamasını devre dışı bırak
ssl._create_default_https_context = ssl._create_unverified_context

# Logger'ı yapılandır
logger = setup_logger('visa_bot')

# Aktif kullanıcılar ve tercihleri
active_users = set()
user_preferences = {}

def is_allowed_user(user_id: int) -> bool:
    """Kullanıcının yetkili olup olmadığını kontrol eder"""
    logger.info(f"Kullanıcı yetkisi kontrol ediliyor - User ID: {user_id}")
    logger.info(f"İzin verilen kullanıcılar: {ALLOWED_USERS}")
    logger.info(f"Admin ID: {ADMIN_USER_ID}")
    return user_id in ALLOWED_USERS or user_id == ADMIN_USER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot başlatıldığında çalışan komut"""
    user_id = update.effective_user.id
    logger.info(f"Start komutu alındı - User ID: {user_id}")
    
    if not is_allowed_user(user_id):
        await update.message.reply_text(
            "⛔️ Üzgünüm, bu botu kullanma yetkiniz yok.\n"
            "Lütfen bot yöneticisiyle iletişime geçin."
        )
        logger.warning(f"Yetkisiz kullanıcı erişim denemesi - User ID: {user_id}")
        return
    
    active_users.add(user_id)
    
    await update.message.reply_text(
        "👋 Hoş geldiniz! Ben VFS Global randevu botuyum.\n\n"
        "🔍 Sizin için sürekli randevu kontrolü yapacağım.\n\n"
        "⚙️ Randevu tercihlerinizi ayarlamak için /setpreferences komutunu kullanın.\n"
        "🛑 Botu durdurmak için /stop komutunu kullanın."
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botu durdurmak için komut"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    logger.info(f"Kullanıcı botu durdurdu - User ID: {user.id}, Username: {user.username}")
    
    if chat_id in active_users:
        active_users.remove(chat_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text="Bot durduruldu. Tekrar başlatmak için /start komutunu kullanabilirsiniz."
    )

async def set_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı tercihlerini ayarlamak için komut"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    logger.info(f"Kullanıcı tercihleri ayarlanmaya başlandı - User ID: {user.id}, Username: {user.username}")
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="Lütfen aşağıdaki bilgileri sırasıyla gönderin:\n"
             "1. Başvuru yapacağınız kişi sayısı (örn: 2)\n"
             "2. Tercih ettiğiniz şehir (örn: Istanbul)\n"
             "3. Tercih ettiğiniz tarih aralığı (örn: 2025-02-01 2025-03-01)"
    )
    
    user_preferences[chat_id] = {
        'step': 'waiting_applicant_count'
    }
    logger.debug(f"Kullanıcı tercihleri başlatıldı - Chat ID: {chat_id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı mesajlarını işle"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    text = update.message.text
    
    logger.debug(f"Gelen mesaj - User ID: {user.id}, Message: {text}")
    
    if chat_id in user_preferences:
        if user_preferences[chat_id]['step'] == 'waiting_applicant_count':
            try:
                applicant_count = int(text)
                user_preferences[chat_id]['applicant_count'] = applicant_count
                user_preferences[chat_id]['step'] = 'waiting_city'
                logger.info(f"Başvuran sayısı ayarlandı - User ID: {user.id}, Count: {applicant_count}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Tercih ettiğiniz şehri yazın (Istanbul/Ankara/Izmir):"
                )
            except ValueError:
                logger.warning(f"Geçersiz başvuran sayısı - User ID: {user.id}, Input: {text}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Lütfen geçerli bir sayı girin."
                )
        
        elif user_preferences[chat_id]['step'] == 'waiting_city':
            if text.lower() in ['istanbul', 'ankara', 'izmir']:
                user_preferences[chat_id]['city'] = text.lower()
                user_preferences[chat_id]['step'] = 'waiting_dates'
                logger.info(f"Şehir tercihi ayarlandı - User ID: {user.id}, City: {text.lower()}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Tercih ettiğiniz tarih aralığını yazın (örn: 2025-02-01 2025-03-01):"
                )
            else:
                logger.warning(f"Geçersiz şehir - User ID: {user.id}, Input: {text}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Lütfen geçerli bir şehir seçin (Istanbul/Ankara/Izmir)"
                )
        
        elif user_preferences[chat_id]['step'] == 'waiting_dates':
            try:
                start_date, end_date = text.split()
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
                user_preferences[chat_id]['date_range'] = (start_date, end_date)
                user_preferences[chat_id]['step'] = 'complete'
                
                logger.info(
                    f"Tarih aralığı ayarlandı - User ID: {user.id}, "
                    f"Start: {start_date}, End: {end_date}"
                )
                
                # Tercihleri göster ve onay iste
                prefs = user_preferences[chat_id]
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Tercihleriniz:\n"
                         f"Kişi sayısı: {prefs['applicant_count']}\n"
                         f"Şehir: {prefs['city']}\n"
                         f"Tarih aralığı: {prefs['date_range'][0]} - {prefs['date_range'][1]}\n\n"
                         f"Onaylıyor musunuz? (evet/hayır)"
                )
                user_preferences[chat_id]['step'] = 'waiting_confirmation'
            except (ValueError, IndexError):
                logger.warning(f"Geçersiz tarih formatı - User ID: {user.id}, Input: {text}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Lütfen geçerli bir tarih aralığı girin (örn: 2025-02-01 2025-03-01)"
                )
        
        elif user_preferences[chat_id]['step'] == 'waiting_confirmation':
            if text.lower() == 'evet':
                logger.info(f"Kullanıcı tercihleri onaylandı - User ID: {user.id}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Tercihleriniz kaydedildi. Uygun randevu bulunduğunda otomatik olarak alınacak."
                )
            else:
                logger.info(f"Kullanıcı tercihleri reddedildi - User ID: {user.id}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Tercihleri tekrar ayarlamak için /setpreferences komutunu kullanın."
                )
            del user_preferences[chat_id]

async def book_appointment(session, date, time):
    """Randevu alma işlemini gerçekleştir"""
    try:
        booking_data = {
            'center': 'istanbul',  # Şehir bilgisi sabit olarak İstanbul olarak ayarlandı
            'date': date,
            'time': time,
            'applicants': 1  # Başvuran sayısı sabit olarak 1 olarak ayarlandı
        }
        
        logger.debug(f"Randevu alma denemesi - Data: {booking_data}")
        
        async with session.post(f"{BASE_URL}/book-appointment", data=booking_data) as response:
            if response.status == 200:
                logger.info(f"Randevu başarıyla alındı - Date: {date}, Time: {time}")
                return True, "Randevu başarıyla alındı!"
            else:
                logger.error(f"Randevu alınamadı - Status: {response.status}")
                return False, "Randevu alınırken bir hata oluştu."
            
    except Exception as e:
        logger.error(f"Randevu alma hatası: {str(e)}", exc_info=True)
        return False, f"Randevu alınırken hata: {str(e)}"

async def check_appointments():
    """Randevu kontrolü yapar ve uygun randevu bulunursa bildirim gönderir."""
    try:
        # Chrome ayarlarını yapılandır
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--allow-insecure-localhost')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--remote-debugging-address=0.0.0.0')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # ChromeDriver'ı yapılandır
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 10)
        
        try:
            # Login sayfasına git
            logger.info("Login sayfası açılıyor...")
            driver.get(LOGIN_URL)
            
            # Login formunu doldur
            email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            
            email_input.send_keys(USER_EMAIL)
            password_input.send_keys(USER_PASSWORD)
            
            # Giriş yap
            submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            submit_button.click()
            
            # Dashboard'ın yüklenmesini bekle
            logger.info("Dashboard bekleniyor...")
            await asyncio.sleep(5)  # Sayfa yüklenmesi için bekle
            
            # Randevu sayfasına git
            logger.info("Randevu sayfasına gidiliyor...")
            driver.get(APPOINTMENT_URL)
            await asyncio.sleep(5)  # Sayfa yüklenmesi için bekle
            
            # Sayfanın HTML içeriğini al
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Randevu kontrolü
            available_slots = soup.find_all('div', class_='available-slot')
            if available_slots:
                for slot in available_slots:
                    date = slot.get('data-date', '')
                    time = slot.get('data-time', '')
                    if date and time:
                        # Randevu butonuna tıkla
                        slot_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"div[data-date='{date}'][data-time='{time}']")))
                        slot_element.click()
                        
                        # Randevu formunu doldur ve gönder
                        submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.submit-appointment")))
                        submit_button.click()
                        
                        await asyncio.sleep(2)
                        
                        # Başarı mesajını kontrol et
                        success_message = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".success-message")))
                        if success_message:
                            await notify_users(f"🎉 Randevu başarıyla alındı!\nTarih: {date}\nSaat: {time}")
                            return
            else:
                logger.info("Uygun randevu bulunamadı")
        
        finally:
            # Tarayıcıyı kapat
            driver.quit()
            
    except Exception as e:
        logger.error(f"Randevu kontrolü sırasında hata: {str(e)}")

async def schedule_checker():
    """Düzenli kontrol için zamanlayıcı"""
    logger.info("Randevu kontrol zamanlayıcısı başlatıldı")
    while True:
        try:
            logger.debug("Randevu kontrolü başlıyor...")
            await check_appointments()
            logger.debug("Randevu kontrolü tamamlandı")
        except Exception as e:
            logger.error("Kontrol sırasında hata", exc_info=True)
        finally:
            await asyncio.sleep(CHECK_INTERVAL)

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yeni kullanıcı ekle (sadece admin kullanabilir)"""
    user = update.effective_user
    
    if user.id != ADMIN_USER_ID:
        logger.warning(f"Yetkisiz kullanıcı admin komutu denedi - User ID: {user.id}")
        await update.message.reply_text("Bu komutu kullanma yetkiniz yok!")
        return

    try:
        new_user_id = int(context.args[0])
        if new_user_id not in ALLOWED_USERS:
            ALLOWED_USERS.append(new_user_id)
            logger.info(f"Yeni kullanıcı eklendi - Admin: {user.id}, New User: {new_user_id}")
            await update.message.reply_text(f"Kullanıcı {new_user_id} başarıyla eklendi!")
        else:
            await update.message.reply_text("Bu kullanıcı zaten ekli!")
    except (ValueError, IndexError):
        await update.message.reply_text("Kullanım: /add_user <user_id>")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı kaldır (sadece admin kullanabilir)"""
    user = update.effective_user
    
    if user.id != ADMIN_USER_ID:
        logger.warning(f"Yetkisiz kullanıcı admin komutu denedi - User ID: {user.id}")
        await update.message.reply_text("Bu komutu kullanma yetkiniz yok!")
        return

    try:
        user_id = int(context.args[0])
        if user_id in ALLOWED_USERS:
            ALLOWED_USERS.remove(user_id)
            logger.info(f"Kullanıcı kaldırıldı - Admin: {user.id}, Removed User: {user_id}")
            await update.message.reply_text(f"Kullanıcı {user_id} kaldırıldı!")
        else:
            await update.message.reply_text("Bu kullanıcı zaten listede değil!")
    except (ValueError, IndexError):
        await update.message.reply_text("Kullanım: /remove_user <user_id>")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İzin verilen kullanıcıları listele (sadece admin kullanabilir)"""
    user = update.effective_user
    
    if user.id != ADMIN_USER_ID:
        logger.warning(f"Yetkisiz kullanıcı admin komutu denedi - User ID: {user.id}")
        await update.message.reply_text("Bu komutu kullanma yetkiniz yok!")
        return

    users_list = "İzin verilen kullanıcılar:\n"
    for user_id in ALLOWED_USERS:
        users_list += f"- {user_id}\n"
    users_list += f"\nAdmin: {ADMIN_USER_ID}"
    
    await update.message.reply_text(users_list)

async def notify_users(message):
    for chat_id in active_users:
        await application.bot.send_message(chat_id=chat_id, text=message)

if __name__ == '__main__':
    logger.info("Bot başlatılıyor...")
    
    # Event loop'u oluştur
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Bot uygulamasını oluştur
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Komutları ekle
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('setpreferences', set_preferences))
    
    # Admin komutlarını ekle
    application.add_handler(CommandHandler('add_user', add_user))
    application.add_handler(CommandHandler('remove_user', remove_user))
    application.add_handler(CommandHandler('list_users', list_users))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Arka planda randevu kontrolünü başlat
    loop.create_task(schedule_checker())

    logger.info("Bot hazır, çalışmaya başlıyor...")
    # Botu başlat
    application.run_polling()

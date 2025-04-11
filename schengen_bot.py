#!/usr/bin/env python3
import os
import sys
import logging
import json
import asyncio
import aiohttp
from datetime import datetime
from pytz import timezone
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand

# Çevre değişkenlerini yükle
load_dotenv()

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Telegram bot ayarları
TELEGRAM_BOT_TOKEN = "TOKEN"
TELEGRAM_CHAT_ID = "user-chat-id"

# API URL
API_URL = "https://api.schengenvisaappointments.com/api/visa-list/?format=json"

# Ülke ve şehir bilgileri
COUNTRIES = {
    'France': 'Fransa',
    'Netherlands': 'Hollanda',
    'Ireland': 'İrlanda',
    'Malta': 'Malta',
    'Sweden': 'İsveç',
    'Czechia': 'Çekya',
    'Croatia': 'Hırvatistan',
    'Bulgaria': 'Bulgaristan',
    'Finland': 'Finlandiya',
    'Slovenia': 'Slovenya',
    'Denmark': 'Danimarka',
    'Norway': 'Norveç',
    'Estonia': 'Estonya',
    'Lithuania': 'Litvanya',
    'Luxembourg': 'Lüksemburg',
    'Ukraine': 'Ukrayna',
    'Latvia': 'Letonya'
}

CITIES = ['Ankara', 'Istanbul', 'Izmir', 'Antalya', 'Gaziantep', 'Bursa', 'Edirne']

class VisaBot:
    def __init__(self):
        self.app = None
        self.running = False
        self.current_check = None
        self.country = None
        self.city = None
        self.frequency = 5  # Varsayılan kontrol sıklığı (dakika)
        self.user_selections = {}

    def create_frequency_keyboard(self):
        """Kontrol sıklığı için butonlu klavye oluştur"""
        keyboard = [
            [InlineKeyboardButton(f"{i} Dakika", callback_data=f"freq_{i}") for i in range(1, 6)]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_country_keyboard(self):
        """Ülke seçimi için butonlu klavye oluştur"""
        keyboard = []
        row = []
        for i, (eng_name, tr_name) in enumerate(COUNTRIES.items(), 1):
            row.append(InlineKeyboardButton(tr_name, callback_data=f"country_{eng_name}"))
            if i % 3 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        return InlineKeyboardMarkup(keyboard)

    def create_city_keyboard(self):
        """Şehir seçimi için butonlu klavye oluştur"""
        keyboard = []
        row = []
        for i, city in enumerate(CITIES, 1):
            row.append(InlineKeyboardButton(city, callback_data=f"city_{city}"))
            if i % 3 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        return InlineKeyboardMarkup(keyboard)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Buton callback işleyicisi"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = str(update.effective_user.id)
            if user_id not in self.user_selections:
                self.user_selections[user_id] = {}

            data = query.data
            logger.info(f"Buton callback alındı: {data} - Kullanıcı: {user_id}")

            # İşlem başladığını kullanıcıya bildir
            await query.edit_message_text(f"⏳ İşleniyor... Lütfen bekleyin.")

            if data.startswith("freq_"):
                try:
                    self.frequency = int(data.split("_")[1])
                    logger.info(f"Kontrol sıklığı ayarlandı: {self.frequency} dakika")
                    
                    if self.running:
                        await self.stop_checking()
                        self.running = True
                        self.current_check = asyncio.create_task(self.check_appointments())
                    
                    await query.edit_message_text(f"✅ Kontrol sıklığı {self.frequency} dakika olarak ayarlandı.")
                except Exception as e:
                    logger.error(f"Sıklık ayarlama hatası: {str(e)}")
                    await query.edit_message_text(f"❌ Sıklık ayarlanırken hata oluştu: {str(e)}")
            
            elif data.startswith("country_"):
                try:
                    # Ülke seçimi işleniyor mesajı
                    logger.info(f"Ülke seçimi işleniyor: {data}")
                    
                    # Ülke kodunu ayıkla
                    parts = data.split("_", 1)
                    if len(parts) < 2:
                        raise ValueError(f"Geçersiz ülke verisi: {data}")
                        
                    selected_country_eng = parts[1]  # İngilizce ülke adını al
                    
                    # Ülke kodunun geçerliliğini kontrol et
                    if selected_country_eng not in COUNTRIES:
                        raise ValueError(f"Geçersiz ülke seçimi: {selected_country_eng}")
                    
                    selected_country_tr = COUNTRIES[selected_country_eng]  # Türkçe karşılığını al
                    logger.info(f"Seçilen ülke: {selected_country_tr} ({selected_country_eng})")
                    
                    # Kullanıcı seçimlerini güncelle
                    self.user_selections[user_id] = {"country": selected_country_eng}  # Önceki seçimleri temizle
                    self.country = selected_country_eng  # Ana değişkeni güncelle
                    
                    # Şehir seçimi için klavyeyi göster
                    await query.edit_message_text(
                        f"✅ {selected_country_tr} seçildi.\n🏢 Lütfen şehir seçin:",
                        reply_markup=self.create_city_keyboard()
                    )
                except Exception as e:
                    logger.error(f"Ülke seçimi hatası: {str(e)}")
                    await query.edit_message_text(
                        f"❌ Ülke seçimi sırasında bir hata oluştu: {str(e)}\nLütfen tekrar deneyin.",
                        reply_markup=self.create_country_keyboard()
                    )
            
            elif data.startswith("city_"):
                try:
                    # Şehir seçimi işleniyor mesajı
                    logger.info(f"Şehir seçimi işleniyor: {data}")
                    
                    # Şehir adını ayıkla
                    parts = data.split("_", 1)
                    if len(parts) < 2:
                        raise ValueError(f"Geçersiz şehir verisi: {data}")
                        
                    selected_city = parts[1]  # Şehir adını al
                    logger.info(f"Seçilen şehir: {selected_city}")
                    
                    # Kullanıcı seçimlerini güncelle
                    self.user_selections[user_id]["city"] = selected_city
                    
                    # Ülke seçimi yapılmış mı kontrol et
                    if "country" in self.user_selections[user_id]:
                        selected_country = self.user_selections[user_id]["country"]
                        logger.info(f"Randevu kontrolü başlatılıyor: {selected_country} - {selected_city}")
                        
                        await self.start_check_with_selections(
                            update,
                            selected_country,
                            selected_city
                        )
                    else:
                        logger.error(f"Ülke seçimi bulunamadı - Kullanıcı: {user_id}")
                        await query.edit_message_text("❌ Lütfen önce bir ülke seçin.")
                except Exception as e:
                    logger.error(f"Şehir seçimi hatası: {str(e)}")
                    await query.edit_message_text(
                        f"❌ Şehir seçimi sırasında bir hata oluştu: {str(e)}\nLütfen tekrar deneyin.",
                        reply_markup=self.create_city_keyboard()
                    )
            else:
                logger.warning(f"Bilinmeyen callback verisi: {data}")
                await query.edit_message_text(f"❌ Bilinmeyen işlem: {data}")
                
        except Exception as e:
            logger.error(f"Callback işleme hatası: {str(e)}")
            try:
                await update.callback_query.edit_message_text(f"❌ İşlem sırasında bir hata oluştu: {str(e)}")
            except Exception:
                logger.error("Hata mesajı gönderilemedi")


    async def start_check_with_selections(self, update, country, city):
        """Seçimlerle randevu kontrolünü başlat"""
        try:
            # Ülke ve şehir bilgilerini kontrol et
            if not country or not city:
                error_msg = "Ülke veya şehir bilgisi eksik"
                logger.error(f"Randevu kontrolü başlatılamadı: {error_msg}")
                
                if hasattr(update, "callback_query"):
                    await update.callback_query.edit_message_text(f"❌ {error_msg}. Lütfen tekrar deneyin.")
                else:
                    await update.message.reply_text(f"❌ {error_msg}. Lütfen tekrar deneyin.")
                return
                
            # Eğer zaten çalışan bir kontrol varsa durdur
            if self.running:
                logger.info(f"Önceki kontrol durduruluyor: {self.country} - {self.city}")
                await self.stop_checking()

            # Yeni kontrol için değişkenleri ayarla
            self.country = country
            self.city = city
            self.running = True
            
            # Ülke adını Türkçe'ye çevir
            country_tr = COUNTRIES.get(country, country)
            
            logger.info(f"Randevu kontrolü başlatılıyor: {country_tr} - {city}")

            # Kullanıcıya bilgi mesajı
            message = (
                f"✅ {country_tr} için {city} şehrinde randevu kontrolü başlatıldı.\n"
                f"⏱ Kontrol sıklığını seçin:"
            )
            
            # Mesajı gönder
            if hasattr(update, "callback_query"):
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=self.create_frequency_keyboard()
                )
            else:
                await update.message.reply_text(
                    message,
                    reply_markup=self.create_frequency_keyboard()
                )

            # Kontrol görevini başlat
            self.current_check = asyncio.create_task(self.check_appointments())
            logger.info(f"Randevu kontrol görevi başlatıldı: {country_tr} - {city}")
            
            # Telegram chat'e bilgi mesajı gönder
            try:
                start_message = (
                    f"🔄 Randevu kontrolü başlatıldı\n"
                    f"📍 Ülke: {country_tr}\n"
                    f"🏢 Şehir: {city}\n"
                    f"⏱ Kontrol sıklığı: {self.frequency} dakika\n"
                    f"⏰ Başlangıç: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                )
                await self.app.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=start_message
                )
            except Exception as e:
                logger.error(f"Başlangıç mesajı gönderme hatası: {str(e)}")
                
        except Exception as e:
            logger.error(f"Randevu kontrolü başlatma hatası: {str(e)}")
            error_message = f"❌ Randevu kontrolü başlatılırken bir hata oluştu: {str(e)}"
            
            try:
                if hasattr(update, "callback_query"):
                    await update.callback_query.edit_message_text(error_message)
                else:
                    await update.message.reply_text(error_message)
            except Exception:
                logger.error("Hata mesajı gönderilemedi")
                
            # Hata durumunda çalışma durumunu sıfırla
            self.running = False
            self.current_check = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bot başlatma komutu"""
        welcome_message = (
            "🌟 Schengen Vize Randevu Kontrol Botuna Hoş Geldiniz! 🌟\n\n"
            "Kullanılabilir komutlar:\n"
            "/start - Bot bilgisi\n"
            "/check - Randevu kontrolünü başlat\n"
            "/stop - Aktif kontrolü durdur\n"
            "/status - Mevcut durum bilgisi\n"
            "/help - Yardım menüsü"
        )
        await update.message.reply_text(welcome_message)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Yardım komutu"""
        help_text = (
            "📋 Komut Listesi:\n\n"
            "1. Randevu Kontrolü Başlatma:\n"
            "/check Fransa Istanbul\n\n"
            "2. Kontrol Durdurma:\n"
            "/stop\n\n"
            "3. Durum Kontrolü:\n"
            "/status\n\n"
            "Desteklenen Ülkeler:\n"
            + ", ".join(COUNTRIES.values()) + "\n\n"
            "Desteklenen Şehirler:\n"
            + ", ".join(CITIES)
        )
        await update.message.reply_text(help_text)

    async def check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Randevu kontrolünü başlat"""
        await update.message.reply_text(
            "🌍 Lütfen ülke seçin:",
            reply_markup=self.create_country_keyboard()
        )

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Randevu kontrolünü durdur"""
        if not self.running:
            await update.message.reply_text("ℹ️ Aktif kontrol bulunmuyor.")
            return

        await self.stop_checking()
        await update.message.reply_text("✅ Randevu kontrolü durduruldu.")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mevcut durum bilgisi"""
        if not self.running:
            await update.message.reply_text("ℹ️ Aktif kontrol bulunmuyor.")
            return

        status_message = (
            f"📍 Kontrol Edilen Ülke: {self.country}\n"
            f"🏢 Kontrol Edilen Şehir: {self.city}\n"
            f"⏱ Kontrol Sıklığı: {self.frequency} dakika\n"
            "✅ Durum: Aktif"
        )
        await update.message.reply_text(status_message)

    async def stop_checking(self):
        """Kontrol görevini durdur"""
        self.running = False
        if self.current_check:
            self.current_check.cancel()
            try:
                await self.current_check
            except asyncio.CancelledError:
                pass
        self.current_check = None

    async def check_appointments(self):
        """Randevu kontrolü yap"""
        check_count = 0
        last_error_time = None
        error_count = 0
        first_check = True
        
        while self.running:
            check_count += 1
            try:
                logger.info(f"Randevu kontrolü yapılıyor: {self.country} - {self.city} (Kontrol #{check_count})")
                
                # Sadece ilk kontrolde bildirim gönder, diğer kontrollerde gönderme
                if first_check:
                    first_check = False
                    # İlk kontrol bildirimini atla çünkü start_check_with_selections'da zaten gönderiliyor
                    logger.info("İlk kontrol - bildirim atlanıyor çünkü başlangıç bildirimi zaten gönderildi")
                    # Bildirim gönderme kodu kaldırıldı
                
                # API'ye istek gönder
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(API_URL, timeout=30) as response:
                            if response.status != 200:
                                error_msg = f"API hatası: HTTP {response.status}"
                                logger.error(error_msg)
                                
                                # Sürekli hata durumunda kullanıcıya bildir
                                error_count += 1
                                if error_count >= 3:
                                    await self.app.bot.send_message(
                                        chat_id=TELEGRAM_CHAT_ID,
                                        text=f"⚠️ API bağlantı sorunu: {error_msg}\nKontroller devam ediyor."
                                    )
                                    error_count = 0
                                continue

                            # Başarılı yanıt, hata sayacını sıfırla
                            error_count = 0
                            
                            try:
                                data = await response.json()
                                logger.info(f"API'den {len(data)} randevu bilgisi alındı")
                            except json.JSONDecodeError as e:
                                logger.error(f"API yanıtı JSON formatında değil: {str(e)}")
                                continue
                            
                            available_appointments = []

                            # Randevuları filtrele
                            for appointment in data:
                                try:
                                    source = appointment.get('source_country')
                                    mission = appointment.get('mission_country', '')
                                    center = appointment.get('center_name', '')
                                    
                                    # Ülke ve şehir kontrolü
                                    if (
                                        source == 'Turkiye'
                                        and self.country == mission
                                        and center and self.city and self.city.lower() in center.lower()
                                    ):
                                        # Randevu tarihini Türkiye saat dilimine çevir
                                        appointment_date = appointment.get('appointment_date')
                                        if appointment_date:
                                            try:
                                                date_obj = datetime.fromisoformat(appointment_date.replace('Z', '+00:00'))
                                                tr_timezone = timezone('Europe/Istanbul')
                                                tr_date = date_obj.astimezone(tr_timezone)
                                                formatted_date = tr_date.strftime('%d.%m.%Y %H:%M')
                                            except ValueError as e:
                                                logger.warning(f"Tarih çevirme hatası: {str(e)}")
                                                formatted_date = appointment_date
                                        else:
                                            formatted_date = 'Tarih bilgisi yok'
                                        
                                        # Randevu bilgilerini ekle
                                        available_appointments.append({
                                            'date': formatted_date,
                                            'center': center,
                                            'category': appointment.get('visa_category', 'Belirtilmemiş'),
                                            'link': appointment.get('book_now_link', '#')
                                        })
                                except Exception as e:
                                    logger.warning(f"Randevu işleme hatası: {str(e)}")
                                    continue

                            # Bulunan randevuları bildir
                            if available_appointments:
                                logger.info(f"{len(available_appointments)} uygun randevu bulundu")
                                for appt in available_appointments:
                                    message = (
                                        f"🎉 {self.country} için randevu bulundu!\n\n"
                                        f"📍 Merkez: {appt['center']}\n"
                                        f"📅 Tarih: {appt['date']}\n"
                                        f"📋 Kategori: {appt['category']}\n"
                                        f"🔗 Randevu Linki:\n{appt['link']}"
                                    )
                                    try:
                                        await self.app.bot.send_message(
                                            chat_id=TELEGRAM_CHAT_ID,
                                            text=message
                                        )
                                    except Exception as e:
                                        logger.error(f"Mesaj gönderme hatası: {str(e)}")
                            else:
                                logger.info(f"Uygun randevu bulunamadı: {self.country} - {self.city}")
                                
                                # Her 10 kontrolde bir durum bildirimi gönder
                                if check_count % 10 == 0:
                                    status_message = (
                                        f"ℹ️ Durum Güncellemesi\n"
                                        f"📍 Ülke: {self.country}\n"
                                        f"🏢 Şehir: {self.city}\n"
                                        f"🔄 Kontrol Sayısı: {check_count}\n"
                                        f"⏱ Kontrol Sıklığı: {self.frequency} dakika\n"
                                        f"⏰ Son Kontrol: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                                        f"✅ Durum: Aktif olarak kontrol ediliyor"
                                    )
                                    try:
                                        await self.app.bot.send_message(
                                            chat_id=TELEGRAM_CHAT_ID,
                                            text=status_message
                                        )
                                    except Exception as e:
                                        logger.error(f"Durum mesajı gönderme hatası: {str(e)}")
                    except aiohttp.ClientError as e:
                        logger.error(f"API bağlantı hatası: {str(e)}")
                        error_count += 1
                        
            except asyncio.CancelledError:
                logger.info("Randevu kontrolü iptal edildi")
                break
            except Exception as e:
                logger.error(f"Kontrol sırasında beklenmeyen hata: {str(e)}")
                error_count += 1
                
                # Sürekli hata durumunda kullanıcıya bildir
                if error_count >= 3:
                    try:
                        await self.app.bot.send_message(
                            chat_id=TELEGRAM_CHAT_ID,
                            text=f"⚠️ Randevu kontrolü sırasında hata: {str(e)}\nKontroller devam ediyor."
                        )
                    except Exception:
                        pass
                    error_count = 0

            # Bir sonraki kontrole kadar bekle
            logger.info(f"Bir sonraki kontrol için {self.frequency} dakika bekleniyor...")
            await asyncio.sleep(self.frequency * 60)

    async def run(self):
        """Bot'u başlat"""
        try:
            logger.info("Bot yapılandırılıyor...")
            self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

            # Komut açıklamalarını tanımla
            commands = [
                BotCommand("start", "Bot bilgisi ve komut listesi"),
                BotCommand("help", "Yardım menüsü"),
                BotCommand("check", "Randevu kontrolünü başlat"),
                BotCommand("stop", "Aktif kontrolü durdur"),
                BotCommand("status", "Mevcut durum bilgisi")
            ]
            
            # Komutları ekle
            logger.info("Komut işleyicileri ekleniyor...")
            self.app.add_handler(CommandHandler("start", self.start))
            self.app.add_handler(CommandHandler("help", self.help))
            self.app.add_handler(CommandHandler("check", self.check))
            self.app.add_handler(CommandHandler("stop", self.stop))
            self.app.add_handler(CommandHandler("status", self.status))
            
            # Callback işleyicisini ekle - önemli: callback_query'leri işlemek için
            logger.info("Callback işleyicisi ekleniyor...")
            self.app.add_handler(CallbackQueryHandler(self.button_callback))

            # Bot'u başlat
            logger.info("Bot başlatılıyor...")
            await self.app.initialize()
            await self.app.start()
            
            # Komut listesini Telegram'a kaydet
            logger.info("Komut listesi Telegram'a kaydediliyor...")
            await self.app.bot.set_my_commands(commands)
            
            # Polling başlat - callback_query'leri de dinle
            logger.info("Polling başlatılıyor...")
            await self.app.updater.start_polling(
                allowed_updates=["message", "callback_query"],  # callback_query'leri de dinle
                drop_pending_updates=True
            )
            
            # Başlangıç mesajı
            logger.info("Bot başarıyla başlatıldı ve çalışıyor!")
            print("✅ Schengen Vize Randevu Kontrol Botu başlatıldı!")
            print("ℹ️ Bot'u durdurmak için Ctrl+C tuşlarına basın.")

            # Polling'i sürdür
            while True:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Bot kapatma sinyali alındı...")
        except Exception as e:
            logger.error(f"Bot çalıştırma hatası: {str(e)}")
            print(f"❌ Bot başlatılırken hata oluştu: {str(e)}")
            raise
        finally:
            if self.app:
                logger.info("Bot kapatılıyor...")
                try:
                    # Aktif kontrolleri durdur
                    if self.running:
                        logger.info("Aktif kontroller durduruluyor...")
                        await self.stop_checking()
                    
                    # Bot'u kapat
                    if self.app.updater and self.app.updater.running:
                        logger.info("Updater durduruluyor...")
                        await self.app.updater.stop()
                    
                    logger.info("Bot durduruluyor...")
                    await self.app.stop()
                    await self.app.shutdown()
                    logger.info("Bot başarıyla kapatıldı.")
                    print("✅ Bot başarıyla kapatıldı.")
                except Exception as e:
                    logger.error(f"Bot kapatma hatası: {str(e)}")
                    print(f"⚠️ Bot kapatılırken hata oluştu: {str(e)}")
                    raise


async def main():
    """Ana program"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN bulunamadı! Lütfen .env dosyasını kontrol edin.")
        return

    if not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID bulunamadı! Lütfen .env dosyasını kontrol edin.")
        return

    bot = VisaBot()
    try:
        logger.info("Bot başlatılıyor...")
        await bot.run()
    except KeyboardInterrupt:
        print("\n👋 Bot kapatılıyor...")
    except Exception as e:
        print(f"\n❌ Kritik hata: {str(e)}")
    finally:
        logger.info("Bot kapatılıyor...")


if __name__ == "__main__":
    asyncio.run(main())

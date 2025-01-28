import os
import sys
import logging
import json
import asyncio
import aiohttp
from dotenv import load_dotenv
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Telegram bot setup
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    logger.error("Telegram token veya chat ID bulunamadı! Lütfen .env dosyasını kontrol edin.")
    sys.exit(1)

API_URL = "https://api.schengenvisaappointments.com/api/visa-list/?format=json"

# Conversation states
SELECTING_COUNTRY, SELECTING_CITY, SELECTING_FREQUENCY = range(3)

# Ülke isimleri sözlüğü
COUNTRIES_TR = {
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

# Ay isimleri sözlüğü
MONTHS_TR = {
    1: 'Ocak',
    2: 'Şubat',
    3: 'Mart',
    4: 'Nisan',
    5: 'Mayıs',
    6: 'Haziran',
    7: 'Temmuz',
    8: 'Ağustos',
    9: 'Eylül',
    10: 'Ekim',
    11: 'Kasım',
    12: 'Aralık'
}

def format_date(date_str):
    """Tarihi formatla: YYYY-MM-DD -> DD Month YYYY"""
    try:
        year, month, day = map(int, date_str.split('-'))
        return f"{day} {MONTHS_TR[month]} {year}"
    except:
        return date_str  # Hata durumunda orijinal tarihi döndür

class AppointmentChecker:
    def __init__(self):
        self.country = None
        self.city = None
        self.frequency = None
        self.application = None
        self.running = False
        self.task = None
        self.active_checks = {}  # chat_id: task dictionary

    def set_parameters(self, country, city, frequency):
        """Parametreleri güncelle"""
        self.country = country
        self.city = city
        self.frequency = frequency

    async def init_bot(self):
        """Initialize the bot"""
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
        await self.application.initialize()
        await self.application.start()
        return self.application

    def setup_handlers(self):
        """Set up the command handlers"""
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start_command)],
            states={
                SELECTING_COUNTRY: [CallbackQueryHandler(self.country_callback)],
                SELECTING_CITY: [CallbackQueryHandler(self.city_callback)],
                SELECTING_FREQUENCY: [CallbackQueryHandler(self.frequency_callback)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_command)],
        )

        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler('help', self.help_command))
        self.application.add_handler(CommandHandler('stop', self.stop_command))
        self.application.add_handler(CommandHandler('status', self.status_command))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        keyboard = []
        for country_code, country_name in COUNTRIES_TR.items():
            keyboard.append([InlineKeyboardButton(country_name, callback_data=f"country_{country_code}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🌍 Hoş geldiniz! Lütfen randevu kontrolü yapmak istediğiniz ülkeyi seçin:",
            reply_markup=reply_markup
        )
        return SELECTING_COUNTRY

    async def country_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Country selection callback"""
        query = update.callback_query
        await query.answer()
        
        country = query.data.split('_')[1]
        context.user_data['country'] = country

        # Şehir seçim menüsü
        cities = {
            '1': 'Ankara',
            '2': 'Istanbul',
            '3': 'Izmir',
            '4': 'Antalya',
            '5': 'Gaziantep',
            '6': 'Bursa',
            '7': 'Antalya',
            '8': 'Edirne',
        }
        
        keyboard = []
        for city_code, city_name in cities.items():
            keyboard.append([InlineKeyboardButton(city_name, callback_data=f"city_{city_name}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"🏢 {COUNTRIES_TR[country]} için şehir seçin:",
            reply_markup=reply_markup
        )
        return SELECTING_CITY

    async def city_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """City selection callback"""
        query = update.callback_query
        await query.answer()
        
        city = query.data.split('_')[1]
        context.user_data['city'] = city

        # Kontrol sıklığı seçim menüsü
        frequencies = [
            ('5 dakika', 5),
            ('15 dakika', 15),
            ('30 dakika', 30),
            ('1 saat', 60)
        ]
        
        keyboard = []
        for freq_name, freq_value in frequencies:
            keyboard.append([InlineKeyboardButton(freq_name, callback_data=f"freq_{freq_value}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⏰ Kontrol sıklığını seçin:",
            reply_markup=reply_markup
        )
        return SELECTING_FREQUENCY

    async def frequency_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Frequency selection callback"""
        query = update.callback_query
        await query.answer()
        
        frequency = int(query.data.split('_')[1])
        chat_id = str(update.effective_chat.id)
        
        # Mevcut kontrolü durdur
        if chat_id in self.active_checks:
            self.active_checks[chat_id].cancel()
        
        # Yeni kontrol başlat
        self.country = context.user_data['country']
        self.city = context.user_data['city']
        self.frequency = frequency
        
        task = asyncio.create_task(self.start_checking_for_chat(chat_id))
        self.active_checks[chat_id] = task
        
        await query.edit_message_text(
            f"✅ Randevu kontrolü başlatıldı!\n\n"
            f"🌍 Ülke: {COUNTRIES_TR[self.country]}\n"
            f"🏢 Şehir: {self.city}\n"
            f"⏰ Kontrol sıklığı: {frequency} dakika\n\n"
            "Uygun randevu bulunduğunda size bildirim göndereceğim.\n"
            "Kontrolleri durdurmak için /stop komutunu kullanabilirsiniz."
        )
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command handler"""
        help_text = (
            "🤖 Mevcut komutlar:\n\n"
            "/start - Yeni randevu kontrolü başlat\n"
            "/stop - Aktif kontrolleri durdur\n"
            "/status - Mevcut kontrol durumunu göster\n"
            "/help - Bu yardım mesajını göster\n"
            "/cancel - Mevcut işlemi iptal et"
        )
        await update.message.reply_text(help_text)

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop command handler"""
        chat_id = str(update.effective_chat.id)
        if chat_id in self.active_checks:
            self.active_checks[chat_id].cancel()
            del self.active_checks[chat_id]
            await update.message.reply_text("🛑 Randevu kontrolleri durduruldu.")
        else:
            await update.message.reply_text("❌ Aktif bir randevu kontrolü bulunamadı.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Status command handler"""
        chat_id = str(update.effective_chat.id)
        if chat_id in self.active_checks:
            status_text = (
                "📊 Mevcut Kontrol Durumu:\n\n"
                f"🌍 Ülke: {COUNTRIES_TR[self.country]}\n"
                f"🏢 Şehir: {self.city}\n"
                f"⏰ Kontrol sıklığı: {self.frequency} dakika"
            )
        else:
            status_text = "❌ Aktif bir randevu kontrolü bulunmuyor.\n\nYeni kontrol başlatmak için /start komutunu kullanın."
        
        await update.message.reply_text(status_text)

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel command handler"""
        await update.message.reply_text(
            "❌ İşlem iptal edildi.\n\nYeni bir kontrol başlatmak için /start komutunu kullanabilirsiniz."
        )
        return ConversationHandler.END

    async def start_checking_for_chat(self, chat_id):
        """Start checking appointments for a specific chat"""
        while True:
            try:
                await self.check_appointments()
                await asyncio.sleep(self.frequency * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Kontrol sırasında hata: {str(e)}")
                await asyncio.sleep(5)

    async def check_appointments(self):
        """API'den randevu kontrolü yap"""
        try:
            conn = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conn) as session:
                async with session.get(API_URL) as response:
                    if response.status != 200:
                        raise Exception(f"API yanıt vermedi: {response.status}")
                    
                    appointments = await response.json()
                    available_appointments = []
                    
                    for appointment in appointments:
                        appointment_date = appointment.get('appointment_date')
                        if not appointment_date:
                            continue
                        
                        if (appointment['source_country'] == 'Turkiye' and 
                            appointment['mission_country'].lower() == self.country.lower() and 
                            self.city.lower() in appointment['center_name'].lower()):
                            
                            available_appointments.append({
                                'country': appointment['mission_country'],
                                'city': appointment['center_name'],
                                'date': appointment_date,
                                'category': appointment['visa_category'],
                                'subcategory': appointment['visa_subcategory'],
                                'link': appointment['book_now_link']
                            })

                    if available_appointments:
                        available_appointments.sort(key=lambda x: x['date'])
                        
                        for appt in available_appointments:
                            country_tr = COUNTRIES_TR.get(appt['country'], appt['country'])
                            formatted_date = format_date(appt['date'])

                            message = f"🎉 {country_tr} için randevu bulundu!\n\n"
                            message += f"🏢 Merkez: {appt['city']}\n"
                            message += f"📅 Tarih: {formatted_date}\n"
                            message += f"📋 Kategori: {appt['category']}\n"
                            if appt['subcategory']:
                                message += f"📝 Alt Kategori: {appt['subcategory']}\n"
                            message += f"\n🔗 Randevu Linki:\n{appt['link']}"
                            
                            await self.send_notification(message)
                        
                        return True
                    
                    logger.info(f"Uygun randevu bulunamadı: {self.country} - {self.city}")
                    return False

        except Exception as e:
            error_message = f"❌ API kontrolü sırasında hata: {str(e)}"
            logger.error(error_message)
            await self.send_notification(error_message)
            return False

    async def send_notification(self, message):
        """Bildirim gönder"""
        logger.info(message)
        try:
            await self.application.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        except Exception as e:
            logger.error(f"Telegram bildirimi gönderilemedi: {str(e)}")
            print(message)

def get_user_input():
    """Kullanıcıdan giriş al"""
    print("\nSchengen Vize Randevu Kontrol Programı")
    print("=====================================")
    
    print("\nÜlke seçimi yapın (1-17):")
    countries = {
        1: 'France',
        2: 'Netherlands',
        3: 'Ireland',
        4: 'Malta',
        5: 'Sweden',
        6: 'Czechia',
        7: 'Croatia',
        8: 'Bulgaria',
        9: 'Finland',
        10: 'Slovenia',
        11: 'Denmark',
        12: 'Norway',
        13: 'Estonia',
        14: 'Lithuania',
        15: 'Luxembourg',
        16: 'Ukraine',
        17: 'Latvia'
    }
    
    for num, country in countries.items():
        print(f"{num}. {COUNTRIES_TR[country]}")
    
    while True:
        try:
            country_choice = int(input("\nSeçiminiz (1-17): "))
            if 1 <= country_choice <= 17:
                selected_country = countries[country_choice]
                break
            print("Lütfen 1-17 arasında bir sayı girin!")
        except ValueError:
            print("Lütfen geçerli bir sayı girin!")
    
    # Şehir seçimi
    cities = {
        '1': 'Ankara',
        '2': 'Istanbul',
        '3': 'Izmir',
        '4': 'Antalya',
        '5': 'Gaziantep',
		'6': 'Bursa',
		'7': 'Antalya',
		'8': 'Edirne',
    }
    
    print("\nŞehir seçimi yapınız:")
    for key, value in cities.items():
        print(f"{key}. {value}")
    
    city_choice = input("\nSeçiminiz (1-5): ")
    selected_city = cities.get(city_choice)
    
    if not selected_city:
        raise ValueError("Geçersiz şehir seçimi!")
    
    # Kontrol sıklığı
    print("\nKontrol sıklığı (dakika):")
    frequency = int(input("Kaç dakikada bir kontrol edilsin? (1-60): "))
    if frequency < 1 or frequency > 60:
        raise ValueError("Geçersiz kontrol sıklığı! 1-60 dakika arası bir değer girin.")
    
    return selected_country, selected_city, frequency

async def main():
    """Ana program"""
    checker = AppointmentChecker()
    
    # Terminal arayüzü için
    if len(sys.argv) > 1 and sys.argv[1] == '--terminal':
        await checker.init_bot()
        
        while True:
            try:
                country, city, frequency = get_user_input()
                checker.set_parameters(country, city, frequency)
                print(f"\n{country} için {city} şehrinde randevu kontrolü başlatılıyor...")
                print(f"Kontrol sıklığı: {frequency} dakika")
                print("\nProgram çalışıyor... Durdurmak için Ctrl+C'ye basın.\n")
                
                checker.task = asyncio.create_task(checker.start_checking_for_chat(TELEGRAM_CHAT_ID))
                await checker.task
                
            except KeyboardInterrupt:
                print("\nProgram durduruluyor...")
                if checker.task:
                    checker.task.cancel()
                await checker.application.stop()
                break
            except Exception as e:
                print(f"\nBeklenmeyen hata: {str(e)}")
                continue
    else:
        # Telegram bot arayüzü için
        await checker.init_bot()
        await checker.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram sonlandırıldı.")
    except Exception as e:
        print(f"\nKritik hata: {str(e)}") 
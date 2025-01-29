import os
import sys
import logging
import json
import asyncio
import requests
import telebot
from telebot import types
from dotenv import load_dotenv
import time
import urllib3

# SSL uyarılarını devre dışı bırak
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        self.bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
        self.country = None
        self.city = None
        self.frequency = None
        self.running = False
        self.task = None
        self.active_checks = {}  # chat_id: task dictionary
        self.setup_handlers()
        self.loop = None

    def setup_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            markup = types.InlineKeyboardMarkup()
            for country_code, country_name in COUNTRIES_TR.items():
                markup.add(types.InlineKeyboardButton(country_name, callback_data=f"country_{country_code}"))
            self.bot.send_message(message.chat.id, "🌍 Hoş geldiniz! Lütfen randevu kontrolü yapmak istediğiniz ülkeyi seçin:", reply_markup=markup)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('country_'))
        def country_callback(call):
            country = call.data.split('_')[1]
            self.country = country
            
            markup = types.InlineKeyboardMarkup()
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
            for city_code, city_name in cities.items():
                markup.add(types.InlineKeyboardButton(city_name, callback_data=f"city_{city_name}"))
            
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🏢 {COUNTRIES_TR[country]} için şehir seçin:",
                reply_markup=markup
            )

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('city_'))
        def city_callback(call):
            city = call.data.split('_')[1]
            self.city = city
            
            markup = types.InlineKeyboardMarkup()
            frequencies = [
                ('1 dakika', 1),
                ('5+1 dakika', 5),
                ('15+1 dakika', 15),
                ('30+1 dakika', 30),
                ('1 saat +1 dakika', 60)
            ]
            for freq_name, freq_value in frequencies:
                markup.add(types.InlineKeyboardButton(freq_name, callback_data=f"freq_{freq_value}"))
            
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="⏰ Kontrol sıklığını seçin:\n(Not: 1 dakika hariç diğer seçeneklere +1 dakika eklenir)",
                reply_markup=markup
            )

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('freq_'))
        def frequency_callback(call):
            frequency = int(call.data.split('_')[1])
            # 1 dakika seçildiyse ekstra ekleme yapma
            self.frequency = frequency if frequency == 1 else frequency + 1
            chat_id = str(call.message.chat.id)
            
            if chat_id in self.active_checks:
                self.stop_checking(chat_id)
            
            self.start_checking(chat_id)
            
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ Randevu kontrolü başlatıldı!\n\n"
                     f"🌍 Ülke: {COUNTRIES_TR[self.country]}\n"
                     f"🏢 Şehir: {self.city}\n"
                     f"⏰ Kontrol sıklığı: {self.frequency} dakika\n\n"
                     "Uygun randevu bulunduğunda size bildirim göndereceğim.\n"
                     "Kontrolleri durdurmak için /stop komutunu kullanabilirsiniz."
            )

        @self.bot.message_handler(commands=['stop'])
        def stop_command(message):
            chat_id = str(message.chat.id)
            if chat_id in self.active_checks:
                self.stop_checking(chat_id)
                self.bot.reply_to(message, "🛑 Randevu kontrolleri durduruldu.")
            else:
                self.bot.reply_to(message, "❌ Aktif bir randevu kontrolü bulunamadı.")

        @self.bot.message_handler(commands=['status'])
        def status_command(message):
            chat_id = str(message.chat.id)
            if chat_id in self.active_checks:
                status_text = (
                    "📊 Mevcut Kontrol Durumu:\n\n"
                    f"🌍 Ülke: {COUNTRIES_TR[self.country]}\n"
                    f"🏢 Şehir: {self.city}\n"
                    f"⏰ Kontrol sıklığı: {self.frequency} dakika"
                )
            else:
                status_text = "❌ Aktif bir randevu kontrolü bulunmuyor.\n\nYeni kontrol başlatmak için /start komutunu kullanın."
            
            self.bot.reply_to(message, status_text)

        @self.bot.message_handler(commands=['help'])
        def help_command(message):
            help_text = (
                "🤖 Mevcut komutlar:\n\n"
                "/start - Yeni randevu kontrolü başlat\n"
                "/stop - Aktif kontrolleri durdur\n"
                "/status - Mevcut kontrol durumunu göster\n"
                "/help - Bu yardım mesajını göster"
            )
            self.bot.reply_to(message, help_text)

    def start_checking(self, chat_id):
        """Kontrol işlemini başlat"""
        def check_loop():
            while True:
                try:
                    self.check_appointments_sync()
                except Exception as e:
                    logger.error(f"Kontrol sırasında hata: {str(e)}")
                finally:
                    time.sleep(self.frequency * 60)

        import threading
        thread = threading.Thread(target=check_loop)
        thread.daemon = True
        thread.start()
        self.active_checks[chat_id] = thread

    def stop_checking(self, chat_id):
        """Kontrol işlemini durdur"""
        if chat_id in self.active_checks:
            del self.active_checks[chat_id]

    def check_appointments_sync(self):
        """Senkron randevu kontrolü"""
        try:
            response = requests.get(API_URL, verify=False)
            if response.status_code != 200:
                raise Exception(f"API yanıt vermedi: {response.status_code}")
            
            appointments = response.json()
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
                    
                    self.send_notification(message)
                
                return True
            
            logger.info(f"Uygun randevu bulunamadı: {self.country} - {self.city}")
            return False

        except Exception as e:
            error_message = f"❌ API kontrolü sırasında hata: {str(e)}"
            logger.error(error_message)
            self.send_notification(error_message)
            return False

    def send_notification(self, message):
        """Bildirim gönder"""
        logger.info(message)
        try:
            self.bot.send_message(TELEGRAM_CHAT_ID, message)
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
    print("Not: 1 dakika seçerseniz her dakika kontrol edilir.")
    print("Not: Diğer sürelere otomatik olarak 1 dakika eklenecektir.")
    frequency = int(input("Kaç dakikada bir kontrol edilsin? (1-60): "))
    if frequency < 1 or frequency > 60:
        raise ValueError("Geçersiz kontrol sıklığı! 1-60 dakika arası bir değer girin.")
    
    return selected_country, selected_city, frequency

def main():
    """Ana program - Terminal modu"""
    checker = AppointmentChecker()
    
    while True:
        try:
            country, city, frequency = get_user_input()
            checker.country = country
            checker.city = city
            # 1 dakika seçildiyse ekstra ekleme yapma
            checker.frequency = frequency if frequency == 1 else frequency + 1
            print(f"\n{country} için {city} şehrinde randevu kontrolü başlatılıyor...")
            print(f"Kontrol sıklığı: {checker.frequency} dakika")
            print("\nProgram çalışıyor... Durdurmak için Ctrl+C'ye basın.\n")
            
            checker.start_checking(TELEGRAM_CHAT_ID)
            
            # Ana thread'i canlı tut
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                checker.stop_checking(TELEGRAM_CHAT_ID)
                break
            
        except KeyboardInterrupt:
            print("\nProgram durduruluyor...")
            checker.stop_checking(TELEGRAM_CHAT_ID)
            break
        except Exception as e:
            print(f"\nBeklenmeyen hata: {str(e)}")
            continue

def run_bot():
    """Normal bot modu için başlatıcı"""
    checker = AppointmentChecker()
    print("Bot başlatılıyor...")
    checker.bot.infinity_polling()

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--terminal':
            main()
        else:
            run_bot()
    except KeyboardInterrupt:
        print("\nProgram sonlandırıldı.")
    except Exception as e:
        print(f"\nKritik hata: {str(e)}") 
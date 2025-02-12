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
        self.active_checks = {}
        self.setup_handlers()
        self.loop = None
        
        # API URL'leri
        self.apis = {
            'schengen': "https://api.schengenvisaappointments.com/api/visa-list/?format=json",
            'vfs': "https://visa.vfsglobal.com/tur/tr/api/appointments",
            'italy': "https://prenotami.esteri.it/api/schedule",
            'germany': "https://service2.diplo.de/rktermin/extern/appointment_showMonth.do"
        }
        
        # Ülke grupları
        self.country_groups = {
            'schengen': COUNTRIES_TR,
            'vfs': {
                'UK': 'İngiltere',
                'CAN': 'Kanada',
                'AUS': 'Avustralya',
                'NZL': 'Yeni Zelanda',
                'ZAF': 'Güney Afrika'
            },
            'italy': {'ITA': 'İtalya'},
            'germany': {'DEU': 'Almanya'}
        }

    def setup_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            markup = types.InlineKeyboardMarkup()
            
            # Kategori butonları
            markup.add(types.InlineKeyboardButton("🇪🇺 Schengen Ülkeleri", callback_data="category_schengen"))
            markup.add(types.InlineKeyboardButton("🌏 VFS Global Ülkeleri", callback_data="category_vfs"))
            markup.add(types.InlineKeyboardButton("🌍 Diğer Ülkeler", callback_data="category_other"))
            
            self.bot.send_message(
                message.chat.id, 
                "🌍 Hoş geldiniz!\nLütfen randevu kontrolü yapmak istediğiniz ülke kategorisini seçin:",
                reply_markup=markup
            )

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('category_'))
        def category_callback(call):
            category = call.data.split('_')[1]
            markup = types.InlineKeyboardMarkup()
            
            if category == 'schengen':
                # Schengen ülkeleri
                for country_code, country_name in COUNTRIES_TR.items():
                    markup.add(types.InlineKeyboardButton(country_name, callback_data=f"country_{country_code}"))
                text = "🇪🇺 Lütfen Schengen ülkesini seçin:"
            
            elif category == 'vfs':
                # VFS Global ülkeleri
                for country_code, country_name in self.country_groups['vfs'].items():
                    markup.add(types.InlineKeyboardButton(country_name, callback_data=f"country_{country_code}"))
                text = "🌏 Lütfen VFS Global ülkesini seçin:"
            
            elif category == 'other':
                # Diğer ülkeler (İtalya ve Almanya)
                other_countries = {**self.country_groups['italy'], **self.country_groups['germany']}
                for country_code, country_name in other_countries.items():
                    markup.add(types.InlineKeyboardButton(country_name, callback_data=f"country_{country_code}"))
                text = "🌍 Lütfen ülke seçin:"
            
            # Geri dönüş butonu
            markup.add(types.InlineKeyboardButton("⬅️ Geri", callback_data="back_to_categories"))
            
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup
            )

        @self.bot.callback_query_handler(func=lambda call: call.data == 'back_to_categories')
        def back_to_categories(call):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🇪🇺 Schengen Ülkeleri", callback_data="category_schengen"))
            markup.add(types.InlineKeyboardButton("🌏 VFS Global Ülkeleri", callback_data="category_vfs"))
            markup.add(types.InlineKeyboardButton("🌍 Diğer Ülkeler", callback_data="category_other"))
            
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="🌍 Lütfen randevu kontrolü yapmak istediğiniz ülke kategorisini seçin:",
                reply_markup=markup
            )

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
            
            # Geri dönüş butonu
            markup.add(types.InlineKeyboardButton("⬅️ Geri", callback_data="back_to_categories"))
            
            country_name = self.get_country_name(country)
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🏢 {country_name} için şehir seçin:",
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
            
            # Ülke ismini doğru sözlükten al
            country_name = self.get_country_name(self.country)
            
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ Randevu kontrolü başlatıldı!\n\n"
                     f"🌍 Ülke: {country_name}\n"
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
                # Ülke ismini doğru sözlükten al
                country_name = self.get_country_name(self.country)
                status_text = (
                    "📊 Mevcut Kontrol Durumu:\n\n"
                    f"🌍 Ülke: {country_name}\n"
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
            # Ülke grubunu belirle
            api_group = self.determine_api_group()
            logger.info(f"API Grubu: {api_group}, Ülke: {self.country}, Şehir: {self.city}")
            
            if api_group == 'schengen':
                return self.check_schengen_appointments()
            elif api_group == 'vfs':
                return self.check_vfs_appointments()
            elif api_group == 'italy':
                return self.check_italy_appointments()
            elif api_group == 'germany':
                return self.check_germany_appointments()
            else:
                logger.error(f"Desteklenmeyen API grubu: {api_group}")
                return False
            
        except Exception as e:
            error_message = f"❌ API kontrolü sırasında hata: {str(e)}"
            logger.error(error_message)
            self.send_notification(error_message)
            return False

    def determine_api_group(self):
        """Ülkenin hangi API grubuna ait olduğunu belirle"""
        for group, countries in self.country_groups.items():
            if self.country in countries:
                return group
        return 'schengen'  # varsayılan olarak schengen

    def check_schengen_appointments(self):
        """Schengen randevularını kontrol et"""
        response = requests.get(self.apis['schengen'], verify=False)
        if response.status_code != 200:
            raise Exception(f"Schengen API yanıt vermedi: {response.status_code}")
        
        appointments = response.json()
        return self.process_schengen_appointments(appointments)

    def check_vfs_appointments(self):
        """VFS Global randevularını kontrol et"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Origin': 'https://visa.vfsglobal.com',
            'Referer': 'https://visa.vfsglobal.com/tur/tr/appointment',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        try:
            response = requests.get(
                f"{self.apis['vfs']}/{self.country.lower()}/tr/appointment",
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 403:
                logger.warning("VFS API erişim engeli. Farklı bir User-Agent ile tekrar deneniyor...")
                # Alternatif User-Agent ile tekrar dene
                headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
                response = requests.get(
                    f"{self.apis['vfs']}/{self.country.lower()}/tr/appointment",
                    headers=headers,
                    verify=False,
                    timeout=30
                )
            
            if response.status_code != 200:
                raise Exception(f"VFS API yanıt vermedi: {response.status_code}")
            
            appointments = response.json()
            return self.process_vfs_appointments(appointments)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"VFS API bağlantı hatası: {str(e)}")
            raise Exception(f"VFS API bağlantı hatası: {str(e)}")

    def check_italy_appointments(self):
        """İtalya randevularını kontrol et"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Origin': 'https://prenotami.esteri.it',
            'Referer': 'https://prenotami.esteri.it/Services',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        try:
            # Önce oturum açma sayfasına istek at
            session = requests.Session()
            session.headers.update(headers)
            
            # Ana sayfaya git ve CSRF token al
            response = session.get('https://prenotami.esteri.it/', verify=False, timeout=30)
            if response.status_code != 200:
                raise Exception(f"İtalya ana sayfasına erişilemedi: {response.status_code}")
            
            # Randevu API'sine istek at
            api_url = f"{self.apis['italy']}?office={self.city}&service=2"  # service=2 genellikle vize servisi
            response = session.get(api_url, verify=False, timeout=30)
            
            if response.status_code == 500:
                logger.warning("İtalya API'si şu anda hizmet veremiyor. Daha sonra tekrar denenecek.")
                return False
            elif response.status_code != 200:
                raise Exception(f"İtalya API yanıt vermedi: {response.status_code}")
            
            try:
                appointments = response.json()
                return self.process_italy_appointments(appointments)
            except json.JSONDecodeError:
                logger.error("İtalya API'si geçersiz JSON yanıtı döndürdü")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"İtalya API bağlantı hatası: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"İtalya randevu kontrolü sırasında hata: {str(e)}")
            return False

    def check_germany_appointments(self):
        """Almanya randevularını kontrol et"""
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html'
        }
        response = requests.get(self.apis['germany'], headers=headers, verify=False)
        if response.status_code != 200:
            raise Exception(f"Almanya API yanıt vermedi: {response.status_code}")
        
        # HTML parse etme işlemi gerekebilir
        return self.process_germany_appointments(response.text)

    def process_schengen_appointments(self, appointments):
        """Schengen randevularını işle"""
        try:
            available_appointments = []
            if not appointments:
                logger.warning("Schengen API boş yanıt döndürdü")
                return False

            for appointment in appointments:
                try:
                    if not all(key in appointment for key in ['source_country', 'mission_country', 'center_name']):
                        continue

                    if (appointment['source_country'] == 'Turkiye' and 
                        appointment['mission_country'].lower() == self.country.lower() and 
                        self.city.lower() in appointment['center_name'].lower()):
                        
                        appt_data = {
                            'country': appointment['mission_country'],
                            'city': appointment['center_name'],
                            'date': appointment.get('appointment_date', 'Tarih belirtilmemiş'),
                            'category': appointment.get('visa_category', 'Kategori belirtilmemiş'),
                            'subcategory': appointment.get('visa_subcategory', ''),
                            'link': appointment.get('book_now_link', self.apis['schengen'])
                        }
                        available_appointments.append(appt_data)
                except Exception as e:
                    logger.error(f"Randevu işlenirken hata: {str(e)}")
                    continue
            
            return self.send_appointment_notifications(available_appointments)
        except Exception as e:
            logger.error(f"Schengen randevuları işlenirken hata: {str(e)}")
            return False

    def process_vfs_appointments(self, appointments):
        """VFS randevularını işle"""
        try:
            available_appointments = []
            if not appointments or 'data' not in appointments:
                logger.warning("VFS API boş yanıt döndürdü veya data alanı eksik")
                return False

            for appointment in appointments.get('data', []):
                try:
                    if appointment.get('available'):
                        appt_data = {
                            'country': self.country,
                            'city': appointment.get('location', self.city),
                            'date': appointment.get('date', 'Tarih belirtilmemiş'),
                            'category': 'Vize Başvurusu',
                            'subcategory': appointment.get('type', ''),
                            'link': appointment.get('booking_link', self.apis['vfs'])
                        }
                        available_appointments.append(appt_data)
                except Exception as e:
                    logger.error(f"VFS randevusu işlenirken hata: {str(e)}")
                    continue
            
            return self.send_appointment_notifications(available_appointments)
        except Exception as e:
            logger.error(f"VFS randevuları işlenirken hata: {str(e)}")
            return False

    def process_italy_appointments(self, appointments):
        """İtalya randevularını işle"""
        try:
            available_appointments = []
            if not appointments:
                logger.warning("İtalya API boş yanıt döndürdü")
                return False

            # İtalya API'sinin yanıt formatına göre işle
            for date, slots in appointments.items():
                if slots and isinstance(slots, list):
                    for slot in slots:
                        try:
                            if slot.get('available', False):
                                appt_data = {
                                    'country': self.country,
                                    'city': self.city,
                                    'date': date,
                                    'category': 'Vize Başvurusu',
                                    'subcategory': slot.get('service_type', ''),
                                    'link': 'https://prenotami.esteri.it/Services/Booking'
                                }
                                available_appointments.append(appt_data)
                        except Exception as e:
                            logger.error(f"İtalya randevusu işlenirken hata: {str(e)}")
                            continue

            return self.send_appointment_notifications(available_appointments)
        except Exception as e:
            logger.error(f"İtalya randevuları işlenirken hata: {str(e)}")
            return False

    def send_appointment_notifications(self, appointments):
        """Randevu bildirimlerini gönder"""
        try:
            if not appointments:
                logger.info(f"Uygun randevu bulunamadı: {self.country} - {self.city}")
                return False

            # Tarihe göre sırala (None değerleri en sona at)
            appointments.sort(key=lambda x: x.get('date', '') or '')
            
            for appt in appointments:
                try:
                    country_name = self.get_country_name(appt.get('country', self.country))
                    formatted_date = format_date(appt.get('date', 'Tarih belirtilmemiş'))

                    message = f"🎉 {country_name} için randevu bulundu!\n\n"
                    message += f"🏢 Merkez: {appt.get('city', self.city)}\n"
                    message += f"📅 Tarih: {formatted_date}\n"
                    message += f"📋 Kategori: {appt.get('category', 'Belirtilmemiş')}\n"
                    if appt.get('subcategory'):
                        message += f"📝 Alt Kategori: {appt['subcategory']}\n"
                    message += f"\n🔗 Randevu Linki:\n{appt.get('link', 'Link mevcut değil')}"
                    
                    self.send_notification(message)
                except Exception as e:
                    logger.error(f"Bildirim oluşturulurken hata: {str(e)}")
                    continue
            
            return True
        except Exception as e:
            logger.error(f"Bildirimler gönderilirken hata: {str(e)}")
            return False

    def get_country_name(self, country_code):
        """Ülke koduna göre Türkçe ismi getir"""
        for group in self.country_groups.values():
            if country_code in group:
                return group[country_code]
        return country_code

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
    print("\nVize Randevu Kontrol Programı")
    print("=====================================")
    
    print("\nÜlke seçimi yapın:")
    countries = {
        # Schengen Ülkeleri
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
        17: 'Latvia',
        # VFS Global Ülkeleri
        18: 'UK',
        19: 'CAN',
        20: 'AUS',
        21: 'NZL',
        22: 'ZAF',
        # Diğer Ülkeler
        23: 'ITA',
        24: 'DEU'
    }
    
    # Ülke isimlerini Türkçe olarak göster
    country_names = {
        'UK': 'İngiltere',
        'CAN': 'Kanada',
        'AUS': 'Avustralya',
        'NZL': 'Yeni Zelanda',
        'ZAF': 'Güney Afrika',
        'ITA': 'İtalya',
        'DEU': 'Almanya'
    }
    
    print("\nSchengen Ülkeleri:")
    for num in range(1, 18):
        country = countries[num]
        print(f"{num}. {COUNTRIES_TR[country]}")
    
    print("\nVFS Global Ülkeleri:")
    for num in range(18, 23):
        country = countries[num]
        print(f"{num}. {country_names[country]}")
    
    print("\nDiğer Ülkeler:")
    for num in range(23, 25):
        country = countries[num]
        print(f"{num}. {country_names[country]}")
    
    while True:
        try:
            country_choice = int(input("\nSeçiminiz (1-24): "))
            if 1 <= country_choice <= 24:
                selected_country = countries[country_choice]
                break
            print("Lütfen 1-24 arasında bir sayı girin!")
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
# Schengen Vize Randevu Kontrol Botu 🌍

Schengen vizesi için randevu kontrolü yapmanızı sağlayan bir Telegram botudur. Bot, belirtilen ülke ve şehir için düzenli olarak randevu kontrolü yapar ve uygun randevu bulunduğunda Telegram üzerinden bildirim gönderir.

## Özellikler ✨

- 17 farklı Schengen ülkesi için randevu kontrolü
- 7 farklı Türkiye şehrinde randevu takibi
- Telegram üzerinden kolay kullanım
- Butonlu arayüz ile ülke ve şehir seçimi
- Özelleştirilebilir kontrol sıklığı (1-5 dakika)
- Detaylı randevu bilgileri (tarih, merkez, kategori)
- Otomatik bildirim sistemi
- Randevu bulunduğunda doğrudan rezervasyon bağlantısı

## Kurulum 🚀

### Gereksinimler

- Python 3.8 veya üzeri (Python 3.11 önerilir)
- pip (Python paket yöneticisi)

### Adımlar

1. Repoyu klonlayın:
```bash
git clone https://github.com/ibidi/schengen-visa-bot.git
cd schengen-visa-bot
```

2. (Opsiyonel) Sanal ortam oluşturun ve aktifleştirin:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# veya
.venv\Scripts\activate  # Windows
```

3. Gerekli Python paketlerini yükleyin:
```bash
pip install -r requirements.txt
```

4. `.env` dosyasını oluşturun ve Telegram bot bilgilerinizi ekleyin:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Gerekli Kütüphaneler

- python-telegram-bot (v20.6)
- python-dotenv (v1.0.0)
- aiohttp (v3.8.6)
- asyncio (v3.4.3)
- pytz (v2023.3)

## Kullanım 📱

Botu başlatmak için:
```bash
python3 schengen_bot.py
```

### Telegram Komutları

- `/start` - Bot bilgisi ve komut listesi
- `/help` - Yardım menüsü
- `/check` - Butonlu arayüz ile randevu kontrolünü başlat
- `/stop` - Aktif kontrolü durdur
- `/status` - Mevcut durum bilgisi

### Butonlu Arayüz Kullanımı

1. `/check` komutunu gönderin
2. Açılan menüden ülke seçin
3. Şehir seçin
4. Kontrol sıklığını (1-5 dakika) seçin

### Eski Komut Kullanımı (Opsiyonel)

```
/check Fransa Istanbul
```

## Desteklenen Ülkeler 🌐

- 🇫🇷 Fransa
- 🇳🇱 Hollanda
- 🇮🇪 İrlanda
- 🇲🇹 Malta
- 🇸🇪 İsveç
- 🇨🇿 Çekya
- 🇭🇷 Hırvatistan
- 🇧🇬 Bulgaristan
- 🇫🇮 Finlandiya
- 🇸🇮 Slovenya
- 🇩🇰 Danimarka
- 🇳🇴 Norveç
- 🇪🇪 Estonya
- 🇱🇹 Litvanya
- 🇱🇺 Lüksemburg
- 🇺🇦 Ukrayna
- 🇱🇻 Letonya

## Desteklenen Şehirler 🏢

- 🇹🇷 Ankara
- 🇹🇷 Istanbul
- 🇹🇷 Izmir
- 🇹🇷 Antalya
- 🇹🇷 Gaziantep
- 🇹🇷 Bursa
- 🇹🇷 Edirne

## Geliştirme 🛠

Bu bot Python 3 ile geliştirilmiştir ve aşağıdaki ana kütüphaneleri kullanmaktadır:

- python-telegram-bot
- aiohttp
- python-dotenv

## Lisans 📄

Bu proje MIT lisansı altında lisanslanmıştır. Daha fazla bilgi için `LICENSE` dosyasına bakın.

## Katkıda Bulunma 🤝

Her türlü katkıya açığız! Lütfen bir pull request göndermeden önce değişikliklerinizi tartışmak için bir issue açın.

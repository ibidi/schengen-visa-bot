# 🌍 Schengen Vize Randevu Kontrol Botu

Bu bot, Schengen vizesi için randevu kontrolü yapmanızı sağlayan bir Python uygulamasıdır. Bot, belirtilen ülke ve şehir için düzenli aralıklarla randevu kontrolü yapar ve uygun randevu bulunduğunda Telegram üzerinden bildirim gönderir.

## 🚀 Özellikler

- 17 farklı Schengen ülkesi için randevu kontrolü
- 8 farklı Türkiye şehrinden randevu arama
- Telegram üzerinden anlık bildirimler
- Özelleştirilebilir kontrol sıklığı
- Kullanıcı dostu menü arayüzü
- Terminal veya Telegram bot modu seçeneği

## 📋 Gereksinimler

- Python 3.8 - 3.11 arası bir sürüm (3.13 desteklenmemektedir)
- Telegram Bot Token
- Telegram Chat ID

## 🛠️ Kurulum

1. Python'un desteklenen bir sürümünü yükleyin (3.8 - 3.11 arası):
   - Windows: [Python İndirme Sayfası](https://www.python.org/downloads/)
   - macOS: `brew install python@3.11`
   - Linux: `sudo apt-get install python3.11`

2. Repoyu klonlayın:
```bash
git clone https://github.com/ibidi/schengen-visa-bot.git
cd schengen-visa-bot
```

3. Sanal ortam oluşturun ve aktifleştirin:
```bash
# Windows için:
python -m venv venv
venv\Scripts\activate

# macOS/Linux için:
python3 -m venv venv
source venv/bin/activate
```

4. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

5. `.env` dosyasını düzenleyin:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## 🎮 Kullanım

Bot iki farklı modda çalıştırılabilir:

### 1. Telegram Bot Modu
Bu mod, Telegram üzerinden komutlarla kontrol edilebilen bir bot başlatır.
```bash
python bot.py
```

### 2. Terminal Modu
Bu mod, terminal üzerinden kontrol edilebilen bir arayüz sunar.
```bash
python bot.py --terminal
```

### Kontrol Sıklığı
Bot, seçtiğiniz kontrol sıklığına otomatik olarak 1 dakika ekler. Örneğin:
- 5 dakika seçerseniz, kontrol 6 dakikada bir yapılacak
- 15 dakika seçerseniz, kontrol 16 dakikada bir yapılacak

## 🤖 Telegram Bot Komutları

- `/start` - Yeni randevu kontrolü başlat
- `/stop` - Aktif kontrolleri durdur
- `/status` - Mevcut kontrol durumunu göster
- `/help` - Komut listesini göster

## 📱 Telegram Bot Kurulumu

1. Telegram'da [@BotFather](https://t.me/botfather) ile yeni bir bot oluşturun
2. Bot token'ını alın ve `.env` dosyasına kaydedin
3. [@userinfobot](https://t.me/userinfobot)'u kullanarak Chat ID'nizi alın
4. Chat ID'yi `.env` dosyasına kaydedin

## ⚠️ Notlar

- Bot, randevu bulduğunda size Telegram üzerinden bildirim gönderecektir
- Kontrol sıklığını çok düşük tutmamaya özen gösterin
- Program çalışırken Ctrl+C ile durdurabilirsiniz
- SSL sertifika uyarıları otomatik olarak gizlenmektedir

## 🔍 Desteklenen Ülkeler

- Fransa
- Hollanda
- İrlanda
- Malta
- İsveç
- Çekya
- Hırvatistan
- Bulgaristan
- Finlandiya
- Slovenya
- Danimarka
- Norveç
- Estonya
- Litvanya
- Lüksemburg
- Ukrayna
- Letonya

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. 
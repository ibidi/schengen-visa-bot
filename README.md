# 🌍 Schengen Vize Randevu Kontrol Botu

Bu bot, Schengen vizesi için randevu kontrolü yapmanızı sağlayan bir Python uygulamasıdır. Bot, belirtilen ülke ve şehir için düzenli aralıklarla randevu kontrolü yapar ve uygun randevu bulunduğunda Telegram ve web arayüzü üzerinden bildirim gönderir.

## 🚀 Özellikler

- 17 farklı Schengen ülkesi için randevu kontrolü
- 8 farklı Türkiye şehrinden randevu arama
- Çoklu bildirim sistemi:
  - 🔔 Web arayüzünde anlık bildirimler
  - 🎵 Sesli bildirimler
  - 🖥️ Masaüstü bildirimleri
  - 📱 Telegram bildirimleri
- Bildirim geçmişi ve yönetimi
- Özelleştirilebilir bildirim ayarları
- Gerçek zamanlı durum güncellemeleri
- Kullanıcı dostu web arayüzü
- Terminal veya Telegram bot modu seçeneği
- WebSocket ile anlık iletişim
- Otomatik log kaydı ve takibi

## 📋 Gereksinimler

- Python 3.8 - 3.11 arası bir sürüm (3.13 desteklenmemektedir)
- Telegram Bot Token
- Telegram Chat ID
- Modern bir web tarayıcısı (Chrome, Firefox, Safari, Edge)

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
FLASK_SECRET_KEY=your_secret_key_here
```

## 🎮 Kullanım

Bot iki farklı modda çalıştırılabilir:

### 1. Web Arayüzü Modu
Bu mod, web tarayıcısı üzerinden kontrol edilebilen bir arayüz sunar.
```bash
python web_app.py
```
Tarayıcınızda `http://localhost:5000` adresine gidin.

### 2. Telegram Bot Modu
Bu mod, Telegram üzerinden komutlarla kontrol edilebilen bir bot başlatır.
```bash
python bot.py
```

### 3. Terminal Modu
Bu mod, terminal üzerinden kontrol edilebilen bir arayüz sunar.
```bash
python bot.py --terminal
```

## 🔔 Bildirim Sistemi

Bot şu bildirim kanallarını destekler:

1. **Web Bildirimleri**: Web arayüzünde anlık pop-up bildirimler
2. **Sesli Bildirimler**: Randevu bulunduğunda sesli uyarı
3. **Masaüstü Bildirimleri**: Tarayıcı üzerinden masaüstü bildirimleri
4. **Telegram Bildirimleri**: Telegram üzerinden mesaj bildirimleri

Bildirim ayarlarını `/notification_settings` sayfasından özelleştirebilirsiniz.

## 📱 Telegram Bot Komutları

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

- Bot, randevu bulduğunda size tüm bildirim kanalları üzerinden haber verecektir
- Masaüstü bildirimleri için tarayıcı izinlerini vermeniz gerekir
- Kontrol sıklığını çok düşük tutmamaya özen gösterin
- Program çalışırken Ctrl+C ile durdurabilirsiniz
- SSL sertifika uyarıları otomatik olarak gizlenmektedir

## 🔍 Desteklenen Ülkeler

### 🇪🇺 Schengen Ülkeleri
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

### 🌏 VFS Global Ülkeleri
- İngiltere
- Kanada
- Avustralya
- Yeni Zelanda
- Güney Afrika

### 🌍 Diğer Ülkeler
- İtalya
- Almanya

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. 
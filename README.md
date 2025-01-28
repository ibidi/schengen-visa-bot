# 🌍 Schengen Vize Randevu Kontrol Botu

Bu bot, Schengen vizesi için randevu kontrolü yapmanızı sağlayan bir Python uygulamasıdır. Bot, belirtilen ülke ve şehir için düzenli aralıklarla randevu kontrolü yapar ve uygun randevu bulunduğunda Telegram üzerinden bildirim gönderir.

## 🚀 Özellikler

- 17 farklı Schengen ülkesi için randevu kontrolü
- 8 farklı Türkiye şehrinden randevu arama
- Telegram üzerinden anlık bildirimler
- Özelleştirilebilir kontrol sıklığı
- Kullanıcı dostu menü arayüzü

## 📋 Gereksinimler

- Python 3.7+
- Telegram Bot Token
- Telegram Chat ID

## 🛠️ Kurulum

1. Repoyu klonlayın:
```bash
git clone https://github.com/yourusername/schengen-visa-bot.git
cd schengen-visa-bot
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. `.env` dosyasını düzenleyin:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## 🎮 Kullanım

1. Programı başlatın:
```bash
python bot.py
```

2. Menüden istediğiniz ülkeyi ve şehri seçin
3. Kontrol sıklığını belirleyin (1-60 dakika arası)
4. Program çalışmaya başlayacak ve uygun randevu bulunduğunda Telegram üzerinden bildirim alacaksınız

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

## 📱 Telegram Bot Kurulumu

1. Telegram'da [@BotFather](https://t.me/botfather) ile yeni bir bot oluşturun
2. Bot token'ını alın ve `.env` dosyasına kaydedin
3. [@userinfobot](https://t.me/userinfobot)'u kullanarak Chat ID'nizi alın
4. Chat ID'yi `.env` dosyasına kaydedin

## ⚠️ Notlar

- Bot, randevu bulduğunda size Telegram üzerinden bildirim gönderecektir
- Kontrol sıklığını çok düşük tutmamaya özen gösterin
- Program çalışırken Ctrl+C ile menüye dönebilirsiniz

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. 
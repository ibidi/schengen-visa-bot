# Schengen Visa Bot

## Proje Açıklaması

Bu proje, Schengen vizesi için randevu alım sürecini otomatikleştiren bir Telegram botudur. Kullanıcıların vize randevusu almak için gerekli adımları kolaylaştırmak amacıyla geliştirilmiştir. Bot, kullanıcıların belirli bir tarih ve saat için randevu alabilmelerini sağlar ve uygun randevuları kontrol eder.

## Özellikler
- **Telegram Bot Entegrasyonu:** Kullanıcılar, bot ile etkileşimde bulunarak randevu alabilirler.
- **Otomatik Randevu Kontrolü:** Bot, belirli aralıklarla randevu alım sayfasını kontrol eder ve uygun randevuları bildirir.
- **Hata Yönetimi:** Randevu kontrolü sırasında oluşabilecek hatalar için ayrıntılı loglama ve hata yönetimi.
- **Kullanıcı Yetkilendirmesi:** Sadece belirli kullanıcıların botu kullanabilmesi için yetkilendirme sistemi.

## Hata Yönetimi
Bot, aşağıdaki hataları yönetir:
- **ChromeDriver Hataları:** ChromeDriver ile ilgili sürüm uyumsuzlukları ve başlatma hataları.
- **Ağ Hataları:** Randevu kontrolü sırasında ağ bağlantısı sorunları.
- **HTML Parsing Hataları:** Sayfa yapısında değişiklikler olduğunda oluşabilecek parsing hataları.
- **Kullanıcı Girişi Hataları:** Yanlış kullanıcı bilgileri girildiğinde oluşabilecek hatalar.

## Gereksinimler
- Python 3.x
- `selenium`
- `webdriver-manager`
- `python-telegram-bot`
- `beautifulsoup4`
- `python-dotenv`

## Kurulum
1. Depoyu klonlayın:
   ```bash
   git clone <repo-url>
   cd schengen-visa-bot
   ```
2. Gerekli bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
3. `.env` dosyasını oluşturun ve gerekli ortam değişkenlerini ekleyin:
   ```bash
   TELEGRAM_TOKEN=<your-telegram-bot-token>
   USER_EMAIL=<your-email>
   USER_PASSWORD=<your-password>
   ALLOWED_USERS=<comma-separated-user-ids>
   ADMIN_USER_ID=<your-admin-user-id>
   ```
4. Botu çalıştırın:
   ```bash
   python3 bot.py
   ```

## Kullanım
- `/start`: Botu başlatır.
- `/setpreferences`: Randevu tercihlerinizi ayarlamak için kullanılır.

## Katkıda Bulunma
Herhangi bir katkıda bulunmak isterseniz, lütfen bir pull request gönderin veya sorunları bildirin.

## Lisans
Bu proje MIT Lisansı altında lisanslanmıştır.

MIT Lisansı

Copyright (c) 2025 [ibidi]

İzin verilir, kopyalanabilir ve dağıtılabilir, ancak aşağıdaki koşullara uyulmalıdır:

1. Yukarıdaki telif hakkı bildirimi ve bu izin bildirimi, tüm kopyalarda veya önemli bir kısmında yer almalıdır.
2. Bu yazılım, "olduğu gibi" sağlanmaktadır ve hiçbir garanti verilmemektedir. Bu, açık veya zımni, ticari elverişlilik veya belirli bir amaca uygunluk dahil, ancak bunlarla sınırlı olmamak üzere, garantileri içerir. Yazar veya telif hakkı sahipleri, bu yazılımın kullanımından kaynaklanan herhangi bir talep, zarar veya diğer yükümlülüklerden sorumlu değildir.

# VFS Global Vize Randevu Takip Botu

Bu Telegram botu, VFS Global üzerinden vize randevularını otomatik olarak takip eder ve uygun randevular bulunduğunda size bildirim gönderir.

## Özellikler

- VFS Global websitesini düzenli olarak kontrol eder
- Yeni randevular bulunduğunda Telegram üzerinden bildirim gönderir
- Kolay kullanım için basit komutlar
- Çoklu kullanıcı desteği

## Kurulum

1. Gerekli Python paketlerini yükleyin:
```bash
pip install -r requirements.txt
```

2. Telegram Bot Token'ı alın:
   - Telegram'da @BotFather ile konuşun
   - `/newbot` komutunu kullanarak yeni bir bot oluşturun
   - Size verilen API token'ı kaydedin

3. `.env.example` dosyasını `.env` olarak kopyalayın ve Telegram Bot Token'ınızı ekleyin:
```bash
cp .env.example .env
```

4. `.env` dosyasını düzenleyin ve `TELEGRAM_BOT_TOKEN` değerini kendi bot token'ınızla değiştirin.

## Kullanım

Botu başlatmak için:
```bash
python bot.py
```

### Telegram Komutları

- `/start` - Botu başlat ve randevu takibini aktifleştir
- `/stop` - Randevu takibini durdur
- `/help` - Yardım mesajını göster

## Güvenlik Notları

- `.env` dosyanızı asla GitHub'a pushlamayın
- Bot token'ınızı gizli tutun
- VFS Global'in kullanım şartlarına uygun kullanmaya özen gösterin

## Katkıda Bulunma

1. Bu repository'yi fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Bir Pull Request oluşturun 
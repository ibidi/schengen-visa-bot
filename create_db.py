from web_app import app, db, User, Notification, AppointmentLog
from werkzeug.security import generate_password_hash
import os

def create_database():
    with app.app_context():
        # Veritabanını oluştur
        db.drop_all()  # Önce tüm tabloları sil
        db.create_all()  # Sonra yeniden oluştur
        
        # İlk kullanıcıyı kontrol et ve oluştur
        admin_user = User(
            username='admin',
            password=generate_password_hash('admin123'),  # Güvenli şifre hash'i
            telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID'),
            notification_sound=True,
            notification_desktop=True,
            notification_telegram=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Admin kullanıcısı oluşturuldu!")
        print("👤 Kullanıcı adı: admin")
        print("🔑 Şifre: admin123")

if __name__ == '__main__':
    print("🔄 Veritabanı oluşturuluyor...")
    create_database()
    print("✅ Veritabanı oluşturuldu!") 
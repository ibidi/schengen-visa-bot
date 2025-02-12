from web_app import app, db, User
from werkzeug.security import generate_password_hash
import os

def create_database():
    with app.app_context():
        # Veritabanını oluştur
        db.create_all()
        
        # İlk kullanıcıyı kontrol et ve oluştur
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                password=generate_password_hash('admin123'),  # Güvenli şifre hash'i
                telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID')
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Admin kullanıcısı oluşturuldu!")
            print("👤 Kullanıcı adı: admin")
            print("🔑 Şifre: admin123")
        else:
            print("ℹ️ Admin kullanıcısı zaten mevcut.")

if __name__ == '__main__':
    print("🔄 Veritabanı oluşturuluyor...")
    create_database()
    print("✅ Veritabanı oluşturuldu!") 
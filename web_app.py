from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os
from bot import AppointmentChecker
from dotenv import load_dotenv
from werkzeug.security import check_password_hash

# Çevre değişkenlerini yükle
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'gizli-anahtar-123')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///visa_bot.db'
socketio = SocketIO(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ülke grupları
SCHENGEN_COUNTRIES = {
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

VFS_COUNTRIES = {
    'UK': 'İngiltere',
    'CAN': 'Kanada',
    'AUS': 'Avustralya',
    'NZL': 'Yeni Zelanda',
    'ZAF': 'Güney Afrika'
}

OTHER_COUNTRIES = {
    'ITA': 'İtalya',
    'DEU': 'Almanya'
}

# Veritabanı modelleri
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    telegram_chat_id = db.Column(db.String(80), unique=True)
    notification_sound = db.Column(db.Boolean, default=True)
    notification_desktop = db.Column(db.Boolean, default=True)
    notification_telegram = db.Column(db.Boolean, default=True)
    
    @property
    def unread_notifications(self):
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()

class AppointmentLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(80), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    country = db.Column(db.String(80), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    appointment_date = db.Column(db.String(80))
    appointment_link = db.Column(db.String(255))

# Bot örneği
bot = AppointmentChecker()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    return render_template('index.html', 
                         schengen_countries=SCHENGEN_COUNTRIES,
                         vfs_countries=VFS_COUNTRIES,
                         other_countries=OTHER_COUNTRIES)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Geçersiz kullanıcı adı veya şifre')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/start_check', methods=['POST'])
@login_required
def start_check():
    data = request.json
    country = data.get('country')
    city = data.get('city')
    frequency = data.get('frequency')
    
    if not all([country, city, frequency]):
        return jsonify({'error': 'Eksik parametreler'}), 400
    
    try:
        bot.country = country
        bot.city = city
        bot.frequency = int(frequency)
        bot.start_checking(current_user.telegram_chat_id)
        
        # Log kaydı
        log = AppointmentLog(
            country=country,
            city=city,
            date=datetime.now(),
            status='started',
            user_id=current_user.id
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stop_check', methods=['POST'])
@login_required
def stop_check():
    try:
        bot.stop_checking(current_user.telegram_chat_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status')
@login_required
def get_status():
    active_checks = bot.active_checks.get(current_user.telegram_chat_id)
    return jsonify({
        'is_active': bool(active_checks),
        'country': bot.country,
        'city': bot.city,
        'frequency': bot.frequency
    })

@app.route('/logs')
@login_required
def get_logs():
    logs = AppointmentLog.query.filter_by(user_id=current_user.id).order_by(AppointmentLog.date.desc()).limit(50)
    return jsonify([{
        'country': log.country,
        'city': log.city,
        'date': log.date.strftime('%Y-%m-%d %H:%M:%S'),
        'status': log.status
    } for log in logs])

@app.route('/notifications')
@login_required
def notifications():
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.date.desc()).all()
    return render_template('notifications.html', notifications=notifications)

@app.route('/mark_notification_read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()
    return redirect(url_for('notifications'))

@app.route('/notification_settings')
@login_required
def notification_settings():
    return render_template('notification_settings.html')

@app.route('/save_notification_settings', methods=['POST'])
@login_required
def save_notification_settings():
    data = request.json
    user = User.query.get(current_user.id)
    user.notification_sound = data.get('sound', True)
    user.notification_desktop = data.get('desktop', True)
    user.notification_telegram = data.get('telegram', True)
    db.session.commit()
    return jsonify({'success': True})

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        socketio.emit('status_update', {
            'is_active': bool(bot.active_checks.get(current_user.telegram_chat_id)),
            'country': bot.country,
            'city': bot.city,
            'frequency': bot.frequency
        }, room=request.sid)

def send_notification(user_id, country, city, message, appointment_date=None, appointment_link=None):
    """Bildirim gönder"""
    try:
        notification = Notification(
            user_id=user_id,
            country=country,
            city=city,
            date=datetime.now(),
            message=message,
            appointment_date=appointment_date,
            appointment_link=appointment_link,
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()
        
        # WebSocket ile anlık bildirim gönder
        notification_data = {
            'id': notification.id,
            'message': message,
            'country': country,
            'city': city,
            'date': notification.date.strftime('%Y-%m-%d %H:%M:%S'),
            'appointment_date': appointment_date,
            'appointment_link': appointment_link
        }
        
        socketio.emit('new_notification', notification_data, broadcast=True)
        
        # Telegram bildirimi gönder
        user = User.query.get(user_id)
        if user and user.notification_telegram and user.telegram_chat_id:
            bot.send_notification(message)
            
        return True
    except Exception as e:
        print(f"Bildirim gönderme hatası: {str(e)}")
        return False

# Veritabanını oluştur
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    socketio.run(app, debug=True) 
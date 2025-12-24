from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)

# ========== КОНФИГУРАЦИЯ ==========
app.config['SECRET_KEY'] = 'dev-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///college_repair.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# ==================================

db = SQLAlchemy(app)

# Модели базы данных
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, user, technician
    full_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    requests = db.relationship('RepairRequest', backref='author', lazy=True)

    def __repr__(self):
        return f'<User {self.username} - {self.role}>'

class RepairRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    computer_number = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    problem_description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<RepairRequest {self.id} - {self.computer_number}>'

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки прав администратора
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Требуются права администратора', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки прав специалиста
def technician_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role != 'technician':
            flash('Требуются права специалиста', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки прав специалиста ИЛИ администратора
def technician_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role not in ['technician', 'admin']:
            flash('Требуются права специалиста или администратора', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Маршруты
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        print(f"DEBUG: Попытка входа - пользователь: {username}, пароль: {password}")
        
        user = User.query.filter_by(username=username, password=password).first()
        
        if user:
            print(f"DEBUG: Пользователь найден - {user.username}, роль: {user.role}")
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['full_name'] = user.full_name
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('dashboard'))
        else:
            print(f"DEBUG: Пользователь НЕ найден")
            flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    
    # Статистика для админа и специалиста
    if user.role in ['admin', 'technician']:
        total_requests = RepairRequest.query.count()
        pending_requests = RepairRequest.query.filter_by(status='pending').count()
        in_progress_requests = RepairRequest.query.filter_by(status='in_progress').count()
        completed_requests = RepairRequest.query.filter_by(status='completed').count()
        
        stats = {
            'total': total_requests,
            'pending': pending_requests,
            'in_progress': in_progress_requests,
            'completed': completed_requests
        }
    else:
        stats = None
    
    return render_template('dashboard.html', user=user, stats=stats)

@app.route('/requests')
@login_required
def view_requests():
    user = User.query.get(session['user_id'])
    
    if user.role in ['admin', 'technician']:
        # Админ и специалист видят все заявки
        requests = RepairRequest.query.order_by(RepairRequest.created_at.desc()).all()
    else:
        # Пользователь видит только свои заявки
        requests = RepairRequest.query.filter_by(user_id=user.id).order_by(RepairRequest.created_at.desc()).all()
    
    return render_template('view_requests.html', requests=requests, user=user)

@app.route('/requests/create', methods=['GET', 'POST'])
@login_required
def create_request():
    # Только пользователи (не админы и не специалисты) могут создавать заявки
    user = User.query.get(session['user_id'])
    if user.role not in ['user']:
        flash('Только обычные пользователи могут создавать заявки', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        computer_number = request.form['computer_number']
        location = request.form['location']
        problem_description = request.form['problem_description']
        priority = request.form.get('priority', 'medium')
        
        new_request = RepairRequest(
            user_id=session['user_id'],
            computer_number=computer_number,
            location=location,
            problem_description=problem_description,
            priority=priority
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        flash('Заявка успешно создана!', 'success')
        return redirect(url_for('view_requests'))
    
    return render_template('create_request.html')

@app.route('/requests/<int:request_id>/update_status', methods=['POST'])
@login_required
@technician_or_admin_required
def update_request_status(request_id):
    repair_request = RepairRequest.query.get_or_404(request_id)
    new_status = request.form['status']
    
    repair_request.status = new_status
    db.session.commit()
    
    flash('Статус заявки обновлен!', 'success')
    return redirect(url_for('view_requests'))

@app.route('/requests/<int:request_id>/view')
@login_required
@technician_or_admin_required
def view_request_details(request_id):
    """Просмотр деталей заявки (для специалиста и администратора)"""
    repair_request = RepairRequest.query.get_or_404(request_id)
    return render_template('request_details.html', request=repair_request)

@app.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        role = request.form['role']
        
        # Проверяем, не существует ли уже пользователь с таким именем
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Пользователь с таким именем уже существует', 'danger')
            return redirect(url_for('create_user'))
        
        # Валидация пароля
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'danger')
            return redirect(url_for('create_user'))
        
        # Валидация имени пользователя
        if not username.isalnum():
            flash('Имя пользователя должно содержать только буквы и цифры', 'danger')
            return redirect(url_for('create_user'))
        
        # Создаем нового пользователя
        new_user = User(
            username=username,
            password=password,
            full_name=full_name,
            role=role
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Детальное сообщение о создании пользователя
        role_names = {
            'user': 'Пользователь',
            'technician': 'Специалист по ремонту',
            'admin': 'Администратор'
        }
        
        flash({
            'type': 'success',
            'title': 'Пользователь успешно создан!',
            'message': f'{role_names.get(role, role)} "{full_name}" добавлен в систему.',
            'username': username,
            'password': password,
            'role': role_names.get(role, role)
        }, 'user_created')
        
        return redirect(url_for('create_user'))
    
    return render_template('create_user.html')

# API endpoint для получения заявок (для AJAX)
@app.route('/api/requests')
@login_required
def api_requests():
    user = User.query.get(session['user_id'])
    
    if user.role in ['admin', 'technician']:
        requests = RepairRequest.query.order_by(RepairRequest.created_at.desc()).all()
    else:
        requests = RepairRequest.query.filter_by(user_id=user.id).order_by(RepairRequest.created_at.desc()).all()
    
    requests_list = []
    for req in requests:
        requests_list.append({
            'id': req.id,
            'computer_number': req.computer_number,
            'location': req.location,
            'problem_description': req.problem_description,
            'status': req.status,
            'priority': req.priority,
            'created_at': req.created_at.strftime('%Y-%m-%d %H:%M'),
            'author': req.author.full_name
        })
    
    return jsonify(requests_list)

# Маршрут для специалиста - мои задачи
@app.route('/technician/tasks')
@login_required
def technician_tasks():
    """Задачи для специалиста"""
    user = User.query.get(session['user_id'])
    
    # Проверяем, что это специалист
    if user.role != 'technician':
        flash('Требуются права специалиста', 'danger')
        return redirect(url_for('dashboard'))
    
    # Специалист видит все заявки, но можно фильтровать только те, что в работе
    in_progress_requests = RepairRequest.query.filter_by(status='in_progress').order_by(RepairRequest.created_at.desc()).all()
    pending_requests = RepairRequest.query.filter_by(status='pending').order_by(RepairRequest.created_at.desc()).all()
    
    return render_template('technician_tasks.html', 
                          in_progress_requests=in_progress_requests,
                          pending_requests=pending_requests,
                          user=user)

def create_default_users():
    """Создание тестовых пользователей если их нет"""
    with app.app_context():
        print("=" * 60)
        print("Проверка и создание тестовых пользователей...")
        print("=" * 60)
        
        # Список всех тестовых пользователей
        all_users = [
            {
                'username': 'admin',
                'password': 'admin123',
                'role': 'admin',
                'full_name': 'Администратор Системы'
            },
            {
                'username': 'student1',
                'password': 'student123',
                'role': 'user',
                'full_name': 'Иванов Иван Петрович'
            },
            {
                'username': 'student2',
                'password': 'student123',
                'role': 'user',
                'full_name': 'Петрова Анна Сергеевна'
            },
            {
                'username': 'teacher1',
                'password': 'teacher123',
                'role': 'user',
                'full_name': 'Сидоров Михаил Владимирович'
            },
            {
                'username': 'technician1',
                'password': 'tech123',
                'role': 'technician',
                'full_name': 'Сергеев Алексей Викторович'
            }
        ]
        
        created_count = 0
        existing_count = 0
        
        for user_data in all_users:
            # Проверяем, существует ли уже пользователь
            existing_user = User.query.filter_by(username=user_data['username']).first()
            
            if existing_user:
                # Обновляем существующего пользователя
                existing_user.password = user_data['password']
                existing_user.role = user_data['role']
                existing_user.full_name = user_data['full_name']
                existing_count += 1
                print(f"✓ Пользователь {user_data['username']} обновлен")
            else:
                # Создаем нового пользователя
                new_user = User(
                    username=user_data['username'],
                    password=user_data['password'],
                    role=user_data['role'],
                    full_name=user_data['full_name']
                )
                db.session.add(new_user)
                created_count += 1
                print(f"✓ Пользователь {user_data['username']} создан")
        
        try:
            db.session.commit()
            print("\n" + "=" * 60)
            print("РЕЗУЛЬТАТ:")
            print(f"✅ Создано: {created_count} пользователей")
            print(f"📝 Обновлено: {existing_count} пользователей")
            print("=" * 60)
            
            # Показываем список всех пользователей
            users = User.query.all()
            print("\nСПИСОК ПОЛЬЗОВАТЕЛЕЙ В БАЗЕ:")
            print("-" * 40)
            for user in users:
                print(f"• {user.username} ({user.role}): {user.full_name}")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Ошибка при сохранении пользователей: {e}")

def create_test_requests():
    """Создание тестовых заявок"""
    with app.app_context():
        # Проверяем, есть ли уже заявки
        if RepairRequest.query.count() == 0:
            print("\nСоздание тестовых заявок...")
            
            # Получаем пользователей
            users = User.query.all()
            if not users:
                print("❌ Нет пользователей для создания заявок")
                return
            
            # Создаем тестовые заявки
            test_requests = [
                {
                    'user_id': 2,  # student1
                    'computer_number': 'PC-101',
                    'location': 'Аудитория 301',
                    'problem_description': 'Не включается компьютер. При нажатии кнопки питания ничего не происходит.',
                    'status': 'pending',
                    'priority': 'high'
                },
                {
                    'user_id': 3,  # student2
                    'computer_number': 'PC-205',
                    'location': 'Компьютерный класс №2',
                    'problem_description': 'Медленно работает компьютер. Загрузка системы занимает более 5 минут.',
                    'status': 'in_progress',
                    'priority': 'medium'
                },
                {
                    'user_id': 4,  # teacher1
                    'computer_number': 'LAPTOP-12',
                    'location': 'Библиотека',
                    'problem_description': 'Не работает Wi-Fi адаптер. Компьютер не подключается к сети.',
                    'status': 'completed',
                    'priority': 'high'
                },
                {
                    'user_id': 2,  # student1
                    'computer_number': 'PC-308',
                    'location': 'Кабинет информатики',
                    'problem_description': 'Не работает проектор. Изображение не выводится на экран.',
                    'status': 'pending',
                    'priority': 'medium'
                }
            ]
            
            for req_data in test_requests:
                # Проверяем, существует ли пользователь с таким ID
                user = User.query.get(req_data['user_id'])
                if user:
                    request = RepairRequest(
                        user_id=req_data['user_id'],
                        computer_number=req_data['computer_number'],
                        location=req_data['location'],
                        problem_description=req_data['problem_description'],
                        status=req_data['status'],
                        priority=req_data['priority']
                    )
                    db.session.add(request)
                    print(f"✓ Заявка создана: {req_data['computer_number']} - {req_data['status']}")
            
            try:
                db.session.commit()
                print("✅ Тестовые заявки созданы!")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Ошибка при создании заявок: {e}")

if __name__ == '__main__':
    # Создаем таблицы
    with app.app_context():
        try:
            print("🔄 Создание таблиц базы данных...")
            db.create_all()
            print("✅ Таблицы базы данных созданы")
            
            # Создаем тестовых пользователей
            create_default_users()
            
            # Создаем тестовые заявки
            create_test_requests()
            
        except Exception as e:
            print(f"❌ Ошибка при создании базы данных: {e}")
    
    # Запускаем приложение
    print("\n" + "="*70)
    print("🚀 СИСТЕМА РЕМОНТА КОМПЬЮТЕРОВ В КОЛЛЕДЖЕ")
    print("="*70)
    print("Сервер запущен!")
    print("🌐 Откройте в браузере: http://localhost:5000")
    print("\n📋 ДАННЫЕ ДЛЯ ВХОДА:")
    print("-" * 40)
    print("👑 Администратор:")
    print("   Логин: admin")
    print("   Пароль: admin123")
    print("\n🔧 Специалист по ремонту:")
    print("   Логин: technician1")
    print("   Пароль: tech123")
    print("\n👤 Пользователи:")
    print("   Логин: student1 / Пароль: student123")
    print("   Логин: student2 / Пароль: student123")
    print("   Логин: teacher1 / Пароль: teacher123")
    print("\n📱 Возможности специалиста:")
    print("   • Просмотр всех заявок")
    print("   • Изменение статуса заявок")
    print("   • Панель 'Мои задачи'")
    print("   • Не может создавать пользователей")
    print("="*70 + "\n")
    
    app.run(debug=True, port=5000, use_reloader=True)
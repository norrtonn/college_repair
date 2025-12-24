"""
Простой скрипт для создания базы данных SQLite
"""

import os
import sys

print("=" * 60)
print("Создание базы данных для системы ремонта компьютеров")
print("=" * 60)

# Проверяем, есть ли уже файл базы данных
db_file = "college_repair.db"
if os.path.exists(db_file):
    print(f"⚠️  Файл {db_file} уже существует")
    response = input("Удалить и создать заново? (yes/no): ")
    if response.lower() != 'yes':
        print("Операция отменена")
        sys.exit(0)
    else:
        os.remove(db_file)
        print(f"✓ Файл {db_file} удален")

# Импортируем app для создания базы данных
try:
    from app import app, db, User, RepairRequest
    
    with app.app_context():
        # Создаем таблицы
        db.create_all()
        print("✓ Таблицы созданы")
        
        # Создаем тестовых пользователей
        admin = User(
            username='admin',
            password='admin123',
            role='admin',
            full_name='Администратор'
        )
        
        student1 = User(
            username='student1',
            password='student123',
            role='user',
            full_name='Иванов Иван'
        )
        
        db.session.add(admin)
        db.session.add(student1)
        db.session.commit()
        
        print("✓ Тестовые пользователи созданы")
        print("\n" + "=" * 60)
        print("ДАННЫЕ ДЛЯ ВХОДА:")
        print("=" * 60)
        print("Администратор: admin / admin123")
        print("Студент: student1 / student123")
        print("\n" + "=" * 60)
        
        if os.path.exists(db_file):
            size = os.path.getsize(db_file)
            print(f"📁 Файл базы данных: {db_file}")
            print(f"📊 Размер: {size} байт")
        
        print("\n✅ База данных создана успешно!")
        print("🚀 Запустите приложение: python app.py")
        
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что файл app.py находится в той же папке")
except Exception as e:
    print(f"❌ Ошибка: {e}")
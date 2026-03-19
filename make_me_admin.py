# make_me_admin.py
import sqlite3
import json
from datetime import datetime

# Ваш Telegram ID (узнайте у @userinfobot)
YOUR_TELEGRAM_ID = 5658400513  # ЗАМЕНИТЕ НА СВОЙ ID!

# Путь к базе данных
DATABASE_PATH = "electrician_bot.db"

def make_admin():
    """Добавляет себя как администратора"""
    
    # Вводим свои данные
    print("=== НАСТРОЙКА АДМИНИСТРАТОРА ===\n")
    
    telegram_id = int(input("Введите ваш Telegram ID: "))
    full_name = input("Введите ваше ФИО: ")
    phone = input("Введите ваш номер телефона: ")
    
    # Подключаемся к БД
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже такой пользователь
    cursor.execute("SELECT telegram_id FROM electricians WHERE telegram_id = ?", (telegram_id,))
    existing = cursor.fetchone()
    
    if existing:
        # Обновляем существующего - делаем админом
        cursor.execute('''
            UPDATE electricians 
            SET is_admin = 1, is_active = 1, full_name = ?, phone = ?
            WHERE telegram_id = ?
        ''', (full_name, phone, telegram_id))
        print("✅ Пользователь обновлен, теперь он администратор!")
    else:
        # Создаем нового администратора со всеми районами
        all_districts = [1, 2, 3, 4, 5, 6, 7, 8]  # все районы
        districts_json = json.dumps(all_districts)
        
        cursor.execute('''
            INSERT INTO electricians 
            (telegram_id, full_name, phone, districts, is_active, total_orders_taken, rating, joined_at, is_admin)
            VALUES (?, ?, ?, ?, 1, 0, 0.0, ?, 1)
        ''', (telegram_id, full_name, phone, districts_json, datetime.now()))
        print("✅ Новый администратор успешно добавлен!")
    
    conn.commit()
    conn.close()
    
    print(f"\n📊 Информация:")
    print(f"🆔 ID: {telegram_id}")
    print(f"👤 Имя: {full_name}")
    print(f"📞 Телефон: {phone}")
    print(f"👑 Статус: АДМИНИСТРАТОР")
    print("\n✅ Теперь вы можете использовать команды:")
    print("• /stats - статистика")
    print("• /electricians - список монтажников")
    print("• /add_electrician - добавить монтажника")
    print("• /active - активные на смене")

if __name__ == "__main__":
    make_admin()

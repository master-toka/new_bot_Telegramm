# make_me_admin.py - Упрощенная версия без интерактивного ввода
import sqlite3
import json
from datetime import datetime

# ===== ВСТАВЬТЕ СВОИ ДАННЫЕ ЗДЕСЬ =====
YOUR_TELEGRAM_ID = 5658400513  # Ваш ID из @userinfobot
YOUR_NAME = "Александр"            # Ваше имя
YOUR_PHONE = "+79240138454"   # Ваш телефон
# ======================================

# Путь к базе данных
DATABASE_PATH = "electrician_bot.db"

def make_admin():
    """Добавляет администратора в базу данных"""
    
    print("=== НАСТРОЙКА АДМИНИСТРАТОРА ===\n")
    print(f"📌 Добавляем администратора:")
    print(f"🆔 ID: {YOUR_TELEGRAM_ID}")
    print(f"👤 Имя: {YOUR_NAME}")
    print(f"📞 Телефон: {YOUR_PHONE}")
    
    try:
        # Подключаемся к БД
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Все районы (1-8)
        all_districts = [1, 2, 3, 4, 5, 6, 7, 8]
        districts_json = json.dumps(all_districts)
        
        # Проверяем, есть ли уже такой пользователь
        cursor.execute("SELECT telegram_id FROM electricians WHERE telegram_id = ?", (YOUR_TELEGRAM_ID,))
        existing = cursor.fetchone()
        
        if existing:
            # Обновляем существующего - делаем админом
            cursor.execute('''
                UPDATE electricians 
                SET is_admin = 1, 
                    is_active = 1, 
                    full_name = ?, 
                    phone = ?,
                    districts = ?
                WHERE telegram_id = ?
            ''', (YOUR_NAME, YOUR_PHONE, districts_json, YOUR_TELEGRAM_ID))
            print("✅ Пользователь обновлен, теперь он администратор!")
        else:
            # Создаем нового администратора
            cursor.execute('''
                INSERT INTO electricians 
                (telegram_id, full_name, phone, districts, is_active, total_orders_taken, rating, joined_at, is_admin)
                VALUES (?, ?, ?, ?, 1, 0, 0.0, ?, 1)
            ''', (YOUR_TELEGRAM_ID, YOUR_NAME, YOUR_PHONE, districts_json, datetime.now()))
            print("✅ Новый администратор успешно добавлен!")
        
        conn.commit()
        conn.close()
        
        print(f"\n📊 ИТОГ:")
        print(f"🆔 ID: {YOUR_TELEGRAM_ID}")
        print(f"👤 Имя: {YOUR_NAME}")
        print(f"📞 Телефон: {YOUR_PHONE}")
        print(f"👑 Статус: АДМИНИСТРАТОР")
        print("\n✅ Теперь вы можете использовать команды:")
        print("• /stats - статистика")
        print("• /electricians - список монтажников")
        print("• /add_electrician - добавить монтажника")
        print("• /active - активные на смене")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("\n💡 Возможные причины:")
        print("• Неправильный путь к базе данных")
        print("• База данных еще не создана (запустите бота хотя бы раз)")
        print("• Нет прав на запись")

if __name__ == "__main__":
    make_admin()

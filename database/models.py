# database/models.py
import sqlite3
import json
from datetime import datetime
from config import DATABASE_PATH

def init_db():
    """Создание всех таблиц при первом запуске"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей (клиенты)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            phone TEXT,
            registered_at TIMESTAMP,
            total_orders INTEGER DEFAULT 0,
            is_blocked INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица монтажников
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS electricians (
            telegram_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            districts TEXT,  -- JSON список районов
            is_active INTEGER DEFAULT 1,
            total_orders_taken INTEGER DEFAULT 0,
            rating REAL DEFAULT 0,
            joined_at TIMESTAMP,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица заказов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE,
            user_id INTEGER,
            district_id INTEGER,
            description TEXT,
            photo_id TEXT,
            address TEXT,
            location_lat REAL,
            location_lon REAL,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP,
            taken_by INTEGER,
            taken_at TIMESTAMP,
            completed_at TIMESTAMP,
            cancelled_at TIMESTAMP,
            cancel_reason TEXT,
            client_rating INTEGER,
            client_review TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (taken_by) REFERENCES electricians(telegram_id)
        )
    ''')
    
    # Таблица истории заказов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            old_status TEXT,
            new_status TEXT,
            changed_by INTEGER,
            changed_at TIMESTAMP,
            comment TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name, phone=None):
    """Добавление нового пользователя"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже пользователь
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        conn.close()
        return False
    
    cursor.execute('''
        INSERT INTO users (user_id, username, first_name, phone, registered_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, phone, datetime.now()))
    
    conn.commit()
    conn.close()
    return True

def get_user(user_id):
    """Получение данных пользователя"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    return user

def add_electrician(telegram_id, full_name, phone, districts, is_admin=0):
    """Добавление монтажника в систему"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    districts_json = json.dumps(districts)
    
    cursor.execute('''
        INSERT INTO electricians (telegram_id, full_name, phone, districts, joined_at, is_admin)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (telegram_id, full_name, phone, districts_json, datetime.now(), is_admin))
    
    conn.commit()
    conn.close()

def is_electrician(telegram_id):
    """Проверка, является ли пользователь монтажником"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT telegram_id FROM electricians WHERE telegram_id = ? AND is_active = 1", (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def is_admin(telegram_id):
    """Проверка прав администратора"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_admin FROM electricians WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result and result[0] == 1

def create_order(user_id, district_id, description, address, photo_id=None, lat=None, lon=None):
    """Создание новой заявки"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Генерируем номер заказа (дата + номер)
    from datetime import datetime
    date_str = datetime.now().strftime("%y%m%d")
    
    # Получаем последний номер заказа за сегодня
    cursor.execute('''
        SELECT order_number FROM orders 
        WHERE order_number LIKE ? 
        ORDER BY order_id DESC LIMIT 1
    ''', (f"{date_str}-%",))
    
    last_order = cursor.fetchone()
    if last_order:
        last_num = int(last_order[0].split('-')[1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    order_number = f"{date_str}-{new_num:03d}"
    
    cursor.execute('''
        INSERT INTO orders 
        (order_number, user_id, district_id, description, photo_id, address, 
         location_lat, location_lon, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (order_number, user_id, district_id, description, photo_id, address, 
          lat, lon, 'new', datetime.now()))
    
    order_id = cursor.lastrowid
    
    # Обновляем счетчик заказов у пользователя
    cursor.execute('''
        UPDATE users SET total_orders = total_orders + 1 
        WHERE user_id = ?
    ''', (user_id,))
    
    conn.commit()
    conn.close()
    
    return order_id, order_number

def get_order(order_id):
    """Получение заказа по ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT o.*, u.username, u.first_name, u.phone 
        FROM orders o
        LEFT JOIN users u ON o.user_id = u.user_id
        WHERE o.order_id = ?
    ''', (order_id,))
    
    order = cursor.fetchone()
    conn.close()
    
    return order

def take_order(order_id, electrician_id):
    """Монтажник берет заказ"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE orders 
        SET status = 'in_progress', taken_by = ?, taken_at = ?
        WHERE order_id = ? AND status = 'new'
    ''', (electrician_id, datetime.now(), order_id))
    
    affected = cursor.rowcount
    
    if affected > 0:
        # Обновляем счетчик монтажника
        cursor.execute('''
            UPDATE electricians 
            SET total_orders_taken = total_orders_taken + 1 
            WHERE telegram_id = ?
        ''', (electrician_id,))
        
        # Запись в историю
        cursor.execute('''
            INSERT INTO order_history (order_id, old_status, new_status, changed_by, changed_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (order_id, 'new', 'in_progress', electrician_id, datetime.now()))
    
    conn.commit()
    conn.close()
    
    return affected > 0

def complete_order(order_id, electrician_id):
    """Завершение заказа"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE orders 
        SET status = 'completed', completed_at = ?
        WHERE order_id = ? AND taken_by = ? AND status = 'in_progress'
    ''', (datetime.now(), order_id, electrician_id))
    
    affected = cursor.rowcount
    
    if affected > 0:
        cursor.execute('''
            INSERT INTO order_history (order_id, old_status, new_status, changed_by, changed_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (order_id, 'in_progress', 'completed', electrician_id, datetime.now()))
    
    conn.commit()
    conn.close()
    
    return affected > 0

def cancel_order(order_id, user_id, reason='client_cancelled'):
    """Отмена заказа клиентом"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE orders 
        SET status = 'cancelled', cancelled_at = ?, cancel_reason = ?
        WHERE order_id = ? AND user_id = ?
    ''', (datetime.now(), reason, order_id, user_id))
    
    affected = cursor.rowcount
    
    if affected > 0:
        cursor.execute('''
            INSERT INTO order_history (order_id, old_status, new_status, changed_by, changed_at, comment)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (order_id, 'any', 'cancelled', user_id, datetime.now(), reason))
    
    conn.commit()
    conn.close()
    
    return affected > 0

def rate_order(order_id, user_id, rating, review=None):
    """Оценка заказа клиентом"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE orders 
        SET client_rating = ?, client_review = ?
        WHERE order_id = ? AND user_id = ? AND status = 'completed'
    ''', (rating, review, order_id, user_id))
    
    affected = cursor.rowcount
    
    if affected > 0 and rating <= 3:
        # Получаем информацию о монтажнике для уведомления
        cursor.execute('SELECT taken_by FROM orders WHERE order_id = ?', (order_id,))
        taken_by = cursor.fetchone()[0]
        
        if taken_by:
            # Обновляем рейтинг монтажника (упрощенно)
            cursor.execute('''
                UPDATE electricians 
                SET rating = (rating + ?) / 2 
                WHERE telegram_id = ?
            ''', (rating, taken_by))
    
    conn.commit()
    conn.close()
    
    return affected > 0

def get_user_orders(user_id, limit=5):
    """Получение последних заказов пользователя"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT order_number, status, created_at, district_id
        FROM orders 
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    orders = cursor.fetchall()
    conn.close()
    
    return orders
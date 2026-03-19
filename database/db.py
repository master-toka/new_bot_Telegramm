# database/db.py
import sqlite3
from config import DATABASE_PATH

def get_connection():
    """Получение соединения с БД"""
    return sqlite3.connect(DATABASE_PATH)

def execute_query(query, params=()):
    """Выполнение запроса без возврата данных"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def fetch_one(query, params=()):
    """Получение одной записи"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchone()
    conn.close()
    return result

def fetch_all(query, params=()):
    """Получение всех записей"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results
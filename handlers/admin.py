# handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import sqlite3
import json

from database.models import is_admin
from config import DATABASE_PATH, DISTRICTS
from datetime import datetime, timedelta

router = Router()

@router.message(Command("stats"))
async def admin_stats(message: Message):
    """Статистика для руководства"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    # Статистика за сегодня
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Всего заявок сегодня
    cursor.execute('''
        SELECT COUNT(*) FROM orders 
        WHERE DATE(created_at) = DATE(?)
    ''', (today,))
    total_today = cursor.fetchone()[0]
    
    # Выполнено сегодня
    cursor.execute('''
        SELECT COUNT(*) FROM orders 
        WHERE DATE(completed_at) = DATE(?) AND status = 'completed'
    ''', (today,))
    completed_today = cursor.fetchone()[0]
    
    # В работе сейчас
    cursor.execute('''
        SELECT COUNT(*) FROM orders WHERE status = 'in_progress'
    ''')
    in_progress = cursor.fetchone()[0]
    
    # Новые заявки
    cursor.execute('''
        SELECT COUNT(*) FROM orders WHERE status = 'new'
    ''')
    new_orders = cursor.fetchone()[0]
    
    # Заявки по районам
    cursor.execute('''
        SELECT district_id, COUNT(*) FROM orders 
        WHERE DATE(created_at) = DATE(?) 
        GROUP BY district_id
    ''', (today,))
    districts_stats = cursor.fetchall()
    
    conn.close()
    
    # Формируем статистику по районам
    districts_text = ""
    for district_id, count in districts_stats:
        district_name = DISTRICTS.get(district_id, f"Район {district_id}")
        districts_text += f"  • {district_name}: {count}\n"
    
    stats_text = f"""
📊 СТАТИСТИКА ЗА {today.strftime('%d.%m.%Y')}

📌 ОБЩАЯ:
• Всего заявок: {total_today}
• Выполнено: {completed_today}
• В работе сейчас: {in_progress}
• Новые: {new_orders}

📍 ПО РАЙОНАМ:
{districts_text if districts_text else "  • Нет данных"}
    """
    
    await message.answer(stats_text)

@router.message(Command("electricians"))
async def electricians_list(message: Message):
    """Список монтажников на смене"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT telegram_id, full_name, phone, districts, total_orders_taken, rating, is_active 
        FROM electricians 
        ORDER BY total_orders_taken DESC
    ''')
    
    electricians = cursor.fetchall()
    conn.close()
    
    if not electricians:
        await message.answer("Нет монтажников в базе данных")
        return
    
    text = "👷‍♂️ СПИСОК МОНТАЖНИКОВ:\n\n"
    
    for e in electricians:
        telegram_id, full_name, phone, districts_json, total_orders, rating, is_active = e
        
        # Парсим список районов
        try:
            districts = json.loads(districts_json) if districts_json else []
            district_names = [DISTRICTS.get(d, f"ID{d}") for d in districts]
            districts_str = ', '.join(district_names) if district_names else "Не назначены"
        except:
            districts_str = "Ошибка в данных"
        
        status = "✅ НА СМЕНЕ" if is_active else "💤 НЕ АКТИВЕН"
        
        text += f"👤 {full_name}\n"
        text += f"  📞 {phone}\n"
        text += f"  🆔 {telegram_id}\n"
        text += f"  📍 Районы: {districts_str}\n"
        text += f"  📊 Заказов: {total_orders} | ⭐ {rating:.1f}\n"
        text += f"  {status}\n\n"
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(text) > 4000:
        for i in range(0, len(text), 3500):
            await message.answer(text[i:i+3500])
    else:
        await message.answer(text)

@router.message(Command("orders_today"))
async def orders_today(message: Message):
    """Заявки за сегодня"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    today = datetime.now().date()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT order_number, district_id, status, created_at, taken_by 
        FROM orders 
        WHERE DATE(created_at) = DATE(?)
        ORDER BY created_at DESC
    ''', (today,))
    
    orders = cursor.fetchall()
    conn.close()
    
    if not orders:
        await message.answer("За сегодня заявок нет")
        return
    
    status_emoji = {
        'new': '🟡',
        'in_progress': '🔵',
        'completed': '✅',
        'cancelled': '❌'
    }
    
    text = f"📋 ЗАЯВКИ ЗА {today.strftime('%d.%m.%Y')}:\n\n"
    
    for order in orders:
        order_number, district_id, status, created_at, taken_by = order
        district_name = DISTRICTS.get(district_id, "?")
        emoji = status_emoji.get(status, '⚪')
        
        # Форматируем время
        time_str = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S.%f').strftime('%H:%M')
        
        text += f"{emoji} #{order_number} {time_str} - {district_name}\n"
    
    await message.answer(text)

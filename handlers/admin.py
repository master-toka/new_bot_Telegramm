# handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from database.models import is_admin, fetch_all
from config import DISTRICTS
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
    
    conn.close()
    
    stats_text = f"""
📊 СТАТИСТИКА

📅 За сегодня:
• Всего заявок: {total_today}
• Выполнено: {completed_today}

📌 Текущее состояние:
• Новые заявки: {new_orders}
• В работе: {in_progress}
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
        SELECT full_name, phone, districts, total_orders_taken, rating 
        FROM electricians 
        WHERE is_active = 1
        ORDER BY total_orders_taken DESC
    ''')
    
    electricians = cursor.fetchall()
    conn.close()
    
    if not electricians:
        await message.answer("Нет активных монтажников")
        return
    
    text = "👷‍♂️ МОНТАЖНИКИ НА СМЕНЕ:\n\n"
    
    for e in electricians:
        full_name, phone, districts_json, total_orders, rating = e
        import json
        districts = json.loads(districts_json)
        district_names = [DISTRICTS.get(d, "?") for d in districts]
        
        text += f"• {full_name}\n"
        text += f"  📞 {phone}\n"
        text += f"  📍 {', '.join(district_names)}\n"
        text += f"  📊 Заказов: {total_orders} | ⭐ {rating:.1f}\n\n"
    
    await message.answer(text)
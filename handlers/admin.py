# handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
import sqlite3
import json
from datetime import datetime, timedelta

from database.models import is_admin
from config import DATABASE_PATH, DISTRICTS
from states.order_states import AdminStates
from keyboards.reply import get_main_keyboard

router = Router()

# ================ СТАТИСТИКА ================

@router.message(Command("stats"))
async def admin_stats(message: Message):
    """Статистика для руководства"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    today = datetime.now().date()
    
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
    
    # Отмененные сегодня
    cursor.execute('''
        SELECT COUNT(*) FROM orders 
        WHERE DATE(cancelled_at) = DATE(?) AND status = 'cancelled'
    ''', (today,))
    cancelled_today = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = f"""
📊 СТАТИСТИКА ЗА {today.strftime('%d.%m.%Y')}

📌 ОБЩАЯ:
• Всего заявок: {total_today}
• Выполнено: {completed_today}
• Отменено: {cancelled_today}
• В работе сейчас: {in_progress}
• Новые: {new_orders}
    """
    
    await message.answer(stats_text)


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
        SELECT order_number, district_id, status, created_at, 
               taken_by, completed_at 
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
        'new': '🟡 НОВАЯ',
        'in_progress': '🔵 В РАБОТЕ',
        'completed': '✅ ВЫПОЛНЕНО',
        'cancelled': '❌ ОТМЕНЕНО'
    }
    
    text = f"📋 ЗАЯВКИ ЗА {today.strftime('%d.%m.%Y')}:\n\n"
    
    for order in orders:
        order_number, district_id, status, created_at, taken_by, completed_at = order
        district_name = DISTRICTS.get(district_id, "?")
        status_text = status_emoji.get(status, status)
        
        # Форматируем время
        created_time = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S.%f').strftime('%H:%M')
        
        text += f"#{order_number} {created_time} - {district_name}\n"
        text += f"  {status_text}\n"
        
        if taken_by and status == 'completed' and completed_at:
            complete_time = datetime.strptime(completed_at, '%Y-%m-%d %H:%M:%S.%f').strftime('%H:%M')
            text += f"  ✅ Завершено в {complete_time}\n"
        
        text += "\n"
    
    await message.answer(text)


# ================ УПРАВЛЕНИЕ МОНТАЖНИКАМИ ================

@router.message(Command("electricians"))
async def electricians_list(message: Message):
    """Список всех монтажников"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT telegram_id, full_name, phone, districts, total_orders_taken, rating, is_active, is_admin 
        FROM electricians 
        ORDER BY is_active DESC, total_orders_taken DESC
    ''')
    
    electricians = cursor.fetchall()
    conn.close()
    
    if not electricians:
        await message.answer("Нет монтажников в базе данных")
        return
    
    text = "👷‍♂️ СПИСОК МОНТАЖНИКОВ:\n\n"
    
    for e in electricians:
        telegram_id, full_name, phone, districts_json, total_orders, rating, is_active, is_admin_flag = e
        
        # Парсим список районов
        try:
            districts = json.loads(districts_json) if districts_json else []
            district_names = [DISTRICTS.get(d, f"ID{d}") for d in districts]
            districts_str = ', '.join(district_names) if district_names else "Не назначены"
        except:
            districts_str = "Ошибка в данных"
        
        status = "✅ НА СМЕНЕ" if is_active else "💤 НЕ АКТИВЕН"
        admin_status = "👑 АДМИН" if is_admin_flag else "🔧 МОНТАЖНИК"
        
        text += f"👤 {full_name}\n"
        text += f"  📞 {phone}\n"
        text += f"  🆔 {telegram_id}\n"
        text += f"  📍 {districts_str}\n"
        text += f"  📊 Заказов: {total_orders} | ⭐ {rating:.1f}\n"
        text += f"  {admin_status} | {status}\n\n"
    
    # Разбиваем на части, если сообщение слишком длинное
    if len(text) > 4000:
        for i in range(0, len(text), 3500):
            await message.answer(text[i:i+3500])
    else:
        await message.answer(text)


@router.message(Command("active"))
async def active_electricians(message: Message):
    """Активные монтажники на смене"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT full_name, phone, total_orders_taken 
        FROM electricians 
        WHERE is_active = 1
        ORDER BY total_orders_taken DESC
    ''')
    
    active = cursor.fetchall()
    conn.close()
    
    if not active:
        await message.answer("Нет активных монтажников на смене")
        return
    
    text = "✅ АКТИВНЫЕ МОНТАЖНИКИ:\n\n"
    for e in active:
        full_name, phone, total_orders = e
        text += f"• {full_name}\n"
        text += f"  📞 {phone}\n"
        text += f"  📊 Заказов: {total_orders}\n\n"
    
    await message.answer(text)


# ================ ДОБАВЛЕНИЕ НОВОГО МОНТАЖНИКА ================

@router.message(Command("add_electrician"))
async def add_electrician_start(message: Message, state: FSMContext):
    """Начало добавления нового монтажника"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    await message.answer(
        "👷‍♂️ ДОБАВЛЕНИЕ НОВОГО МОНТАЖНИКА\n\n"
        "Введите Telegram ID монтажника:\n"
        "(узнать ID можно у @userinfobot)"
    )
    await state.set_state(AdminStates.waiting_for_electrician_add)


@router.message(StateFilter(AdminStates.waiting_for_electrician_add))
async def process_electrician_id(message: Message, state: FSMContext):
    """Обработка ID монтажника"""
    try:
        telegram_id = int(message.text.strip())
        await state.update_data(telegram_id=telegram_id)
        
        await message.answer(
            "Введите ФИО монтажника:"
        )
        await state.set_state(AdminStates.waiting_for_electrician_name)
    except ValueError:
        await message.answer("❌ Некорректный ID. Введите число:")


@router.message(StateFilter(AdminStates.waiting_for_electrician_name))
async def process_electrician_name(message: Message, state: FSMContext):
    """Обработка имени монтажника"""
    full_name = message.text.strip()
    await state.update_data(full_name=full_name)
    
    await message.answer(
        "Введите номер телефона монтажника (например: +79140001122):"
    )
    await state.set_state(AdminStates.waiting_for_electrician_phone)


@router.message(StateFilter(AdminStates.waiting_for_electrician_phone))
async def process_electrician_phone(message: Message, state: FSMContext):
    """Обработка телефона монтажника"""
    phone = message.text.strip()
    await state.update_data(phone=phone)
    
    # Показываем список районов для выбора
    await message.answer(
        "Выберите районы, в которых работает монтажник\n"
        "(можно выбрать несколько, нажимая на кнопки):",
        reply_markup=get_districts_with_done_keyboard([])
    )
    await state.set_state(AdminStates.waiting_for_district_assign)


@router.callback_query(StateFilter(AdminStates.waiting_for_district_assign))
async def process_electrician_district(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора района для монтажника"""
    data = await state.get_data()
    selected_districts = data.get('selected_districts', [])
    
    if callback.data.startswith('district:'):
        district_id = int(callback.data.split(':')[1])
        
        if district_id in selected_districts:
            selected_districts.remove(district_id)
            await callback.answer(f"Район убран из списка")
        else:
            selected_districts.append(district_id)
            await callback.answer(f"Район добавлен")
        
        await state.update_data(selected_districts=selected_districts)
        
        # Показываем текущий выбор
        district_names = [DISTRICTS.get(d, f"ID{d}") for d in selected_districts]
        await callback.message.edit_text(
            f"Выбранные районы: {', '.join(district_names) if district_names else 'пока нет'}\n\n"
            f"Продолжайте выбирать или нажмите 'Готово':",
            reply_markup=get_districts_with_done_keyboard(selected_districts)
        )
    
    elif callback.data == "done_districts":
        if not selected_districts:
            await callback.answer("Выберите хотя бы один район!", show_alert=True)
            return
        
        # Сохраняем монтажника в БД
        data = await state.get_data()
        telegram_id = data.get('telegram_id')
        full_name = data.get('full_name')
        phone = data.get('phone')
        
        # Сохраняем в БД
        save_electrician(
            telegram_id=telegram_id,
            full_name=full_name,
            phone=phone,
            districts=selected_districts,
            is_admin=False
        )
        
        await callback.message.edit_text(
            f"✅ Монтажник успешно добавлен!\n\n"
            f"👤 {full_name}\n"
            f"📞 {phone}\n"
            f"🆔 {telegram_id}\n"
            f"📍 Районы: {', '.join([DISTRICTS.get(d) for d in selected_districts])}"
        )
        await state.clear()
        await callback.answer()


# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================

def get_districts_with_done_keyboard(selected):
    """Клавиатура для выбора районов с кнопкой Готово"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    buttons = []
    row = []
    
    for district_id, district_name in DISTRICTS.items():
        # Добавляем отметку, если район выбран
        mark = "✅ " if district_id in selected else ""
        button = InlineKeyboardButton(
            text=f"{mark}{district_name}", 
            callback_data=f"district:{district_id}"
        )
        row.append(button)
        
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="✅ ГОТОВО", callback_data="done_districts")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def save_electrician(telegram_id, full_name, phone, districts, is_admin=False):
    """Сохранение монтажника в БД"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    districts_json = json.dumps(districts)
    
    cursor.execute('''
        INSERT OR REPLACE INTO electricians 
        (telegram_id, full_name, phone, districts, is_active, total_orders_taken, rating, joined_at, is_admin)
        VALUES (?, ?, ?, ?, 1, 0, 0.0, ?, ?)
    ''', (telegram_id, full_name, phone, districts_json, datetime.now(), 1 if is_admin else 0))
    
    conn.commit()
    conn.close()

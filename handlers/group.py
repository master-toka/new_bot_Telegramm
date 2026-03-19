# handlers/group.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
import sqlite3
from datetime import datetime

from database.models import take_order, complete_order, get_order, is_electrician, fetch_one, execute_query
from keyboards.reply import get_taken_order_keyboard, get_rating_keyboard, get_main_keyboard
from config import ADMIN_CHAT_ID, DATABASE_PATH, DISTRICTS
from states.order_states import ElectricianStates

router = Router()

@router.callback_query(lambda c: c.data.startswith('take:'))
async def take_order_callback(callback: CallbackQuery):
    """Монтажник берет заказ"""
    electrician_id = callback.from_user.id
    
    # Проверяем, является ли пользователь монтажником
    if not is_electrician(electrician_id):
        await callback.answer("❌ Вы не авторизованы как монтажник", show_alert=True)
        return
    
    order_id = int(callback.data.split(':')[1])
    
    # Проверяем, не взял ли уже кто-то заказ
    order = get_order(order_id)
    if order and order[9] != 'new':  # status не 'new'
        await callback.answer("❌ Заказ уже кто-то взял", show_alert=True)
        return
    
    # Пытаемся взять заказ
    success = take_order(order_id, electrician_id)
    
    if success:
        # Получаем обновленные данные заказа
        order = get_order(order_id)
        
        # Меняем клавиатуру в группе
        await callback.message.edit_reply_markup(
            reply_markup=get_taken_order_keyboard(order_id, electrician_id)
        )
        
        # Добавляем сообщение, что заказ взят
        await callback.message.reply(
            f"🔨 Заказ #{order[1]} взял {callback.from_user.full_name}"
        )
        
        # Отправляем контакты клиента монтажнику в ЛС
        if order:
            # Индексы после изменения get_order:
            # 0-order_id, 1-order_number, 2-user_id, 3-district_id, 4-description,
            # 5-photo_id, 6-address, 7-8-coords, 9-status, 10-created_at,
            # 11-taken_by, 12-taken_at, 13-completed_at, 14-cancelled_at,
            # 15-cancel_reason, 16-client_rating, 17-client_review,
            # 18-username, 19-first_name, 20-phone
            
            user_id = order[2]
            username = order[18] or "нет_username"
            first_name = order[19] or "Клиент"
            phone = order[20] or "не указан"
            address = order[6]
            description = order[4]
            order_number = order[1]
            
            # Создаем клавиатуру для связи с клиентом
            contact_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✉️ Написать клиенту", url=f"tg://user?id={user_id}")],
                [InlineKeyboardButton(text="📞 Показать телефон", callback_data=f"show_phone:{order_id}")],
                [InlineKeyboardButton(text="🔄 Передать заказ", callback_data=f"transfer_request:{order_id}")]
            ])
            
            await callback.bot.send_message(
                electrician_id,
                f"✅ Вы взяли заказ #{order_number}\n\n"
                f"👤 Клиент: {first_name}\n"
                f"📱 Username: @{username}\n"
                f"📞 Телефон: {phone}\n"
                f"🏠 Адрес: {address}\n"
                f"🔧 Описание: {description}\n\n"
                f"Свяжитесь с клиентом в ближайшее время!",
                reply_markup=contact_keyboard
            )
        
        # Уведомление в админ-чат
        await callback.bot.send_message(
            ADMIN_CHAT_ID,
            f"🔨 Заказ #{order[1]} взят монтажником {callback.from_user.full_name}"
        )
        
        await callback.answer("✅ Заказ взят!")
    else:
        await callback.answer("❌ Ошибка при взятии заказа", show_alert=True)

@router.callback_query(lambda c: c.data.startswith('show_phone:'))
async def show_phone_callback(callback: CallbackQuery):
    """Показать телефон клиента (только для монтажника, взявшего заказ)"""
    order_id = int(callback.data.split(':')[1])
    electrician_id = callback.from_user.id
    
    order = get_order(order_id)
    
    if order and order[11] == electrician_id:  # taken_by совпадает
        phone = order[20] or "не указан"
        await callback.answer(f"📞 Телефон клиента: {phone}", show_alert=True)
    else:
        await callback.answer("❌ Доступ запрещен", show_alert=True)

# ================ ФУНКЦИЯ ПЕРЕДАЧИ ЗАЯВКИ ================

@router.callback_query(lambda c: c.data.startswith('transfer_request:'))
async def transfer_request_callback(callback: CallbackQuery, state: FSMContext):
    """Запрос на передачу заказа другому монтажнику"""
    order_id = int(callback.data.split(':')[1])
    electrician_id = callback.from_user.id
    
    order = get_order(order_id)
    
    # Проверяем, что это тот монтажник, который взял заказ
    if not order or order[11] != electrician_id:
        await callback.answer("❌ Вы не можете передать этот заказ", show_alert=True)
        return
    
    # Проверяем статус заказа
    if order[9] != 'in_progress':
        await callback.answer("❌ Заказ нельзя передать (не в работе)", show_alert=True)
        return
    
    await state.update_data(transfer_order_id=order_id)
    
    await callback.message.edit_text(
        f"🔄 Передача заказа #{order[1]}\n\n"
        f"Укажите причину передачи заказа другому монтажнику:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚗 Далеко ехать", callback_data="transfer_reason:far")],
            [InlineKeyboardButton(text="🔧 Сложная работа", callback_data="transfer_reason:complex")],
            [InlineKeyboardButton(text="⏰ Нет времени", callback_data="transfer_reason:busy")],
            [InlineKeyboardButton(text="💊 Плохое самочувствие", callback_data="transfer_reason:sick")],
            [InlineKeyboardButton(text="✏️ Другая причина", callback_data="transfer_reason:other")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="transfer_cancel")]
        ])
    )
    await state.set_state(ElectricianStates.waiting_for_transfer_reason)
    await callback.answer()

@router.callback_query(
    lambda c: c.data.startswith('transfer_reason:'), 
    StateFilter(ElectricianStates.waiting_for_transfer_reason)
)
async def transfer_reason_callback(callback: CallbackQuery, state: FSMContext):
    """Выбор причины передачи"""
    reason_code = callback.data.split(':')[1]
    
    reasons = {
        'far': '🚗 Далеко ехать',
        'complex': '🔧 Сложная работа',
        'busy': '⏰ Нет времени',
        'sick': '💊 Плохое самочувствие',
        'other': '✏️ Другая причина'
    }
    
    reason_text = reasons.get(reason_code, 'Не указана')
    await state.update_data(transfer_reason=reason_text)
    
    data = await state.get_data()
    order_id = data.get('transfer_order_id')
    order = get_order(order_id)
    
    if reason_code == 'other':
        await callback.message.edit_text(
            f"🔄 Передача заказа #{order[1]}\n\n"
            f"Напишите причину передачи:"
        )
        await state.set_state(ElectricianStates.waiting_for_transfer_reason_text)
    else:
        # Сразу показываем список доступных монтажников
        await show_available_electricians(callback, state, order_id, reason_text)
    
    await callback.answer()

@router.message(StateFilter(ElectricianStates.waiting_for_transfer_reason_text))
async def transfer_reason_text_handler(message: Message, state: FSMContext):
    """Обработка текстовой причины передачи"""
    reason_text = message.text.strip()
    await state.update_data(transfer_reason=reason_text)
    
    data = await state.get_data()
    order_id = data.get('transfer_order_id')
    
    await show_available_electricians(message, state, order_id, reason_text)

async def show_available_electricians(event, state: FSMContext, order_id, reason_text):
    """Показать список доступных монтажников для передачи"""
    order = get_order(order_id)
    
    # Получаем список активных монтажников (кроме текущего)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT telegram_id, full_name 
        FROM electricians 
        WHERE is_active = 1 AND telegram_id != ?
        ORDER BY total_orders_taken DESC
    ''', (order[11],))  # текущий монтажник
    
    electricians = cursor.fetchall()
    conn.close()
    
    if not electricians:
        # Нет доступных монтажников
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Вернуть в группу", callback_data=f"return_to_group:{order_id}")]
        ])
        
        if hasattr(event, 'message'):
            await event.message.edit_text(
                f"❌ Нет доступных монтажников для передачи заказа #{order[1]}.\n\n"
                f"Заказ остаётся за вами.",
                reply_markup=keyboard
            )
        else:
            await event.answer(
                f"❌ Нет доступных монтажников для передачи заказа #{order[1]}.\n\n"
                f"Заказ остаётся за вами.",
                reply_markup=keyboard
            )
        await state.clear()
        return
    
    # Создаем клавиатуру со списком монтажников
    buttons = []
    for e_id, e_name in electricians:
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {e_name}", 
                callback_data=f"transfer_to:{order_id}:{e_id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="transfer_cancel")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if hasattr(event, 'message'):
        await event.message.edit_text(
            f"🔄 Передача заказа #{order[1]}\n"
            f"Причина: {reason_text}\n\n"
            f"Выберите монтажника для передачи:",
            reply_markup=keyboard
        )
    else:
        await event.answer(
            f"🔄 Передача заказа #{order[1]}\n"
            f"Причина: {reason_text}\n\n"
            f"Выберите монтажника для передачи:",
            reply_markup=keyboard
        )
    await state.set_state(ElectricianStates.waiting_for_order_complete_confirm)

@router.callback_query(lambda c: c.data.startswith('transfer_to:'))
async def transfer_to_electrician_callback(callback: CallbackQuery, state: FSMContext):
    """Передача заказа выбранному монтажнику"""
    parts = callback.data.split(':')
    order_id = int(parts[1])
    new_electrician_id = int(parts[2])
    old_electrician_id = callback.from_user.id
    
    order = get_order(order_id)
    
    if not order or order[11] != old_electrician_id:
        await callback.answer("❌ Ошибка передачи", show_alert=True)
        return
    
    # Получаем данные для уведомлений
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Получаем имя нового монтажника
    cursor.execute("SELECT full_name FROM electricians WHERE telegram_id = ?", (new_electrician_id,))
    new_electrician = cursor.fetchone()
    new_electrician_name = new_electrician[0] if new_electrician else "Монтажник"
    
    # Обновляем заказ - меняем монтажника
    cursor.execute('''
        UPDATE orders 
        SET taken_by = ?, taken_at = ?
        WHERE order_id = ?
    ''', (new_electrician_id, datetime.now(), order_id))
    
    # Запись в историю
    cursor.execute('''
        INSERT INTO order_history (order_id, old_status, new_status, changed_by, changed_at, comment)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (order_id, 'in_progress', 'transferred', old_electrician_id, datetime.now(), f"Передан монтажнику {new_electrician_id}"))
    
    conn.commit()
    conn.close()
    
    # Уведомление в группу
    await callback.bot.send_message(
        ADMIN_CHAT_ID,  # или GROUP_ID
        f"🔄 Заказ #{order[1]} передан\n"
        f"От: {callback.from_user.full_name}\n"
        f"Кому: {new_electrician_name}"
    )
    
    # Уведомление новому монтажнику в ЛС
    # Получаем данные клиента
    user_id = order[2]
    username = order[18] or "нет_username"
    first_name = order[19] or "Клиент"
    phone = order[20] or "не указан"
    address = order[6]
    description = order[4]
    
    contact_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Написать клиенту", url=f"tg://user?id={user_id}")],
        [InlineKeyboardButton(text="📞 Показать телефон", callback_data=f"show_phone:{order_id}")],
        [InlineKeyboardButton(text="🔄 Передать заказ", callback_data=f"transfer_request:{order_id}")]
    ])
    
    await callback.bot.send_message(
        new_electrician_id,
        f"🔄 Вам передан заказ #{order[1]}\n\n"
        f"👤 Клиент: {first_name}\n"
        f"📱 Username: @{username}\n"
        f"📞 Телефон: {phone}\n"
        f"🏠 Адрес: {address}\n"
        f"🔧 Описание: {description}\n\n"
        f"Свяжитесь с клиентом в ближайшее время!",
        reply_markup=contact_keyboard
    )
    
    # Уведомление старому монтажнику
    await callback.bot.send_message(
        old_electrician_id,
        f"✅ Заказ #{order[1]} успешно передан монтажнику {new_electrician_name}"
    )
    
    await callback.message.edit_text(
        f"✅ Заказ #{order[1]} передан монтажнику {new_electrician_name}"
    )
    
    await state.clear()
    await callback.answer("✅ Заказ передан!")

@router.callback_query(lambda c: c.data.startswith('return_to_group:'))
async def return_to_group_callback(callback: CallbackQuery, state: FSMContext):
    """Вернуть заказ в группу (сделать снова доступным)"""
    order_id = int(callback.data.split(':')[1])
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Возвращаем статус на 'new' и очищаем taken_by
    cursor.execute('''
        UPDATE orders 
        SET status = 'new', taken_by = NULL, taken_at = NULL
        WHERE order_id = ?
    ''', (order_id,))
    
    cursor.execute('''
        INSERT INTO order_history (order_id, old_status, new_status, changed_by, changed_at, comment)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (order_id, 'in_progress', 'returned_to_pool', callback.from_user.id, datetime.now(), "Возвращен в общий пул"))
    
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        f"✅ Заказ #{order_id} возвращен в общий список. Теперь его могут взять другие монтажники."
    )
    
    await state.clear()
    await callback.answer()

@router.callback_query(lambda c: c.data == "transfer_cancel")
async def transfer_cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена передачи заказа"""
    await callback.message.edit_text(
        "❌ Передача заказа отменена."
    )
    await state.clear()
    await callback.answer()

# ================ ЗАВЕРШЕНИЕ ЗАКАЗА ================

@router.callback_query(lambda c: c.data.startswith('complete:'))
async def complete_order_callback(callback: CallbackQuery):
    """Завершение заказа"""
    electrician_id = callback.from_user.id
    
    if not is_electrician(electrician_id):
        await callback.answer("❌ Вы не авторизованы", show_alert=True)
        return
    
    order_id = int(callback.data.split(':')[1])
    
    success = complete_order(order_id, electrician_id)
    
    if success:
        order = get_order(order_id)
        
        await callback.message.edit_text(
            f"✅ Заказ #{order[1]} выполнен!\n"
            f"Мастер: {callback.from_user.full_name}"
        )
        
        # Уведомление клиенту
        await callback.bot.send_message(
            order[2],  # user_id
            f"✅ Ваш заказ #{order[1]} выполнен!\n"
            f"Спасибо, что обратились к нам!\n\n"
            f"Оцените работу мастера:",
            reply_markup=get_rating_keyboard(order_id)
        )
        
        # Уведомление в админ-чат
        await callback.bot.send_message(
            ADMIN_CHAT_ID,
            f"✅ Заказ #{order[1]} выполнен монтажником {callback.from_user.full_name}"
        )
        
        await callback.answer("✅ Заказ завершен!")
    else:
        await callback.answer("❌ Ошибка при завершении заказа", show_alert=True)

@router.callback_query(lambda c: c.data.startswith('call:'))
async def call_client_callback(callback: CallbackQuery):
    """Позвонить клиенту (старая функция, оставлена для совместимости)"""
    order_id = int(callback.data.split(':')[1])
    order = get_order(order_id)
    
    if order:
        await callback.answer(
            f"Телефон: {order[20] or 'не указан'}, Username: @{order[18]}",
            show_alert=True
        )

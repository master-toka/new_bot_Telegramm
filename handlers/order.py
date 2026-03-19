# handlers/order.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from datetime import datetime
import sqlite3

from states.order_states import OrderStates
from database.models import create_order, get_user, get_order, cancel_order
from keyboards.reply import (
    get_main_keyboard, get_districts_keyboard, 
    get_location_keyboard, get_confirmation_keyboard,
    get_cancel_keyboard, get_rating_keyboard
)
from utils.helpers import format_order_for_group
from config import GROUP_ID, DISTRICTS, DATABASE_PATH, ADMIN_CHAT_ID

router = Router()

@router.message(F.text == "🔧 Новая заявка")
async def new_order_start(message: Message, state: FSMContext):
    """Начало создания новой заявки"""
    user_id = message.from_user.id
    
    # Проверяем регистрацию
    user = get_user(user_id)
    if not user:
        await message.answer(
            "Сначала нужно зарегистрироваться. Нажмите /start"
        )
        return
    
    await state.set_state(OrderStates.waiting_for_district)
    await message.answer(
        "Выберите район, где требуется помощь:",
        reply_markup=get_districts_keyboard()
    )

@router.callback_query(
    lambda c: c.data.startswith('district:'), 
    StateFilter(OrderStates.waiting_for_district)
)
async def process_district(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора района"""
    district_id = int(callback.data.split(':')[1])
    district_name = DISTRICTS.get(district_id, "Неизвестный район")
    
    await state.update_data(district_id=district_id, district_name=district_name)
    await callback.message.delete()
    
    await callback.message.answer(
        f"Район: {district_name}\n\n"
        "Опишите проблему подробно:\n"
        "• Что случилось?\n"
        "• Когда обнаружили?\n"
        "• Есть ли искрение/запах гари?",
        reply_markup=None
    )
    await state.set_state(OrderStates.waiting_for_description)
    await callback.answer()

@router.message(StateFilter(OrderStates.waiting_for_description))
async def process_description(message: Message, state: FSMContext):
    """Обработка описания проблемы"""
    description = message.text.strip()
    
    if len(description) < 10:
        await message.answer(
            "Опишите проблему подробнее (минимум 10 символов), "
            "чтобы мастер понимал, с чем ехать."
        )
        return
    
    await state.update_data(description=description)
    await message.answer(
        "Теперь прикрепите фото проблемы, если есть.\n"
        "Это поможет мастеру оценить сложность работ.\n\n"
        "Можно отправить фото сейчас или написать 'Пропустить'.",
        reply_markup=None
    )
    await state.set_state(OrderStates.waiting_for_photo)

@router.message(F.photo, StateFilter(OrderStates.waiting_for_photo))
async def process_photo(message: Message, state: FSMContext):
    """Обработка фото"""
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    
    await message.answer("✅ Фото сохранено!")
    await ask_address(message, state)

@router.message(F.text.lower() == "пропустить", StateFilter(OrderStates.waiting_for_photo))
async def skip_photo(message: Message, state: FSMContext):
    """Пропуск фото"""
    await state.update_data(photo_id=None)
    await ask_address(message, state)

async def ask_address(message: Message, state: FSMContext):
    """Запрос адреса"""
    await message.answer(
        "Укажите адрес, куда нужно приехать:\n"
        "• Можно отправить геолокацию (кнопка ниже)\n"
        "• Или ввести адрес вручную",
        reply_markup=get_location_keyboard()
    )
    await state.set_state(OrderStates.waiting_for_location)

@router.message(F.location, StateFilter(OrderStates.waiting_for_location))
async def process_location(message: Message, state: FSMContext):
    """Обработка геолокации"""
    lat = message.location.latitude
    lon = message.location.longitude
    
    await state.update_data(lat=lat, lon=lon, address="📍 Геолокация отправлена")
    
    await confirm_order(message, state)

@router.message(F.text, StateFilter(OrderStates.waiting_for_location))
async def process_manual_address(message: Message, state: FSMContext):
    """Обработка ручного ввода адреса"""
    address = message.text.strip()
    
    if len(address) < 5:
        await message.answer("Введите корректный адрес (минимум 5 символов)")
        return
    
    await state.update_data(address=address, lat=None, lon=None)
    await confirm_order(message, state)

async def confirm_order(message: Message, state: FSMContext):
    """Подтверждение заявки перед сохранением"""
    data = await state.get_data()
    
    district_name = data.get('district_name', 'Неизвестно')
    description = data.get('description', '')
    address = data.get('address', 'Не указан')
    has_photo = "Да" if data.get('photo_id') else "Нет"
    
    preview = f"""
📋 ПРОВЕРЬТЕ ДАННЫЕ ЗАЯВКИ:

📍 Район: {district_name}
🔧 Описание: {description}
🏠 Адрес: {address}
📸 Фото: {has_photo}

Всё верно?
    """
    
    # Создаем заявку в БД
    user_id = message.from_user.id
    district_id = data.get('district_id')
    description = data.get('description')
    address = data.get('address')
    photo_id = data.get('photo_id')
    lat = data.get('lat')
    lon = data.get('lon')
    
    order_id, order_number = create_order(
        user_id=user_id,
        district_id=district_id,
        description=description,
        address=address,
        photo_id=photo_id,
        lat=lat,
        lon=lon
    )
    
    # Сохраняем ID заказа в state
    await state.update_data(order_id=order_id, order_number=order_number)
    
    await message.answer(
        preview,
        reply_markup=get_confirmation_keyboard(order_id),
        parse_mode="HTML"
    )
    await state.set_state(OrderStates.waiting_for_confirmation)

@router.callback_query(
    lambda c: c.data.startswith('confirm:'), 
    StateFilter(OrderStates.waiting_for_confirmation)
)
async def confirm_order_callback(callback: CallbackQuery, state: FSMContext):
    """Подтверждение заявки"""
    data = await state.get_data()
    order_id = data.get('order_id')
    order_number = data.get('order_number')
    
    await callback.message.edit_text(
        f"✅ Заявка #{order_number} создана и отправлена мастерам!\n"
        "Ожидайте, скоро с вами свяжутся."
    )
    
    # Отправляем заявку в группу монтажников
    user_id = callback.from_user.id
    district_id = data.get('district_id')
    description = data.get('description')
    address = data.get('address')
    photo_id = data.get('photo_id')
    
    # Получаем данные пользователя
    user = get_user(user_id)
    customer_name = user[2] if user else "Клиент"  # first_name
    
    order_text = format_order_for_group(
        order_id=order_id,
        order_number=order_number,
        customer_name=customer_name,
        district_id=district_id,
        description=description,
        address=address,
        has_photo=bool(photo_id)
    )
    
    from keyboards.reply import get_group_order_keyboard
    
    if photo_id:
        await callback.bot.send_photo(
            chat_id=GROUP_ID,
            photo=photo_id,
            caption=order_text,
            reply_markup=get_group_order_keyboard(order_id)
        )
    else:
        await callback.bot.send_message(
            chat_id=GROUP_ID,
            text=order_text,
            reply_markup=get_group_order_keyboard(order_id)
        )
    
    await state.clear()
    await callback.answer()

@router.callback_query(
    lambda c: c.data.startswith('edit:'), 
    StateFilter(OrderStates.waiting_for_confirmation)
)
async def edit_order_callback(callback: CallbackQuery, state: FSMContext):
    """Редактирование заявки"""
    await callback.message.edit_text(
        "Давайте начнем заново. Выберите район:",
        reply_markup=get_districts_keyboard()
    )
    await state.set_state(OrderStates.waiting_for_district)
    await callback.answer()

@router.callback_query(
    lambda c: c.data.startswith('abort:'), 
    StateFilter(OrderStates.waiting_for_confirmation)
)
async def abort_order_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена создания заявки"""
    await callback.message.edit_text(
        "❌ Создание заявки отменено.",
        reply_markup=get_main_keyboard()
    )
    await state.clear()
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith('cancel_order:'))
async def cancel_order_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена заказа клиентом"""
    order_id = int(callback.data.split(':')[1])
    user_id = callback.from_user.id
    
    order = get_order(order_id)
    
    if not order or order[2] != user_id:  # user_id в заказе
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    if order[9] == 'completed':  # status
        await callback.answer("Заказ уже выполнен, отмена невозможна", show_alert=True)
        return
    
    if order[9] == 'in_progress':
        await callback.message.edit_text(
            "⚠️ Мастер уже выехал. Точно отменить заказ?",
            reply_markup=get_cancel_keyboard(order_id)
        )
        await state.set_state(OrderStates.waiting_for_cancel_confirmation)
        await state.update_data(cancel_order_id=order_id)
    else:
        # Простая отмена нового заказа
        cancel_order(order_id, user_id)
        await callback.message.edit_text(
            "✅ Заказ отменен"
        )
        
        # Уведомление в группу
        await callback.bot.send_message(
            GROUP_ID,
            f"❌ Заказ #{order[1]} отменен клиентом"
        )
    
    await callback.answer()

@router.callback_query(
    lambda c: c.data.startswith('confirm_cancel:'), 
    StateFilter(OrderStates.waiting_for_cancel_confirmation)
)
async def confirm_cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Подтверждение отмены заказа"""
    data = await state.get_data()
    order_id = data.get('cancel_order_id')
    user_id = callback.from_user.id
    
    if order_id:
        cancel_order(order_id, user_id, reason='client_cancelled_confirmed')
        await callback.message.edit_text(
            "✅ Заказ отменен"
        )
        
        # Уведомление в группу
        order = get_order(order_id)
        if order:
            await callback.bot.send_message(
                GROUP_ID,
                f"❌ Заказ #{order[1]} отменен клиентом (мастер уже выехал)"
            )
    
    await state.clear()
    await callback.answer()

@router.callback_query(
    lambda c: c.data.startswith('keep_order:'), 
    StateFilter(OrderStates.waiting_for_cancel_confirmation)
)
async def keep_order_callback(callback: CallbackQuery, state: FSMContext):
    """Оставить заказ (не отменять)"""
    await callback.message.edit_text(
        "✅ Заказ остается в работе. Спасибо!"
    )
    await state.clear()
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith('rate:'))
async def rate_order_callback(callback: CallbackQuery, state: FSMContext):
    """Оценка заказа клиентом"""
    parts = callback.data.split(':')
    order_id = int(parts[1])
    rating = int(parts[2])
    user_id = callback.from_user.id
    
    from database.models import rate_order
    success = rate_order(order_id, user_id, rating)
    
    if success:
        if rating <= 3:
            await callback.message.edit_text(
                f"✅ Спасибо за оценку {rating}⭐!\n"
                f"Нам очень жаль, что возникли проблемы.\n"
                f"Напишите, пожалуйста, что пошло не так?"
            )
            await state.update_data(rate_order_id=order_id)
            await state.set_state("waiting_for_review")
        else:
            await callback.message.edit_text(
                f"✅ Спасибо за оценку {rating}⭐!\n"
                f"Будем рады видеть вас снова!"
            )
            await state.clear()
    else:
        await callback.answer("❌ Ошибка при сохранении оценки", show_alert=True)
    
    await callback.answer()

@router.message(StateFilter("waiting_for_review"))
async def process_review(message: Message, state: FSMContext):
    """Обработка отзыва при низкой оценке"""
    data = await state.get_data()
    order_id = data.get('rate_order_id')
    review = message.text.strip()
    
    if order_id:
        # Сохраняем отзыв в БД
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE orders SET client_review = ? WHERE order_id = ?",
            (review, order_id)
        )
        conn.commit()
        conn.close()
        
        # Уведомление руководству
        await message.bot.send_message(
            ADMIN_CHAT_ID,
            f"⚠️ НИЗКАЯ ОЦЕНКА заказа #{order_id}\n"
            f"Отзыв клиента: {review}"
        )
    
    await message.answer(
        "Спасибо за обратную связь! Мы обязательно учтем ваше замечание."
    )
    await state.clear()

@router.callback_query(lambda c: c.data == "cancel_order")
async def cancel_general(callback: CallbackQuery, state: FSMContext):
    """Общая отмена (кнопка Отмена)"""
    await callback.message.edit_text(
        "Действие отменено.",
        reply_markup=None
    )
    await state.clear()
    await callback.answer()

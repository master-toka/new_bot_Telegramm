# handlers/order.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from datetime import datetime

from states.order_states import OrderStates
from database.models import create_order, get_user, get_order, cancel_order
from keyboards.reply import (
    get_main_keyboard, get_districts_keyboard, 
    get_location_keyboard, get_confirmation_keyboard
)
from utils.helpers import format_order_for_group
from config import GROUP_ID, DISTRICTS

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

@router.callback_query(lambda c: c.data.startswith('district:'), OrderStates.waiting_for_district)
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

@router.message(OrderStates.waiting_for_description)
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
        "Можно отправить фото сейчас или нажать 'Пропустить'.",
        reply_markup=None
    )
    await state.set_state(OrderStates.waiting_for_photo)

@router.message(F.photo, OrderStates.waiting_for_photo)
async def process_photo(message: Message, state: FSMContext):
    """Обработка фото"""
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    
    await message.answer("✅ Фото сохранено!")
    await ask_address(message, state)

@router.message(F.text == "Пропустить", OrderStates.waiting_for_photo)
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

@router.message(F.location, OrderStates.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    """Обработка геолокации"""
    lat = message.location.latitude
    lon = message.location.longitude
    
    await state.update_data(lat=lat, lon=lon, address="📍 Геолокация отправлена")
    
    # Здесь можно добавить обратное геокодирование через API Яндекса
    # Но пока просто сохраняем координаты
    
    await confirm_order(message, state)

@router.message(F.text, OrderStates.waiting_for_location)
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
    
    # Создаем временную запись в БД или сохраняем данные для подтверждения
    # Пока просто показываем кнопки
    
    await message.answer(
        preview,
        reply_markup=None,
        parse_mode="HTML"
    )
    
    # Здесь нужно создать заявку в БД с временным статусом или хранить данные в state
    # Для простоты создаем сразу
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
        f"✅ Заявка #{order_number} создана и отправлена мастерам!\n"
        "Ожидайте, скоро с вами свяжутся.",
        reply_markup=get_main_keyboard()
    )
    
    # Отправляем заявку в группу монтажников
    from aiogram import Bot
    from keyboards.reply import get_group_order_keyboard
    
    bot = message.bot
    
    # Получаем данные пользователя
    user = get_user(user_id)
    customer_name = user[2] if user else "Клиент"
    
    order_text = format_order_for_group(
        order_id=order_id,
        order_number=order_number,
        customer_name=customer_name,
        district_id=district_id,
        description=description,
        address=address,
        has_photo=bool(photo_id)
    )
    
    if photo_id:
        await bot.send_photo(
            chat_id=GROUP_ID,
            photo=photo_id,
            caption=order_text,
            reply_markup=get_group_order_keyboard(order_id)
        )
    else:
        await bot.send_message(
            chat_id=GROUP_ID,
            text=order_text,
            reply_markup=get_group_order_keyboard(order_id)
        )
    
    await state.clear()

@router.callback_query(lambda c: c.data.startswith('cancel_order:'))
async def cancel_order_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена заказа клиентом"""
    order_id = int(callback.data.split(':')[1])
    user_id = callback.from_user.id
    
    order = get_order(order_id)
    
    if not order or order[3] != user_id:  # user_id в заказе
        await callback.answer("Заказ не найден")
        return
    
    if order[8] == 'completed':  # status
        await callback.answer("Заказ уже выполнен, отмена невозможна")
        return
    
    if order[8] == 'in_progress':
        await callback.message.edit_text(
            "⚠️ Мастер уже выехал. Точно отменить заказ?",
            reply_markup=get_cancel_keyboard(order_id)
        )
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
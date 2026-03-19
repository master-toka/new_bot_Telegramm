# handlers/group.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database.models import take_order, complete_order, get_order, is_electrician
from keyboards.reply import get_taken_order_keyboard, get_rating_keyboard
from config import ADMIN_CHAT_ID

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
    
    # Пытаемся взять заказ
    success = take_order(order_id, electrician_id)
    
    if success:
        # Меняем клавиатуру в группе
        await callback.message.edit_reply_markup(
            reply_markup=get_taken_order_keyboard(order_id, electrician_id)
        )
        
        # Добавляем сообщение, что заказ взят
        await callback.message.reply(
            f"🔨 Заказ взял {callback.from_user.full_name}"
        )
        
        # Отправляем контакты клиента монтажнику в ЛС
        order = get_order(order_id)
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
                [InlineKeyboardButton(text="📞 Показать телефон", callback_data=f"show_phone:{order_id}")]
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
        await callback.answer("❌ Заказ уже кто-то взял", show_alert=True)

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

@router.callback_query(lambda c: c.data.startswith('transfer:'))
async def transfer_order_callback(callback: CallbackQuery):
    """Передача заказа другому монтажнику"""
    electrician_id = callback.from_user.id
    
    if not is_electrician(electrician_id):
        await callback.answer("❌ Вы не авторизованы", show_alert=True)
        return
    
    order_id = int(callback.data.split(':')[1])
    
    # Здесь можно добавить логику передачи заказа
    await callback.answer("🔄 Функция передачи заказа в разработке", show_alert=True)

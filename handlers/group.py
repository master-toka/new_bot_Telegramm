# handlers/group.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.models import take_order, complete_order, get_order, is_electrician
from keyboards.reply import get_taken_order_keyboard
from utils.helpers import format_order_for_admin
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
            await callback.bot.send_message(
                electrician_id,
                f"✅ Вы взяли заказ #{order[1]}\n\n"
                f"👤 Клиент: {order[11]} @{order[10]}\n"  # first_name, username
                f"📞 Телефон: {order[12] or 'не указан'}\n"
                f"🏠 Адрес: {order[6]}\n"
                f"🔧 Описание: {order[4]}\n\n"
                f"Свяжитесь с клиентом в ближайшее время!"
            )
        
        # Уведомление в админ-чат
        await callback.bot.send_message(
            ADMIN_CHAT_ID,
            f"🔨 Заказ #{order[1]} взят монтажником {callback.from_user.full_name}"
        )
        
        await callback.answer("✅ Заказ взят!")
    else:
        await callback.answer("❌ Заказ уже кто-то взял", show_alert=True)

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
            order[3],  # user_id
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
    """Позвонить клиенту (показывает контакты)"""
    order_id = int(callback.data.split(':')[1])
    order = get_order(order_id)
    
    if order:
        await callback.answer(
            f"Телефон: {order[12] or 'не указан'}, Username: @{order[10]}",
            show_alert=True
        )

@router.callback_query(lambda c: c.data.startswith('rate:'))
async def rate_order_callback(callback: CallbackQuery):
    """Оценка заказа клиентом"""
    parts = callback.data.split(':')
    order_id = int(parts[1])
    rating = int(parts[2])
    user_id = callback.from_user.id
    
    from database.models import rate_order
    success = rate_order(order_id, user_id, rating)
    
    if success:
        await callback.message.edit_text(
            f"✅ Спасибо за оценку {rating}⭐!\n"
            f"Будем рады видеть вас снова!"
        )
        
        if rating <= 3:
            # Запрашиваем отзыв
            await callback.message.answer(
                "Нам очень жаль, что возникли проблемы.\n"
                "Напишите, пожалуйста, что пошло не так?"
            )
            # Здесь можно сохранить отзыв позже
    else:
        await callback.answer("❌ Ошибка при сохранении оценки")
    
    await callback.answer()
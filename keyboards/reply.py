# keyboards/reply.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import DISTRICTS

def get_main_keyboard():
    """Главное меню"""
    keyboard = [
        [KeyboardButton(text="🔧 Новая заявка")],
        [KeyboardButton(text="📋 Мои заявки")],
        [KeyboardButton(text="📞 Срочная помощь")],
        [KeyboardButton(text="ℹ Помощь")],
        [KeyboardButton(text="📍 Районы")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_phone_keyboard():
    """Запрос номера телефона"""
    keyboard = [
        [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)],
        [KeyboardButton(text="🔙 Пропустить")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_districts_keyboard():
    """Клавиатура с районами"""
    buttons = []
    row = []
    
    for district_id, district_name in DISTRICTS.items():
        button = InlineKeyboardButton(
            text=district_name, 
            callback_data=f"district:{district_id}"
        )
        row.append(button)
        
        # По 2 кнопки в ряд
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_order")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirmation_keyboard(order_id):
    """Клавиатура подтверждения заявки"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm:{order_id}"),
            InlineKeyboardButton(text="✏ Редактировать", callback_data=f"edit:{order_id}")
        ],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"abort:{order_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_location_keyboard():
    """Клавиатура для отправки геолокации"""
    keyboard = [
        [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
        [KeyboardButton(text="📝 Ввести адрес вручную")],
        [KeyboardButton(text="🔙 Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_cancel_keyboard(order_id):
    """Клавиатура для отмены заказа"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да, отменить", callback_data=f"confirm_cancel:{order_id}"),
            InlineKeyboardButton(text="❌ Нет, оставить", callback_data=f"keep_order:{order_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_group_order_keyboard(order_id):
    """Клавиатура для заявки в группе монтажников"""
    buttons = [
        [InlineKeyboardButton(text="✅ Взять заказ", callback_data=f"take:{order_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_taken_order_keyboard(order_id, electrician_id):
    """Клавиатура для взятого заказа (для монтажника)"""
    buttons = [
        [InlineKeyboardButton(text="📞 Позвонить клиенту", callback_data=f"call:{order_id}")],
        [InlineKeyboardButton(text="✅ Завершить", callback_data=f"complete:{order_id}")],
        [InlineKeyboardButton(text="🔄 Передать другому", callback_data=f"transfer:{order_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_rating_keyboard(order_id):
    """Клавиатура для оценки заказа"""
    buttons = []
    row = []
    
    for i in range(1, 6):
        button = InlineKeyboardButton(text=f"{i}⭐", callback_data=f"rate:{order_id}:{i}")
        row.append(button)
        
        if len(row) == 5:
            buttons.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
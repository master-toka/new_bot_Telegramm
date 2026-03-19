# utils/helpers.py
from datetime import datetime
from config import DISTRICTS, COMPANY_NAME, DISPATCHER_PHONE

def format_phone(phone):
    """Форматирование номера телефона"""
    # Убираем все кроме цифр
    digits = ''.join(filter(str.isdigit, phone))
    
    if len(digits) == 11:
        return f"8({digits[1:4]}){digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    return phone

def get_district_name(district_id):
    """Получение названия района по ID"""
    return DISTRICTS.get(district_id, "Неизвестный район")

def format_order_for_group(order_id, order_number, customer_name, district_id, 
                          description, address, has_photo):
    """Форматирование заявки для отправки в группу"""
    district_name = get_district_name(district_id)
    photo_text = "📸 Фото: есть" if has_photo else "📸 Фото: нет"
    
    return f"""
⚡ НОВАЯ ЗАЯВКА #{order_number}

👤 Клиент: {customer_name}
📍 Район: {district_name}
🏠 Адрес: {address}
🔧 Описание: {description}
📅 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}
{photo_text}
    """

def format_order_for_admin(order_id, order_number, customer_name, username, 
                          phone, district_id, address, description, has_photo, status):
    """Форматирование заявки для чата руководства"""
    district_name = get_district_name(district_id)
    phone_str = format_phone(phone) if phone else "не указан"
    photo_str = "есть" if has_photo else "нет"
    
    status_translate = {
        'new': 'Новая',
        'in_progress': 'В работе',
        'completed': 'Выполнена',
        'cancelled': 'Отменена'
    }
    
    return f"""
📊 ДЕТАЛИ ЗАЯВКИ #{order_number}

👤 Клиент: {customer_name}
📞 Username: @{username}
📞 Телефон: {phone_str}
📍 Район: {district_name}
🏠 Адрес: {address}
🔧 Описание: {description}
🖼 Фото: {photo_str}
⏰ Создана: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Статус: {status_translate.get(status, status)}
    """

def get_welcome_text(name):
    """Текст приветствия"""
    return f"""
⚡ {COMPANY_NAME} ⚡

Здравствуйте, {name}!
Быстрое решение проблем с электричеством:
• Круглосуточно
• Выезд по городу и районам
• Опытные мастера

Выберите действие в меню ниже
    """

def get_help_text():
    """Текст помощи"""
    return f"""
📞 СРОЧНАЯ СВЯЗЬ:
Телефон: {DISPATCHER_PHONE}
(круглосуточно)

🕐 Режим работы: 24/7

Если проблема требует срочного вмешательства
(искрит, дымит, нет света во всем доме) -
СРАЗУ ЗВОНИТЕ ПО ТЕЛЕФОНУ!
    """

def get_districts_text():
    """Текст со списком районов"""
    districts_list = "\n".join([f"• {name}" for name in DISTRICTS.values()])
    return f"""
📍 Мы работаем в следующих районах:

{districts_list}

Если вашего района нет в списке, выберите "Другой" и укажите населенный пункт в адресе.
    """
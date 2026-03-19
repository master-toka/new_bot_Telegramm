# handlers/start.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from database.models import add_user, get_user, is_electrician, is_admin
from keyboards.reply import get_main_keyboard, get_phone_keyboard
from utils.helpers import get_welcome_text, get_help_text, get_districts_text
from config import DISPATCHER_PHONE

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or "no_username"
    first_name = message.from_user.first_name or "Пользователь"
    
    # Очищаем предыдущие состояния
    await state.clear()
    
    # Проверяем, зарегистрирован ли пользователь
    user = get_user(user_id)
    
    if not user:
        # Новый пользователь - запрашиваем регистрацию
        await message.answer(
            f"👋 Здравствуйте! Я бот компании {COMPANY_NAME}\n\n"
            "Для начала работы давайте познакомимся. Как я могу к Вам обращаться?",
            reply_markup=None
        )
        await state.set_state("waiting_for_name")
    else:
        # Уже зарегистрирован
        welcome_text = get_welcome_text(user[3])  # first_name
        await message.answer(
            welcome_text,
            reply_markup=get_main_keyboard()
        )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда помощи"""
    await message.answer(
        get_help_text(),
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "ℹ Помощь")
async def help_button(message: Message):
    """Кнопка помощи"""
    await message.answer(
        get_help_text(),
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "📍 Районы")
async def districts_button(message: Message):
    """Кнопка с районами"""
    await message.answer(
        get_districts_text(),
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "📞 Срочная помощь")
async def urgent_button(message: Message):
    """Кнопка срочной помощи"""
    await message.answer(
        f"🚨 СРОЧНАЯ ПОМОЩЬ!\n\n"
        f"Немедленно звоните диспетчеру:\n"
        f"📞 {DISPATCHER_PHONE}\n\n"
        f"Если ситуация критическая (искрит, дымит, нет света) - не ждите ответа бота, звоните сразу!",
        reply_markup=get_main_keyboard()
    )

@router.message(state="waiting_for_name")
async def process_name(message: Message, state: FSMContext):
    """Получение имени при регистрации"""
    name = message.text.strip()
    
    if len(name) > 50:
        await message.answer("Слишком длинное имя. Пожалуйста, введите покороче.")
        return
    
    await state.update_data(name=name)
    await message.answer(
        f"Приятно познакомиться, {name}!\n"
        "Отправьте ваш номер телефона для связи (нажмите кнопку ниже).",
        reply_markup=get_phone_keyboard()
    )
    await state.set_state("waiting_for_phone")

@router.message(F.contact, state="waiting_for_phone")
async def process_phone_contact(message: Message, state: FSMContext):
    """Получение номера телефона через контакт"""
    phone = message.contact.phone_number
    user_id = message.from_user.id
    username = message.from_user.username or "no_username"
    
    data = await state.get_data()
    name = data.get('name', message.from_user.first_name)
    
    # Сохраняем пользователя в БД
    add_user(user_id, username, name, phone)
    
    await state.clear()
    
    await message.answer(
        f"✅ Регистрация завершена!\n\n"
        f"{get_welcome_text(name)}",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "🔙 Пропустить", state="waiting_for_phone")
async def process_phone_skip(message: Message, state: FSMContext):
    """Пропуск ввода телефона"""
    user_id = message.from_user.id
    username = message.from_user.username or "no_username"
    
    data = await state.get_data()
    name = data.get('name', message.from_user.first_name)
    
    # Сохраняем пользователя в БД без телефона
    add_user(user_id, username, name)
    
    await state.clear()
    
    await message.answer(
        f"✅ Регистрация завершена!\n\n"
        f"{get_welcome_text(name)}\n\n"
        f"⚠️ Вы не указали телефон, но мастер сможет связаться с вами через Telegram.",
        reply_markup=get_main_keyboard()
    )

@router.message(F.text == "📋 Мои заявки")
async def my_orders(message: Message):
    """Просмотр своих заявок"""
    from database.models import get_user_orders
    from config import DISTRICTS
    
    user_id = message.from_user.id
    orders = get_user_orders(user_id)
    
    if not orders:
        await message.answer(
            "У вас пока нет заявок. Нажмите «🔧 Новая заявка» чтобы создать первую!",
            reply_markup=get_main_keyboard()
        )
        return
    
    status_emoji = {
        'new': '🟡',
        'in_progress': '🔵',
        'completed': '✅',
        'cancelled': '❌'
    }
    
    orders_text = "📋 Ваши последние заявки:\n\n"
    for order in orders:
        order_number, status, created_at, district_id = order
        district_name = DISTRICTS.get(district_id, "Неизвестный район")
        date_str = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S.%f').strftime('%d.%m.%Y %H:%M')
        emoji = status_emoji.get(status, '⚪')
        
        orders_text += f"{emoji} Заявка #{order_number}\n"
        orders_text += f"   📍 {district_name}\n"
        orders_text += f"   🕐 {date_str}\n\n"
    
    await message.answer(orders_text, reply_markup=get_main_keyboard())
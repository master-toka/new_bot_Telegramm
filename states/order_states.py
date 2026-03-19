# states/order_states.py
from aiogram.fsm.state import State, StatesGroup

class OrderStates(StatesGroup):
    """
    Состояния для создания и управления заявками
    """
    # Состояния для создания новой заявки
    waiting_for_district = State()              # Ожидание выбора района
    waiting_for_description = State()            # Ожидание описания проблемы
    waiting_for_photo = State()                  # Ожидание загрузки фото
    waiting_for_location = State()                # Ожидание геолокации или адреса
    waiting_for_confirmation = State()            # Ожидание подтверждения заявки
    
    # Состояния для управления существующей заявкой
    waiting_for_cancel_confirmation = State()     # Ожидание подтверждения отмены
    waiting_for_review = State()                   # Ожидание отзыва (при низкой оценке)

# Если нужны отдельные состояния для разных типов действий,
# можно добавить дополнительные классы:

class AdminStates(StatesGroup):
    """Состояния для административных действий"""
    waiting_for_electrician_add = State()         # Добавление нового монтажника
    waiting_for_district_assign = State()         # Назначение районов монтажнику
    waiting_for_manual_order_assign = State()     # Ручное назначение заказа

class ElectricianStates(StatesGroup):
    """Состояния для действий монтажника"""
    waiting_for_order_complete_confirm = State()  # Подтверждение завершения
    waiting_for_transfer_reason = State()         # Причина передачи заказа
    waiting_for_problem_report = State()          # Сообщение о проблеме

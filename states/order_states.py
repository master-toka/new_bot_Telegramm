# states/order_states.py
from aiogram.fsm.state import State, StatesGroup

class OrderStates(StatesGroup):
    """Состояния для создания заявки"""
    waiting_for_district = State()
    waiting_for_description = State()
    waiting_for_photo = State()
    waiting_for_address = State()
    waiting_for_location = State()
    waiting_for_confirmation = State()
    waiting_for_cancel_confirmation = State()
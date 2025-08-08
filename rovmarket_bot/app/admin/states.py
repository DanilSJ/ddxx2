from aiogram.fsm.state import StatesGroup, State


class AdCreationStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_photos = State()
    waiting_for_confirmation = State()
    waiting_for_name = State()
    waiting_for_description = State()

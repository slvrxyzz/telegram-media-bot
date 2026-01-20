from aiogram.fsm.state import State, StatesGroup


class UploadStates(StatesGroup):
    waiting_for_media = State()
    waiting_for_description = State()


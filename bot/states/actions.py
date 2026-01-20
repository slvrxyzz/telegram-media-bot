from aiogram.fsm.state import State, StatesGroup


class ActionStates(StatesGroup):
    waiting_get_id = State()
    waiting_delete_id = State()
    waiting_edit_id = State()
    waiting_edit_text = State()
    waiting_search_text = State()
    waiting_filter_args = State()


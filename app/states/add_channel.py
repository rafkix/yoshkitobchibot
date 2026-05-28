from aiogram.fsm.state import State, StatesGroup


class AddChannelState(StatesGroup):
    waiting_for_source = State()         # telegram channel: id/link/forward
    waiting_for_private_link = State()   # private invite link
    waiting_for_external_link = State()  # external link
    waiting_for_external_title = State() # external link title
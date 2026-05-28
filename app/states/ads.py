from aiogram.fsm.state import StatesGroup, State


class SendAds(StatesGroup):
    send_forward = State()


class SendCopy(StatesGroup):
    send_copy = State()


class AddAd(StatesGroup):
    title = State()
    description = State()
    waiting_for_button_text = State()
    waiting_for_button_url_or_callback = State()
    confirm_buttons = State()

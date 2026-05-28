# app/states/register.py
from aiogram.fsm.state import State, StatesGroup


class RegisterState(StatesGroup):
    full_name = State()
    birth_date = State()
    region = State()
    district = State()
    neighborhood = State()
    neighborhood_manual = State()  # ← YANGI: o‘zi yozish
    workplace = State()
    phone_number = State()
    contest = State()
    direction = State()
    confirm = State()
    edit_field = State()  # ← YANGI: tahrirlash rejimi

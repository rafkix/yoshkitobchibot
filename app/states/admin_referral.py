# app/states/admin_referral.py

from aiogram.fsm.state import State, StatesGroup


class AdminReferralState(StatesGroup):
    waiting_user_id = State()  # Admin user ID kiritishini kutmoqda
    waiting_new_score = State()  # Admin yangi ball kiritishini kutmoqda

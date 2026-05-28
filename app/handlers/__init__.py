from aiogram import Dispatcher

from app.handlers import admins, users, groups, channels


def setup(dp: Dispatcher):
    """
    Botning routerlarini sozlash uchun setup funksiyasi.
    """
    admins.setup(dp)
    users.setup(dp)
    channels.setup(dp)

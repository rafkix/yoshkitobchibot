from aiogram import Dispatcher
from .chatjoin import router as channel


def setup(dp: Dispatcher):
    """
    Botning routerlarini ulash uchun setup funksiyasi.
    """
    dp.include_routers(channel)

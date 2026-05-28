from aiogram import Dispatcher
from .start import router as user_router
from .register import router as register_router
from .help import router as help_router
from .menu import router as menu_router
from .prizes import router as prizes_router

def setup(dp: Dispatcher):
    """
    Botning routerlarini ulash uchun setup funksiyasi.
    """
    dp.include_routers(
        user_router,
        register_router,
        help_router,
        menu_router,
        prizes_router
    )
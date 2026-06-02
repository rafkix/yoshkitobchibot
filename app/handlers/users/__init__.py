from aiogram import Dispatcher
from .start import router as user_router
from .register import router as register_router
from .help import router as help_router
from .profile import router as profile_router
from .rating import router as rating_router
from .referral import router as referral_router
from .prizes import router as prizes_router
from .test import router as test_router


def setup(dp: Dispatcher):
    """
    Botning routerlarini ulash uchun setup funksiyasi.
    """
    dp.include_routers(
        user_router,
        register_router,
        help_router,
        rating_router,
        profile_router,
        referral_router,
        prizes_router,
        test_router,
    )

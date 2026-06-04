from aiogram import Dispatcher
from .main_admin import router as main_admin_router
from .channels.add_channel import router as channels
from .channels.view_channels import router as view_channels_router
from .channels.delete_channel import router as delete_channel_router
from .ads.send_ads import router as admin_ads_router
from .tests.upload_questions import router as upload_questions_router
from .users import router as users_router
from .contest import router as contest_router
from .tests.test_admin import router as test_admin_router
from .referral_admin import router as referral_admin


def setup(dp: Dispatcher):
    dp.include_routers(
        main_admin_router,
        channels,
        view_channels_router,
        delete_channel_router,
        admin_ads_router,
        upload_questions_router,
        users_router,
        contest_router,
        test_admin_router,
        referral_admin,
    )

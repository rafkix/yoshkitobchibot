from aiogram import Dispatcher
from .main_admin import router as main_admin_router
from .channels.add_channel import router as channels
from .channels.view_channels import router as view_channels_router
from .channels.delete_channel import router as delete_channel_router
from .ads.send_ads import router as admin_ads_router
from .ads.ads import router as ads
from .ads.upload_questions import router as upload_questions_router


def setup(dp: Dispatcher):
     """
     Botning routerlarini ulash uchun setup funksiyasi.
     """
     dp.include_routers(
          main_admin_router,
          channels,
          view_channels_router,
          delete_channel_router,
          admin_ads_router,
          ads,
          upload_questions_router,
     )
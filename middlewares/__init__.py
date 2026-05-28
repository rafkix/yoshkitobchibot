from aiogram import Dispatcher
from .throttling import ThrottlingMiddleware
from .checking_middlewares import SubscriptionMiddleware


def setup(dp: Dispatcher):
    # router.message.middleware(ThrottlingMiddleware())
    dp.message.middleware(SubscriptionMiddleware())

from typing import Union
from aiogram import Bot
from aiogram.types import ChatMemberMember, ChatMemberOwner, ChatMemberAdministrator


async def chek(user_id: int, channel: Union[str, int]) -> bool:
    bot = Bot.get_current()
    chat_member = await bot.get_chat_member(chat_id=channel, user_id=user_id)

    # Check if the user is an administrator or the bot itself
    if (
        chat_member.status in ["administrator", "creator"]
        or chat_member.user.id == bot.id
    ):
        return True

    # Foydalanuvchi a‘zo yoki admin/owner bo‘lsa True qaytaradi
    return isinstance(
        chat_member, (ChatMemberMember, ChatMemberAdministrator, ChatMemberOwner)
    )

from aiogram import Router
from aiogram.types import ChatJoinRequest

from database.database import session_maker
from database.services.join_request_service import mark_channel_request_by_chat_id

router = Router()


@router.chat_join_request()
async def handle_join_request(event: ChatJoinRequest):
    user_id = event.from_user.id
    chat_id = event.chat.id
    user_chat_id = event.user_chat_id  # 🔥 MUHIM
    print(user_chat_id, user_id)
    async with session_maker() as session:
        await mark_channel_request_by_chat_id(
            session=session,
            user_id=user_id,
            telegram_chat_id=chat_id,
        )

    print(f"JOIN REQUEST: user={user_id}, chat={chat_id}, user_chat_id={user_chat_id}")

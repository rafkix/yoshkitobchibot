import logging
from typing import Callable, Awaitable, Any, Dict

from aiogram import BaseMiddleware, types
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.config import ADMINS
from database.services.channel_service import get_all_channels
from database.services.join_request_service import (
    get_active_channel_join,
    add_channel_join,
)
from database.database import session_maker


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        user_id = None
        deep_link = None
        bot = None
        is_check_callback = False

        # =========================
        # EVENT PARSING
        # =========================
        if isinstance(event, types.Message):
            if not event.from_user:
                return await handler(event, data)

            user_id = event.from_user.id
            bot = event.bot

            if event.text:
                parts = event.text.strip().split(maxsplit=1)
                if len(parts) > 1:
                    deep_link = parts[1]

        elif isinstance(event, types.CallbackQuery):
            if not event.from_user:
                return await handler(event, data)

            user_id = event.from_user.id
            bot = event.bot

            if event.data and event.data.startswith("check"):
                is_check_callback = True
                deep_link = event.data.split(":", 1)[1] if ":" in event.data else None

        else:
            return await handler(event, data)

        if not user_id or not bot:
            return await handler(event, data)

        # =========================
        # ADMIN SKIP
        # =========================
        if user_id in ADMINS:
            return await handler(event, data)

        # =========================
        # MAIN LOGIC (ONE SESSION)
        # =========================
        async with session_maker() as session:
            try:
                channels = await get_all_channels(session, active_only=True)
            except Exception as e:
                logging.error(f"❗ Kanal olishda xatolik: {e}")
                return await handler(event, data)

            if not channels:
                return await handler(event, data)

            unsubscribed_buttons = []
            is_not_subscribed = False

            for channel in channels:
                try:
                    # =========================
                    # 🔒 PRIVATE CHANNEL
                    # =========================
                    if channel.is_private:
                        join = await get_active_channel_join(
                            session=session,
                            user_id=user_id,
                            channel_id=channel.channel_id,
                        )

                        if join:
                            continue  # ✅ Foydalanuvchi allaqachon qo‘shilgan

                        if channel.channel_link:
                            unsubscribed_buttons.append(
                                InlineKeyboardButton(
                                    text=channel.title or "🔒 Private kanal",
                                    url=channel.channel_link,
                                )
                            )
                            is_not_subscribed = True

                        continue  # ❗ Telegram API ni o‘tkazib yuborish

                    # =========================
                    # 📢 PUBLIC CHANNEL
                    # =========================
                    if channel.link_type == "telegram_channel":
                        if not channel.telegram_chat_id:
                            continue

                        try:
                            member = await bot.get_chat_member(
                                chat_id=channel.telegram_chat_id,
                                user_id=user_id,
                            )
                        except Exception as e:
                            logging.warning(
                                f"get_chat_member xatosi "
                                f"(channel_id={channel.channel_id}): {e}"
                            )
                            continue

                        if member.status in {"member", "administrator", "creator"}:
                            await add_channel_join(
                                session=session,
                                user_id=user_id,
                                channel_id=channel.channel_id,
                            )
                            continue

                        if member.status == "restricted" and getattr(
                            member, "is_member", False
                        ):
                            await add_channel_join(
                                session=session,
                                user_id=user_id,
                                channel_id=channel.channel_id,
                            )
                            continue

                        # Obuna bo‘lmagan — tugma qo‘shamiz
                        if channel.channel_link:
                            unsubscribed_buttons.append(
                                InlineKeyboardButton(
                                    text="Obuna bo‘lish",
                                    url=channel.channel_link,
                                )
                            )
                            is_not_subscribed = True

                        continue

                    # =========================
                    # 🔐 INVITE LINK (so‘rovli)
                    # =========================
                    if channel.link_type == "telegram_invite":
                        join = await get_active_channel_join(
                            session=session,
                            user_id=user_id,
                            channel_id=channel.channel_id,
                        )

                        if join:
                            continue  # ✅ Tasdiqlangan

                        if channel.channel_link:
                            unsubscribed_buttons.append(
                                InlineKeyboardButton(
                                    text="Obuna bo‘lish",
                                    url=channel.channel_link,
                                )
                            )
                            is_not_subscribed = True

                        continue

                    # =========================
                    # 🌐 EXTERNAL LINK
                    # =========================
                    if channel.link_type == "external_link":
                        if not channel.requires_check:
                            continue

                        if channel.channel_link:
                            unsubscribed_buttons.append(
                                InlineKeyboardButton(
                                    text="Obuna bo‘lish",
                                    url=channel.channel_link,
                                )
                            )
                            is_not_subscribed = True

                except Exception as e:
                    logging.warning(
                        f"⚠️ Obuna tekshirishda xatolik "
                        f"(channel_id={channel.channel_id}): {e}"
                    )

        # =========================
        # FOYDALANUVCHINI BLOKLASH
        # =========================
        if is_not_subscribed:
            builder = InlineKeyboardBuilder()

            for btn in unsubscribed_buttons:
                builder.add(btn)

            check_callback = "check"
            if deep_link:
                check_callback += f":{deep_link}"

            builder.add(
                InlineKeyboardButton(
                    text="Tekshirish",
                    callback_data=check_callback,
                )
            )

            builder.adjust(1)

            text = "Avval kanallarga obuna bo‘ling:"

            try:
                if isinstance(event, types.CallbackQuery):
                    await event.answer("🔄 Qayta tekshirildi")

                    if event.message:
                        await event.message.edit_text(
                            text=text,
                            parse_mode="HTML",
                            reply_markup=builder.as_markup(),
                        )
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=builder.as_markup(),
                    )

            except Exception as e:
                logging.error(f"❗ Obuna xabarini yuborishda xatolik: {e}")

            return  # Handler ga o‘tkazmaymiz

        # =========================
        # HANDLER GA o‘TKAZISH
        # =========================
        if is_check_callback:
            data["subscription_passed"] = True
            data["deep_link_after_subscribe"] = deep_link

        return await handler(event, data)

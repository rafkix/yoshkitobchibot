from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def referral_share_keyboard(referral_link: str, share_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Do‘stlarga ulashish",
                    switch_inline_query=referral_link,
                )
            ],
            [InlineKeyboardButton(text="🔗 Oddiy ulashish", url=share_url)],
        ]
    )


def inline_join_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 Loyihaga qo‘shilish",
                    url=referral_link,
                )
            ]
        ]
    )

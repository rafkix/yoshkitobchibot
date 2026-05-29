import asyncio
import random

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func

from database.database import session_maker
from database.models import TestSession, Test, Question
from database.services.test_service import TestService, SECONDS_PER_QUESTION

router = Router()


# =========================================================
# KLAVIATURA — TESTLAR Ro‘YXATI
# =========================================================

EMOJIS = ["📗", "📘", "📙", "📕"]


def tests_list_keyboard(tests: list):
    builder = InlineKeyboardBuilder()
    for t in tests:
        emoji = random.choice(EMOJIS)
        builder.add(
            InlineKeyboardButton(
                text=f"{emoji} {t.title}",
                callback_data=f"pick_test:{t.id}",
            )
        )
    builder.adjust(1)
    return builder.as_markup()


def start_test_keyboard(test_id: int):
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🚀 Boshlash", callback_data=f"start_test:{test_id}")
    )
    builder.add(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_tests"))
    builder.adjust(1)
    return builder.as_markup()


# =========================================================
# KLAVIATURA — A B C D
# =========================================================


def question_keyboard(question_id: int):
    builder = InlineKeyboardBuilder()
    for opt in ["A", "B", "C", "D"]:
        builder.add(
            InlineKeyboardButton(
                text=opt,
                callback_data=f"ans:{question_id}:{opt}",
            )
        )
    builder.adjust(4)
    return builder.as_markup()


# =========================================================
# YORDAMCHI — vaqtni chiroyli ko‘rsatish
# =========================================================


def format_duration(seconds: int) -> str:
    minutes = seconds // 60
    if minutes >= 60:
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours} soat {mins} daqiqa" if mins else f"{hours} soat"
    return f"{minutes} daqiqa"


# =========================================================
# SAVOL YUBORISH
# =========================================================


async def send_question(target, session_obj: TestSession, service: TestService):
    question = await service.get_current_question(session_obj)
    if not question:
        return False

    answered = len(session_obj.answers)
    total = len(session_obj.question_ids)
    remaining = service.remaining_seconds(session_obj)
    minutes, seconds = divmod(remaining, 60)

    text = (
        f"⌛️ <i>Qolgan vaqt: {minutes:02d}:{seconds:02d}</i>\n\n"
        f"❓ Savol <code>{answered + 1}/{total}</code>\n\n"
        f"{question.text}\n\n"
        f"A) {question.option_a}\n"
        f"B) {question.option_b}\n"
        f"C) {question.option_c}\n"
        f"D) {question.option_d}\n\n"
        f"yoshkitobchi.uz"
    )

    kb = question_keyboard(question.id)

    if isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        try:
            await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await target.message.answer(text, parse_mode="HTML", reply_markup=kb)

    return True


# =========================================================
# NATIJA XABARI
# =========================================================


def result_text(result: dict, expired: bool = False) -> str:
    header = (
        "⏰ <b>Vaqt tugadi! Test avtomatik yakunlandi.</b>\n\n"
        if expired
        else "🎉 <b>Test yakunlandi!</b>\n\n"
    )
    return (
        f"{header}"
        f"✅ To‘g‘ri javoblar: <b>{result['correct']}/{result['total']}</b>\n"
        f"📝 Javob berildi: <b>{result['answered']}</b> ta\n"
        f"📊 Rasch ball: <b>{result['score']}</b> / 100\n"
        f"📈 Theta (θ): {result['theta']}\n\n"
        f"🏆 Ball reytingga qo‘shildi!"
    )


# =========================================================
# 📄 Test tugmasi — testlar ro‘yxatini ko‘rsatish
# =========================================================


@router.message(F.text == "📄 Test")
async def test_list_show(message: Message):
    async with session_maker() as session:
        result = await session.execute(
            select(Test).where(Test.is_active.is_(True)).order_by(Test.id)
        )
        tests = result.scalars().all()

    if not tests:
        await message.answer(
            "⚠️ Hozircha hech qanday test mavjud emas. Keyinroq urinib ko‘ring."
        )
        return

    await message.answer(
        "📚 <b>Testlar ro‘yxati</b>\n\nBitta testni tanlang:",
        parse_mode="HTML",
        reply_markup=tests_list_keyboard(tests),
    )


# =========================================================
# TEST TANLASH — ma'lumot + Boshlash tugmasi
# =========================================================


@router.callback_query(F.data.startswith("pick_test:"))
async def pick_test(callback: CallbackQuery):
    test_id = int(callback.data.split(":")[1])

    async with session_maker() as session:
        result = await session.execute(select(Test).where(Test.id == test_id))
        test = result.scalar_one_or_none()

        if not test:
            await callback.answer("Test topilmadi.", show_alert=True)
            return

        q_count = await session.scalar(
            select(func.count(Question.id)).where(
                Question.test_id == test_id,
                Question.is_active.is_(True),
            )
        )

    # Savol soniga qarab vaqtni hisoblash
    actual_count = min(q_count, 40)
    duration_sec = actual_count * SECONDS_PER_QUESTION
    duration_str = format_duration(duration_sec)

    await callback.message.edit_text(
        f"📋 <b>{test.title}</b>\n\n"
        f"📝 Savollar soni: <b>{actual_count} ta</b>\n"
        f"🕐 Vaqt: <b>{duration_str}</b>\n\n"
        f"Testni boshlashga tayyormisiz?",
        parse_mode="HTML",
        reply_markup=start_test_keyboard(test_id),
    )
    await callback.answer()


# =========================================================
# ORQAGA — testlar ro‘yxatiga qaytish
# =========================================================


@router.callback_query(F.data == "back_to_tests")
async def back_to_tests(callback: CallbackQuery):
    async with session_maker() as session:
        result = await session.execute(
            select(Test).where(Test.is_active.is_(True)).order_by(Test.id)
        )
        tests = result.scalars().all()

    await callback.message.edit_text(
        "📚 <b>Testlar ro‘yxati</b>\n\nBitta testni tanlang:",
        parse_mode="HTML",
        reply_markup=tests_list_keyboard(tests),
    )
    await callback.answer()


# =========================================================
# BOSHLASH — sessiya yaratib savollarni yuborish
# =========================================================


@router.callback_query(F.data.startswith("start_test:"))
async def start_test(callback: CallbackQuery):
    test_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    async with session_maker() as session:
        service = TestService(session)
        session_obj, status = await service.get_or_create_session(user_id, test_id)

        if status == "completed":
            await callback.message.edit_text(
                "✅ Siz bu testni allaqachon yakunlagansiz. Natija reytingda hisobga olingan."
            )
            await callback.answer()
            return

        if status == "expired":
            await callback.message.edit_text(
                "⏰ Oldingi sessiyangiz vaqti tugagan edi. Natija hisoblab saqlandi."
            )
            await callback.answer()
            return

        if status == "no_questions":
            await callback.message.edit_text(
                "⚠️ Bu testda hozircha savollar yo‘q. Keyinroq urinib ko‘ring."
            )
            await callback.answer()
            return

        total_q = len(session_obj.question_ids)
        duration_str = format_duration(session_obj.duration_seconds)

        if status == "continued":
            answered = len(session_obj.answers)
            remaining = service.remaining_seconds(session_obj)
            r_min, r_sec = divmod(remaining, 60)
            await callback.message.edit_text(
                f"▶️ <b>Test davom ettirilmoqda.</b>\n\n"
                f"✅ Javob berildi: <b>{answered}/{total_q}</b>\n"
                f"🕐 Qolgan vaqt: <b>{r_min:02d}:{r_sec:02d}</b>",
                parse_mode="HTML",
            )

        if status == "new":
            await callback.message.edit_text(
                f"🚀 <b>Test boshlandi!</b>\n\n"
                f"📋 Jami: <b>{total_q} ta savol</b>\n"
                f"🕐 Vaqt: <b>{duration_str}</b>\n\n"
                f"Har bir savolga A, B, C yoki D tugmasini bosib javob bering.\n"
                f"⚠️ Vaqt tugagach test avtomatik yakunlanadi.",
                parse_mode="HTML",
            )

        await callback.answer()
        await send_question(callback.message, session_obj, service)

        asyncio.create_task(
            auto_finish_timer(user_id, callback.message.chat.id, callback.bot, test_id)
        )


# =========================================================
# AVTOMATIK YAKUNLASH TIMER
# =========================================================


async def auto_finish_timer(user_id: int, chat_id: int, bot, test_id: int):
    async with session_maker() as session:
        result = await session.execute(
            select(TestSession).where(
                TestSession.user_id == user_id,
                TestSession.test_id == test_id,
                TestSession.is_completed.is_(False),
            )
        )
        session_obj = result.scalar_one_or_none()
        if not session_obj:
            return
        wait = session_obj.duration_seconds

    await asyncio.sleep(wait)

    async with session_maker() as session:
        service = TestService(session)
        result = await session.execute(
            select(TestSession).where(
                TestSession.user_id == user_id,
                TestSession.test_id == test_id,
                TestSession.is_completed.is_(False),
            )
        )
        session_obj = result.scalar_one_or_none()
        if not session_obj:
            return

        res = await service.finish_session(session_obj, user_id)
        await bot.send_message(
            chat_id=chat_id,
            text=result_text(res, expired=True),
            parse_mode="HTML",
        )


# =========================================================
# JAVOB HANDLER
# =========================================================


@router.callback_query(F.data.startswith("ans:"))
async def answer_handler(callback: CallbackQuery):
    parts = callback.data.split(":")
    question_id = int(parts[1])
    answer = parts[2]
    user_id = callback.from_user.id

    async with session_maker() as session:
        service = TestService(session)

        result = await session.execute(
            select(TestSession).where(
                TestSession.user_id == user_id,
                TestSession.is_completed.is_(False),
            )
        )
        session_obj = result.scalar_one_or_none()

        if not session_obj:
            await callback.answer(
                "Sessiya topilmadi yoki test tugallangan.", show_alert=True
            )
            return

        if service.is_expired(session_obj):
            res = await service.finish_session(session_obj, user_id)
            await callback.message.edit_text(
                result_text(res, expired=True), parse_mode="HTML"
            )
            await callback.answer()
            return

        if str(question_id) in session_obj.answers:
            await callback.answer(
                "Bu savolga allaqachon javob berdingiz.", show_alert=True
            )
            return

        await service.save_answer(session_obj, question_id, answer)
        await callback.answer(f"✅ {answer} tanlandi")

        answered = len(session_obj.answers)
        total = len(session_obj.question_ids)

        if answered >= total:
            res = await service.finish_session(session_obj, user_id)
            await callback.message.edit_text(result_text(res), parse_mode="HTML")
        else:
            await send_question(callback, session_obj, service)

# app/handlers/users/tests.py

import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func

from app.keyboards.users.tests import (
    question_keyboard,
    start_test_keyboard,
    tests_list_keyboard,
)
from database.database import session_maker
from database.models import TestSession, Test, Question
from database.services.test_service import (
    TestService,
    SECONDS_PER_QUESTION,
    TEST_MAX_QUESTIONS,
)

router = Router()


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
        f"⏳ <b>Qolgan vaqt:</b> {minutes:02d}:{seconds:02d}\n\n"
        f"📖 <b>Savol {answered + 1}/{total}</b>\n\n"
        f"{question.text}\n\n"
        f"A) {question.option_a}\n"
        f"B) {question.option_b}\n"
        f"C) {question.option_c}\n"
        f"D) {question.option_d}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"Yosh Kitobxon Test Platformasi"
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
    title = (
        "⏰ <b>Test vaqti yakunlandi</b>\n\n"
        if expired
        else "📊 <b>Test natijalari</b>\n\n"
    )

    return (
        f"{title}"
        f"✅ To‘g‘ri javoblar: <b>{result['correct']}/{result['total']}</b>\n"
        f"📝 Javob berilgan savollar: <b>{result['answered']}</b>\n"
        f"📈 Rasch ball: <b>{result['score']}</b>/100\n"
        f"📉 Theta (θ): <b>{result['theta']}</b>\n\n"
        f"Natija reyting tizimiga qo‘shildi."
    )


# =========================================================
# 📄 Test tugmasi — testlar ro‘yxatini ko‘rsatish
# =========================================================


@router.message(F.text == "📄 Test" or "/test")
async def test_list_show(message: Message):
    async with session_maker() as session:
        tests = await TestService(session).get_available_tests()

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
        service = TestService(session)
        result = await session.execute(select(Test).where(Test.id == test_id))
        test = result.scalar_one_or_none()

        if not test:
            await callback.answer("Test topilmadi.", show_alert=True)
            return
        if not service.is_available(test):
            await callback.answer("Bu test hozir aktiv emas.", show_alert=True)
            return

        # FIXED: faqat is_active=True savollar sanaladi
        q_count = await session.scalar(
            select(func.count(Question.id)).where(
                Question.test_id == test_id,
                Question.is_active.is_(True),
            )
        )
        max_questions = TEST_MAX_QUESTIONS
        seconds_per_question = SECONDS_PER_QUESTION
        availability_str = service.availability_text(test)

    actual_count = min(q_count or 0, max_questions)
    duration_sec = actual_count * seconds_per_question
    duration_str = format_duration(duration_sec)

    await callback.message.edit_text(
        f"📋 <b>{test.title}</b>\n\n"
        f"📝 Savollar soni: <b>{actual_count} ta</b>\n"
        f"🕐 Vaqt: <b>{duration_str}</b>\n\n"
        f"🗓 Ochilish vaqti: <b>{availability_str}</b>\n\n"
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
        tests = await TestService(session).get_available_tests()

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

        if status == "not_available":
            await callback.message.edit_text(
                "⚠️ Bu test hozir aktiv emas yoki vaqti tugagan."
            )
            await callback.answer()
            return

        if status == "error":
            await callback.message.edit_text(
                "❌ Xatolik yuz berdi. Keyinroq urinib ko‘ring."
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
                f"📋 <b>Test davom ettirilmoqda</b>\n\n"
                f"Javob berilgan: <b>{answered}/{total_q}</b>\n"
                f"Qolgan vaqt: <b>{r_min:02d}:{r_sec:02d}</b>",
                parse_mode="HTML",
            )

        if status == "new":
            await callback.message.edit_text(
                f"📋 <b>Test boshlandi</b>\n\n"
                f"• Savollar soni: <b>{total_q}</b>\n"
                f"• Ajratilgan vaqt: <b>{duration_str}</b>\n\n"
                f"Har bir savol uchun mos javob variantini tanlang.\n"
                f"Vaqt tugaganda test avtomatik ravishda yakunlanadi.",
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
        wait = service.remaining_seconds(session_obj)

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

        # FIXED: test_id bo‘yicha ham filtrlanadi
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

        # Savol bu sessiyaga tegishli ekanligini tekshirish
        if question_id not in session_obj.question_ids:
            await callback.answer(
                "Bu savol sizning testingizga tegishli emas.", show_alert=True
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

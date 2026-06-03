# database/services/test_service.py

import random
import logging
from datetime import datetime, UTC, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Question, Test, TestSession
from app.utils.rasch import rasch_ability, theta_to_score

logger = logging.getLogger(__name__)

# Hardcoded defaults - test parametrlari
TEST_MAX_QUESTIONS = 40
TEST_SECONDS_PER_QUESTION = 90

# FIX: handler fayli shu nomdan import qiladi
SECONDS_PER_QUESTION = TEST_SECONDS_PER_QUESTION


class TestService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    def _as_utc(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    def availability_status(self, test: Test) -> str:
        """Test holatini vaqt kesimida aniqlash."""
        if not test.is_active:
            return "inactive"

        now = self._now()
        starts_at = self._as_utc(test.starts_at)
        ends_at = self._as_utc(test.ends_at)

        if starts_at and now < starts_at:
            return "not_started"
        if ends_at and now > ends_at:
            return "ended"
        return "available"

    def is_available(self, test: Test) -> bool:
        """Test hozir foydalanish uchun ochiqmi."""
        return self.availability_status(test) == "available"

    def availability_text(self, test: Test) -> str:
        """Test holati uchun o‘qilishi oson matn."""
        status = self.availability_status(test)
        if status == "not_started":
            if test.starts_at:
                return test.starts_at.strftime("%d.%m.%Y %H:%M")
            return "Tez orada"
        if status == "ended":
            return "Tugagan"
        if status == "inactive":
            return "Nofaol"
        return "Aktiv"

    async def get_available_tests(self) -> list[Test]:
        """Hozir foydalanish mumkin bo‘lgan testlar ro‘yxati."""
        try:
            result = await self.session.execute(
                select(Test).where(Test.is_active.is_(True))
            )
            tests = result.scalars().all()
            return [t for t in tests if self.availability_status(t) == "available"]
        except Exception as e:
            logger.error(f"❌ Testlar ro‘yxatini olishda xatolik: {e}")
            return []

    async def has_completed(self, user_id: int, test_id: int) -> bool:
        """Foydalanuvchi testni yakunlaganini tekshirish."""
        try:
            result = await self.session.execute(
                select(TestSession).where(
                    and_(
                        TestSession.user_id == user_id,
                        TestSession.test_id == test_id,
                        TestSession.is_completed.is_(True),
                    )
                )
            )
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"❌ Sessiya tekshirishda xatolik (User: {user_id}): {e}")
            return False

    async def get_or_create_session(
        self, user_id: int, test_id: int
    ) -> tuple[TestSession | None, str]:
        """Imtihon sessiyasini xavfsiz boshlash yoki faol sessiyani qaytarish."""
        try:
            result = await self.session.execute(select(Test).where(Test.id == test_id))
            test = result.scalar_one_or_none()
            if not test or self.availability_status(test) != "available":
                return None, "not_available"

            if await self.has_completed(user_id, test_id):
                return None, "completed"

            # Mavjud faol sessiyani qidirish
            active_res = await self.session.execute(
                select(TestSession).where(
                    and_(
                        TestSession.user_id == user_id,
                        TestSession.test_id == test_id,
                        TestSession.is_completed.is_(False),
                    )
                )
            )
            session_obj = active_res.scalar_one_or_none()
            if session_obj:
                if self.is_expired(session_obj):
                    await self.finish_session(session_obj, user_id)
                    return None, "completed"
                return session_obj, "continued"

            # FIXED: faqat is_active=True savollar tanlanadi
            q_res = await self.session.execute(
                select(Question.id).where(
                    Question.test_id == test_id,
                    Question.is_active.is_(True),
                )
            )
            all_q_ids = list(q_res.scalars().all())
            if not all_q_ids:
                return None, "no_questions"

            selected_ids = random.sample(
                all_q_ids, min(len(all_q_ids), TEST_MAX_QUESTIONS)
            )
            duration = len(selected_ids) * TEST_SECONDS_PER_QUESTION

            new_session = TestSession(
                user_id=user_id,
                test_id=test_id,
                question_ids=selected_ids,
                answers={},
                duration_seconds=duration,
                started_at=self._now(),
                is_completed=False,
            )
            self.session.add(new_session)
            await self.session.commit()
            await self.session.refresh(new_session)
            return new_session, "new"
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"❌ Sessiya yaratishda xatolik (User: {user_id}, Test: {test_id}): {e}"
            )
            return None, "error"

    def is_expired(self, session_obj: TestSession) -> bool:
        """Sessiyaga ajratilgan vaqt tugaganini tekshirish."""
        now = self._now()
        end_time = session_obj.started_at + timedelta(
            seconds=session_obj.duration_seconds
        )
        return now > end_time

    def remaining_seconds(self, session_obj: TestSession) -> int:
        """Sessiya yakunlanishi uchun qolgan vaqtni hisoblash (soniyada)."""
        now = self._now()
        end_time = session_obj.started_at + timedelta(
            seconds=session_obj.duration_seconds
        )
        remaining = int((end_time - now).total_seconds())
        return max(0, remaining)

    async def get_current_question(self, session_obj: TestSession) -> Question | None:
        """Foydalanuvchi hali javob bermagan navbatdagi savolni yuklash."""
        try:
            for q_id in session_obj.question_ids:
                if str(q_id) not in session_obj.answers:
                    res = await self.session.execute(
                        select(Question).where(Question.id == q_id)
                    )
                    return res.scalar_one_or_none()
            return None
        except Exception as e:
            logger.error(
                f"❌ Savolni yuklashda xatolik (Sessiya ID: {session_obj.id}): {e}"
            )
            return None

    async def save_answer(
        self, session_obj: TestSession, question_id: int, answer: str
    ) -> bool:
        """Foydalanuvchi javobini saqlash."""
        try:
            if self.is_expired(session_obj) or session_obj.is_completed:
                return False

            current_answers = dict(session_obj.answers or {})
            current_answers[str(question_id)] = answer.strip().upper()
            session_obj.answers = current_answers

            self.session.add(session_obj)
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"❌ Javobni saqlashda xatolik (Sessiya: {session_obj.id}): {e}"
            )
            return False

    async def finish_session(self, session_obj: TestSession, user_id: int) -> dict:
        """Sessiyani Rasch modeli asosida hisoblab, yakuniy natijani e'lon qilish."""
        try:
            if session_obj.is_completed:
                return {
                    "total": 0,
                    "correct": 0,
                    "answered": 0,
                    "score": 0,
                    "theta": 0.0,
                    "status": "already_completed",
                }

            q_ids = session_obj.question_ids
            q_result = await self.session.execute(
                select(Question).where(Question.id.in_(q_ids))
            )
            questions = {q.id: q for q in q_result.scalars().all()}

            correct_list = []
            difficulty_list = []
            correct_count = 0

            for q_id in q_ids:
                q = questions.get(q_id)
                if not q:
                    continue
                user_ans = session_obj.answers.get(str(q_id), "")
                is_correct = user_ans.upper() == q.correct.upper()

                correct_list.append(1.0 if is_correct else 0.0)
                difficulty_list.append(getattr(q, "difficulty", 0.0))
                if is_correct:
                    correct_count += 1

            theta = rasch_ability(correct_list, difficulty_list)
            score = theta_to_score(theta)

            session_obj.is_completed = True
            session_obj.rasch_score = score
            session_obj.completed_at = self._now()
            self.session.add(session_obj)

            from database.services.user_service import UserService

            u_service = UserService(self.session)
            user = await u_service.get_user(user_id)
            if user:
                user.test_score += int(score)
                user.total_score = user.test_score + user.referral_score
                self.session.add(user)

            await self.session.commit()

            return {
                "total": len(q_ids),
                "correct": correct_count,
                "answered": len(session_obj.answers),
                "score": score,
                "theta": round(theta, 2),
                "status": "success",
            }
        except Exception as e:
            await self.session.rollback()
            logger.error(
                f"❌ Sessiyani yopishda xatolik (Sessiya: {session_obj.id}): {e}"
            )
            return {
                "total": 0,
                "correct": 0,
                "answered": 0,
                "score": 0,
                "theta": 0.0,
                "status": "error",
            }

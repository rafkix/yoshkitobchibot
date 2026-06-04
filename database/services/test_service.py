# database/services/test_service.py

import logging
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.rasch import rasch_ability, theta_to_score
from database.models import Question, Test, TestSession

logger = logging.getLogger(__name__)

TEST_MAX_QUESTIONS = 40
TEST_SECONDS_PER_QUESTION = 90
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
        return self.availability_status(test) == "available"

    async def get_available_tests(self) -> list[Test]:
        try:
            result = await self.session.execute(
                select(Test).where(Test.is_active.is_(True))
            )
            tests = result.scalars().all()
            return [t for t in tests if self.is_available(t)]
        except Exception as e:
            logger.error(f"Testlarni olishda xatolik: {e}")
            return []

    async def has_completed(self, user_id: int, test_id: int) -> bool:
        result = await self.session.execute(
            select(TestSession.id).where(
                TestSession.user_id == user_id,
                TestSession.test_id == test_id,
                TestSession.is_completed.is_(True),
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_or_create_session(
        self,
        user_id: int,
        test_id: int,
    ):
        try:
            test_result = await self.session.execute(
                select(Test).where(Test.id == test_id)
            )
            test = test_result.scalar_one_or_none()

            if not test or not self.is_available(test):
                return None, "not_available"

            if await self.has_completed(user_id, test_id):
                return None, "completed"

            active_result = await self.session.execute(
                select(TestSession).where(
                    TestSession.user_id == user_id,
                    TestSession.test_id == test_id,
                    TestSession.is_completed.is_(False),
                )
            )

            session_obj = active_result.scalar_one_or_none()

            if session_obj:
                if self.is_expired(session_obj):
                    result = await self.finish_session(session_obj, user_id)
                    return None, result["status"]
                return session_obj, "continued"

            q_result = await self.session.execute(
                select(Question.id).where(
                    Question.test_id == test_id,
                    Question.is_active.is_(True),
                )
            )

            question_ids = list(q_result.scalars().all())

            if not question_ids:
                return None, "no_questions"

            selected = random.sample(
                question_ids,
                min(len(question_ids), TEST_MAX_QUESTIONS),
            )

            session_obj = TestSession(
                user_id=user_id,
                test_id=test_id,
                question_ids=selected,
                answers={},
                duration_seconds=len(selected) * TEST_SECONDS_PER_QUESTION,
                started_at=self._now(),
                is_completed=False,
            )

            self.session.add(session_obj)
            await self.session.commit()
            await self.session.refresh(session_obj)

            return session_obj, "new"

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Sessiya yaratishda xatolik: {e}")
            return None, "error"

    def is_expired(self, session_obj: TestSession) -> bool:
        end_time = session_obj.started_at + timedelta(
            seconds=session_obj.duration_seconds
        )
        return self._now() > end_time

    def remaining_seconds(self, session_obj: TestSession) -> int:
        end_time = session_obj.started_at + timedelta(
            seconds=session_obj.duration_seconds
        )
        return max(
            0,
            int((end_time - self._now()).total_seconds()),
        )

    async def get_current_question(
        self,
        session_obj: TestSession,
    ) -> Question | None:
        try:
            unanswered = [
                q_id
                for q_id in session_obj.question_ids
                if str(q_id) not in session_obj.answers
            ]

            if not unanswered:
                return None

            result = await self.session.execute(
                select(Question).where(Question.id == unanswered[0])
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Savol olishda xatolik: {e}")
            return None

    async def save_answer(
        self,
        session_obj: TestSession,
        question_id: int,
        answer: str,
    ) -> bool:
        try:
            if session_obj.is_completed or self.is_expired(session_obj):
                return False

            current_question = await self.get_current_question(session_obj)

            if not current_question:
                return False

            if current_question.id != question_id:
                return False

            answers = dict(session_obj.answers or {})

            if str(question_id) in answers:
                return False

            answers[str(question_id)] = answer.strip().upper()
            session_obj.answers = answers

            self.session.add(session_obj)
            await self.session.commit()
            await self.session.refresh(session_obj)

            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Javob saqlashda xatolik: {e}")
            return False

    async def finish_session(
        self,
        session_obj: TestSession,
        user_id: int,
    ) -> dict:
        try:
            locked = await self.session.execute(
                select(TestSession)
                .where(TestSession.id == session_obj.id)
                .with_for_update()
            )

            session_obj = locked.scalar_one()

            if session_obj.is_completed:
                return {
                    "status": "already_completed",
                    "total": 0,
                    "correct": 0,
                    "answered": 0,
                    "score": 0,
                    "theta": 0.0,
                }

            q_result = await self.session.execute(
                select(Question).where(Question.id.in_(session_obj.question_ids))
            )

            questions = {q.id: q for q in q_result.scalars().all()}

            correct_count = 0
            correct_list = []
            difficulty_list = []

            for q_id in session_obj.question_ids:
                q = questions.get(q_id)

                if not q:
                    continue

                answer = session_obj.answers.get(str(q_id), "")
                is_correct = answer.upper() == q.correct.upper()

                correct_list.append(1.0 if is_correct else 0.0)
                difficulty_list.append(getattr(q, "difficulty", 0.0))

                if is_correct:
                    correct_count += 1

            theta = rasch_ability(correct_list, difficulty_list)
            score = theta_to_score(theta)

            session_obj.is_completed = True
            session_obj.completed_at = self._now()
            session_obj.rasch_score = score

            from database.services.user_service import UserService

            user_service = UserService(self.session)
            user = await user_service.get_user(user_id)

            if user:
                user.test_score += int(score)
                user.total_score = user.test_score + user.referral_score
                self.session.add(user)

            self.session.add(session_obj)
            await self.session.commit()

            return {
                "status": "success",
                "total": len(session_obj.question_ids),
                "correct": correct_count,
                "answered": len(session_obj.answers),
                "score": score,
                "theta": round(theta, 2),
            }

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Sessiyani yopishda xatolik: {e}")

            return {
                "status": "error",
                "total": 0,
                "correct": 0,
                "answered": 0,
                "score": 0,
                "theta": 0.0,
            }

    def availability_text(self, test: Test) -> str:
        starts_at = self._as_utc(test.starts_at)
        ends_at = self._as_utc(test.ends_at)

        if not starts_at and not ends_at:
            return "Doimiy ochiq"

        if starts_at and not ends_at:
            return f"{starts_at:%d.%m.%Y %H:%M} dan"

        if not starts_at and ends_at:
            return f"{ends_at:%d.%m.%Y %H:%M} gacha"

        return f"{starts_at:%d.%m.%Y %H:%M} - {ends_at:%d.%m.%Y %H:%M}"

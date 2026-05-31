import random
from datetime import datetime, UTC, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Question, Test, TestSession
from app.utils.rasch import rasch_ability, theta_to_score
from database.services.settings_service import SettingsService

QUESTIONS_PER_SESSION = 40  # default (sozlamalardan o'zgartiriladi)
SECONDS_PER_QUESTION = 90   # default (sozlamalardan o'zgartiriladi)


class TestService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _as_utc(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def availability_status(self, test: Test) -> str:
        if not test.is_active:
            return "inactive"

        now = self._now()
        starts_at = self._as_utc(test.starts_at)
        ends_at = self._as_utc(test.ends_at)

        if starts_at and now < starts_at:
            return "not_started"
        if ends_at and now >= ends_at:
            return "ended"
        return "available"

    def is_available(self, test: Test) -> bool:
        return self.availability_status(test) == "available"

    async def get_available_tests(self) -> list[Test]:
        result = await self.session.execute(
            select(Test).where(Test.is_active.is_(True)).order_by(Test.id)
        )
        tests = result.scalars().all()
        return [test for test in tests if self.is_available(test)]

    def availability_text(self, test: Test) -> str:
        starts_at = self._as_utc(test.starts_at)
        ends_at = self._as_utc(test.ends_at)

        if starts_at and ends_at:
            return (
                f"{starts_at.strftime('%Y-%m-%d %H:%M')} dan "
                f"{ends_at.strftime('%Y-%m-%d %H:%M')} gacha"
            )
        if starts_at:
            return f"{starts_at.strftime('%Y-%m-%d %H:%M')} dan boshlab"
        if ends_at:
            return f"{ends_at.strftime('%Y-%m-%d %H:%M')} gacha"
        return "Doimiy ochiq"

    # ─── Tugallangan sessiya bormi? ────────────────────────────────────────
    async def has_completed(self, user_id: int, test_id: int) -> bool:
        result = await self.session.execute(
            select(TestSession).where(
                TestSession.user_id == user_id,
                TestSession.test_id == test_id,
                TestSession.is_completed.is_(True),
            )
        )
        return result.scalar_one_or_none() is not None

    # ─── Vaqt tugaganmi? ───────────────────────────────────────────────────
    def is_expired(self, session_obj: TestSession) -> bool:
        if session_obj.is_completed:
            return False
        deadline = session_obj.started_at.replace(tzinfo=UTC) + timedelta(
            seconds=session_obj.duration_seconds
        )
        return datetime.now(UTC) >= deadline

    # ─── Qolgan vaqt (soniya) ──────────────────────────────────────────────
    def remaining_seconds(self, session_obj: TestSession) -> int:
        deadline = session_obj.started_at.replace(tzinfo=UTC) + timedelta(
            seconds=session_obj.duration_seconds
        )
        return max(0, int((deadline - datetime.now(UTC)).total_seconds()))

    # ─── Sessiya olish yoki yangi ochish ───────────────────────────────────
    async def get_or_create_session(
        self, user_id: int, test_id: int
    ) -> tuple[TestSession | None, str]:
        """
        Qaytaradi: (session_obj, status)
        status: "completed" | "expired" | "continued" | "new" | "no_questions" | "not_available"
        """
        test_result = await self.session.execute(select(Test).where(Test.id == test_id))
        test = test_result.scalar_one_or_none()
        if not test or not self.is_available(test):
            return None, "not_available"

        if await self.has_completed(user_id, test_id):
            return None, "completed"

        # Tugallanmagan sessiya bormi?
        result = await self.session.execute(
            select(TestSession).where(
                TestSession.user_id == user_id,
                TestSession.test_id == test_id,
                TestSession.is_completed.is_(False),
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if self.is_expired(existing):
                await self.finish_session(existing, user_id)
                return None, "expired"
            return existing, "continued"

        # Yangi sessiya — shu testning savollarini yukla
        q_result = await self.session.execute(
            select(Question.id).where(
                Question.test_id == test_id,
                Question.is_active.is_(True),
            )
        )
        all_ids = [row[0] for row in q_result.fetchall()]

        if len(all_ids) == 0:
            return None, "no_questions"

        # Sozlamalardan dinamik qiymat olish
        svc = SettingsService(self.session)
        max_q = await svc.get_int("test_max_questions", QUESTIONS_PER_SESSION)
        sec_q = await svc.get_int("test_seconds_per_question", SECONDS_PER_QUESTION)

        # Mavjud savollar soni maksimaldan kam bo'lsa, hammasini oladi
        questions_count = min(max_q, len(all_ids))
        chosen = random.sample(all_ids, questions_count)

        # Vaqtni savol soniga qarab hisoblash
        duration = questions_count * sec_q

        session_obj = TestSession(
            user_id=user_id,
            test_id=test_id,
            question_ids=chosen,
            answers={},
            duration_seconds=duration,
            started_at=datetime.now(UTC),
        )
        self.session.add(session_obj)
        await self.session.commit()
        await self.session.refresh(session_obj)
        return session_obj, "new"

    # ─── Joriy savol ───────────────────────────────────────────────────────
    async def get_current_question(self, session_obj: TestSession) -> Question | None:
        answered = len(session_obj.answers)
        if answered >= len(session_obj.question_ids):
            return None
        q_id = session_obj.question_ids[answered]
        result = await self.session.execute(select(Question).where(Question.id == q_id))
        return result.scalar_one_or_none()

    # ─── Javob saqlash ─────────────────────────────────────────────────────
    async def save_answer(
        self, session_obj: TestSession, question_id: int, answer: str
    ):
        session_obj.answers = {**session_obj.answers, str(question_id): answer}
        await self.session.commit()

    # ─── Testni yakunlash va Rasch hisoblash ───────────────────────────────
    async def finish_session(self, session_obj: TestSession, user_id: int) -> dict:
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
            difficulty_list.append(q.difficulty)
            if is_correct:
                correct_count += 1

        theta = rasch_ability(correct_list, difficulty_list)
        score = theta_to_score(theta)

        session_obj.is_completed = True
        session_obj.rasch_score = score
        session_obj.completed_at = datetime.now(UTC)
        await self.session.commit()

        from database.services.user_service import UserService

        await UserService(self.session).add_test_score(user_id, score)

        return {
            "correct": correct_count,
            "total": len(q_ids),
            "answered": len(session_obj.answers),
            "theta": theta,
            "score": score,
        }

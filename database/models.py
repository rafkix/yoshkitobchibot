# database/models.py

import enum
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    JSON,  # 💡 O'zgarish: JSON import qilindi
)

# ❌ O'chirildi: from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ContestType(str, enum.Enum):
    MAIN = "main"
    ADDITIONAL = "additional"
    YOSH_KITOBXON_2026 = "yosh_kitobxon_2026"


class DirectionType(str, enum.Enum):
    AGE_10_14 = "10_14"
    AGE_15_19 = "15_19"
    AGE_20_30 = "20_30"


class ContestStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    FINISHED = "finished"


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    birth_date: Mapped[Optional[date]] = mapped_column(Date)
    phone_number: Mapped[Optional[str]] = mapped_column(String(50))
    region: Mapped[Optional[str]] = mapped_column(String(100))
    district: Mapped[Optional[str]] = mapped_column(String(100))
    neighborhood: Mapped[Optional[str]] = mapped_column(String(100))
    workplace: Mapped[Optional[str]] = mapped_column(String(255))
    contest: Mapped[Optional[ContestType]] = mapped_column(Enum(ContestType))
    direction: Mapped[Optional[DirectionType]] = mapped_column(Enum(DirectionType))

    is_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    referred_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="SET NULL")
    )

    test_score: Mapped[int] = mapped_column(Integer, default=0)
    referral_score: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Test(Base):
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    questions: Mapped[List["Question"]] = relationship(
        "Question", back_populates="test", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tests.id", ondelete="CASCADE")
    )
    text: Mapped[str] = mapped_column(Text)
    option_a: Mapped[str] = mapped_column(Text)
    option_b: Mapped[str] = mapped_column(Text)
    option_c: Mapped[str] = mapped_column(Text)
    option_d: Mapped[str] = mapped_column(Text)
    correct: Mapped[str] = mapped_column(String(10))  # 'a', 'b', 'c' yoki 'd'
    difficulty: Mapped[float] = mapped_column(default=0.0)

    test: Mapped["Test"] = relationship("Test", back_populates="questions")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TestSession(Base):
    __tablename__ = "test_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE")
    )
    test_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tests.id", ondelete="CASCADE")
    )

    # 💡 O'zgarish: JSONB larning o'rniga universal JSON qo'yildi
    question_ids: Mapped[List[int]] = mapped_column(JSON)
    answers: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=3600)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    rasch_score: Mapped[int] = mapped_column(Integer, default=0)


class Channel(Base):
    __tablename__ = "channels"

    channel_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255))
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True)
    channel_link: Mapped[Optional[str]] = mapped_column(String(500), unique=True)
    link_type: Mapped[str] = mapped_column(String(50))
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_check: Mapped[bool] = mapped_column(Boolean, default=True)
    previous_subscribers_count: Mapped[Optional[int]] = mapped_column(Integer)
    current_subscribers_count: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ChannelJoin(Base):
    __tablename__ = "channel_joins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE")
    )
    channel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("channels.channel_id", ondelete="CASCADE")
    )
    is_joined: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReferralContest(Base):
    __tablename__ = "referral_contests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    button_text: Mapped[Optional[str]] = mapped_column(String(100))
    min_referrals: Mapped[int] = mapped_column(Integer, default=10)
    prize_description: Mapped[Optional[str]] = mapped_column(Text)
    referral_score_per_user: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[ContestStatus] = mapped_column(
        Enum(ContestStatus), default=ContestStatus.DRAFT
    )
    winner_user_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

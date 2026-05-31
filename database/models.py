from datetime import date, datetime, UTC
from enum import Enum

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Enum as SqlEnum,
)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


# =========================================================
# BASE
# =========================================================


class Base(DeclarativeBase):
    pass


# =========================================================
# ENUMS
# =========================================================


class ContestType(str, Enum):
    YOSH_KITOBXON_2026 = "yosh_kitobxon_2026"


class DirectionType(str, Enum):
    AGE_10_14 = "10_14"
    AGE_15_19 = "15_19"
    AGE_20_30 = "20_30"


class ChannelType(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    REQUEST = "request"
    GROUP = "group"
    SUPERGROUP = "supergroup"


# =========================================================
# USER
# =========================================================


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=True)
    region: Mapped[str] = mapped_column(String(100), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=True)
    neighborhood: Mapped[str] = mapped_column(String(100), nullable=True)
    workplace: Mapped[str] = mapped_column(String(255), nullable=True)

    contest: Mapped[ContestType] = mapped_column(SqlEnum(ContestType), nullable=True)
    direction: Mapped[DirectionType] = mapped_column(
        SqlEnum(DirectionType), nullable=True
    )

    referral_score: Mapped[int] = mapped_column(Integer, default=0)
    test_score: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)

    referred_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id"),
        nullable=True,
    )

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
    )

    channel_joins = relationship("ChannelJoin", back_populates="user")

    def __repr__(self):
        return (
            f"<User("
            f"user_id={self.user_id}, "
            f"full_name='{self.full_name}', "
            f"total_score={self.total_score}"
            f")>"
        )


# =========================================================
# CHANNEL
# =========================================================


class Channel(Base):
    __tablename__ = "channels"

    channel_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    link_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="telegram_channel"
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(
        Integer, unique=True, nullable=True
    )
    channel_link: Mapped[str | None] = mapped_column(
        String(500), nullable=True, unique=True
    )
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_check: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    previous_subscribers_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    current_subscribers_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    joins: Mapped[list["ChannelJoin"]] = relationship(
        "ChannelJoin",
        back_populates="channel",
        cascade="all, delete-orphan",
    )


class ChannelJoin(Base):
    __tablename__ = "channel_join"
    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", name="uq_user_channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.channel_id", ondelete="CASCADE"), nullable=False
    )
    is_joined: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="channel_joins")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="joins")


# =========================================================
# AD
# =========================================================


class Ad(Base):
    __tablename__ = "ads"

    ad_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    buttons: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


# =========================================================
# TEST
# =========================================================


class Test(Base):
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    questions: Mapped[list["Question"]] = relationship(
        "Question", back_populates="test"
    )
    sessions: Mapped[list["TestSession"]] = relationship(
        "TestSession", back_populates="test"
    )


# =========================================================
# QUESTION
# =========================================================


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tests.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(500), nullable=False)
    option_b: Mapped[str] = mapped_column(String(500), nullable=False)
    option_c: Mapped[str] = mapped_column(String(500), nullable=False)
    option_d: Mapped[str] = mapped_column(String(500), nullable=False)
    correct: Mapped[str] = mapped_column(String(1), nullable=False)
    difficulty: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    test: Mapped["Test"] = relationship("Test", back_populates="questions")


# =========================================================
# TEST SESSION
# =========================================================


class TestSession(Base):
    __tablename__ = "test_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "test_id", name="uq_test_session_user_test"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id"), nullable=False
    )
    test_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tests.id"), nullable=False
    )
    question_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    rasch_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Savol soniga qarab dinamik hisoblangan vaqt (soniyada)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=3600)

    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    test: Mapped["Test"] = relationship("Test", back_populates="sessions")


# =========================================================
# CONTEST (Referal konkurs)
# =========================================================


class ContestStatus(str, Enum):
    ACTIVE   = "active"
    FINISHED = "finished"
    DRAFT    = "draft"


class ReferralContest(Base):
    """Admin tomonidan yaratilgan vaqtinchalik referal konkurs."""
    __tablename__ = "referral_contests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    button_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Nechtadan referal talab qilinadi
    min_referrals: Mapped[int] = mapped_column(Integer, default=10)

    prize_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ContestStatus] = mapped_column(
        SqlEnum(ContestStatus), default=ContestStatus.DRAFT, nullable=False
    )

    # g‘olib user_id (random tanlangandan keyin to‘ldiriladi)
    winner_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )


# =========================================================
# BOT SETTINGS (Sozlamalar)
# =========================================================


class BotSettings(Base):
    """Bot global sozlamalari — admin panel orqali boshqariladi."""
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    def __repr__(self):
        return f"<BotSettings(key={self.key}, value={self.value})>"


# =========================================================
# CUSTOM BUTTON (Admin tomonidan sozlanadigan tugmalar)
# =========================================================


class CustomButton(Base):
    """Admin tomonidan yaratilgan inline tugmalar."""
    __tablename__ = "custom_buttons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    text: Mapped[str] = mapped_column(String(255), nullable=False)  # tugma matni
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)  # url, message, handler
    action_value: Mapped[str | None] = mapped_column(Text, nullable=True)  # URL yoki xabar matni
    position: Mapped[int] = mapped_column(Integer, default=0)  # tartib raqami
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    menu_section: Mapped[str] = mapped_column(String(50), default="main")  # qaysi menyu
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

from datetime import date, datetime, UTC
from enum import Enum

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
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

    # Telegram ID
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )

    # Full Name
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )

    # Birth Date
    birth_date: Mapped[date] = mapped_column(
        Date,
        nullable=True,
    )

    # Phone Number
    phone_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
    )

    # Location
    region: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )

    district: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )

    neighborhood: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )

    # Work / Study
    workplace: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )

    # Contest
    contest: Mapped[ContestType] = mapped_column(
        SqlEnum(ContestType),
        nullable=True,
    )

    # Direction
    direction: Mapped[DirectionType] = mapped_column(
        SqlEnum(DirectionType),
        nullable=True,
    )

    # Scores
    referral_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    test_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    total_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    # Referral
    referred_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id"),
        nullable=True,
    )

    # Admin
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    # Registration Completed
    is_registered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    # Created At
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
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.channel_id", ondelete="CASCADE"),
        nullable=False,
    )
    is_joined: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="channel_joins")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="joins")


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

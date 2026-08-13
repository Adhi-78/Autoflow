from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    workflows = relationship("Workflow", back_populates="owner", cascade="all, delete-orphan")


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    # Trigger config, e.g. trigger_type="schedule", trigger_config='{"interval_minutes": 5}'
    trigger_type = Column(String, nullable=False)      # "schedule" | "webhook" | "gmail"
    trigger_config = Column(Text, default="{}")         # JSON stored as text

    # Which connected Google account this workflow uses (for a Gmail trigger and/or a
    # Sheets action within it). Null if the workflow doesn't touch Google at all.
    google_account_id = Column(Integer, ForeignKey("google_accounts.id"), nullable=True)

    last_run_at = Column(DateTime, nullable=True)
    gmail_seen_ids = Column(Text, default="[]")  # JSON list of already-processed Gmail message IDs
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="workflows")
    google_account = relationship("GoogleAccount")
    actions = relationship("Action", back_populates="workflow", cascade="all, delete-orphan", order_by="Action.step_order")
    executions = relationship("Execution", back_populates="workflow", cascade="all, delete-orphan")


class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    action_type = Column(String, nullable=False)   # "telegram" | "sheets" | "email" | "openai_summary"
    action_config = Column(Text, default="{}")      # JSON stored as text
    step_order = Column(Integer, default=0)          # order in which actions run

    workflow = relationship("Workflow", back_populates="actions")


class GoogleAccount(Base):
    """A single connected Google account. A user can connect several - each one
    gets a user-chosen label (or falls back to the account's own email address
    if no label was given), so workflows can be pointed at a specific one."""
    __tablename__ = "google_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    label = Column(String, nullable=False)          # user-provided name, or falls back to `email`
    email = Column(String, nullable=False)           # the actual Google account address, fetched via OAuth
    credentials_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    telegram_bot_token = Column(String, nullable=True)   # optional per-user override; usually blank, shared bot from .env is used
    telegram_chat_id = Column(String, nullable=True)
    telegram_connect_code = Column(String, nullable=True, unique=True)  # pending "Connect Telegram" code, cleared once matched

    # Superseded by the GoogleAccount table (multi-account support) - kept only
    # so old rows don't error out; no longer read or written to.
    google_credentials_json = Column(Text, nullable=True)
    sheets_spreadsheet_id = Column(String, nullable=True)

    # Phase 3 field, for News Digest summarization
    openai_api_key = Column(String, nullable=True)


class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    status = Column(String, default="running")   # "running" | "success" | "failed"
    message = Column(Text, default="")
    duration_seconds = Column(Float, default=0.0)
    started_at = Column(DateTime, default=datetime.utcnow)

    workflow = relationship("Workflow", back_populates="executions")

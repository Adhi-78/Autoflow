from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ---------- Auth ----------

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Actions ----------

class ActionCreate(BaseModel):
    action_type: str          # "telegram" | "sheets" | "email" | "openai_summary"
    action_config: dict = {}
    step_order: int = 0


class ActionOut(BaseModel):
    id: int
    action_type: str
    action_config: str
    step_order: int

    class Config:
        from_attributes = True


# ---------- Settings (per-user integration credentials) ----------

class SettingsIn(BaseModel):
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    sheets_spreadsheet_id: Optional[str] = None
    openai_api_key: Optional[str] = None


class SettingsOut(BaseModel):
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_connected: bool = False
    sheets_spreadsheet_id: Optional[str] = None
    openai_api_key: Optional[str] = None

    class Config:
        from_attributes = True


class TelegramConnectOut(BaseModel):
    connect_link: str
    code: str


# ---------- Google Accounts (multi-account support) ----------

class GoogleAccountOut(BaseModel):
    id: int
    label: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Workflows ----------

class WorkflowCreate(BaseModel):
    name: str
    trigger_type: str          # "schedule" | "webhook" | "gmail"
    trigger_config: dict = {}  # e.g. {"interval_minutes": 5}
    actions: List[ActionCreate] = []
    google_account_id: Optional[int] = None  # which connected account, if this workflow touches Gmail/Sheets


class WorkflowOut(BaseModel):
    id: int
    name: str
    is_active: bool
    trigger_type: str
    trigger_config: str
    google_account_id: Optional[int]
    last_run_at: Optional[datetime]
    created_at: datetime
    actions: List[ActionOut] = []

    class Config:
        from_attributes = True


# ---------- Executions ----------

class ExecutionOut(BaseModel):
    id: int
    workflow_id: int
    status: str
    message: str
    duration_seconds: float
    started_at: datetime

    class Config:
        from_attributes = True

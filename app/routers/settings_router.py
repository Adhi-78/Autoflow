from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.config import settings as app_settings

router = APIRouter(prefix="/settings", tags=["settings"])


def _to_out(settings_row) -> schemas.SettingsOut:
    if not settings_row:
        return schemas.SettingsOut()
    return schemas.SettingsOut(
        telegram_bot_token=settings_row.telegram_bot_token,
        telegram_chat_id=settings_row.telegram_chat_id,
        telegram_connected=bool(settings_row.telegram_chat_id),
        sheets_spreadsheet_id=settings_row.sheets_spreadsheet_id,
        openai_api_key=settings_row.openai_api_key,
        google_connected=bool(settings_row.google_credentials_json),
    )


@router.get("/", response_model=schemas.SettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    settings_row = db.query(models.Settings).filter(models.Settings.user_id == current_user.id).first()
    return _to_out(settings_row)


@router.post("/", response_model=schemas.SettingsOut)
def save_settings(
    settings_in: schemas.SettingsIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    settings_row = db.query(models.Settings).filter(models.Settings.user_id == current_user.id).first()
    if not settings_row:
        settings_row = models.Settings(user_id=current_user.id)
        db.add(settings_row)

    if settings_in.telegram_bot_token is not None:
        settings_row.telegram_bot_token = settings_in.telegram_bot_token
    if settings_in.telegram_chat_id is not None:
        settings_row.telegram_chat_id = settings_in.telegram_chat_id
    if settings_in.sheets_spreadsheet_id is not None:
        settings_row.sheets_spreadsheet_id = settings_in.sheets_spreadsheet_id
    if settings_in.openai_api_key is not None:
        settings_row.openai_api_key = settings_in.openai_api_key

    db.commit()
    db.refresh(settings_row)
    return _to_out(settings_row)


@router.post("/telegram/connect", response_model=schemas.TelegramConnectOut)
def start_telegram_connect(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Generates a one-time code and a t.me link. The user taps the link,
    Telegram sends /start <code> to the shared bot, and the background
    poller (see telegram_shared_bot.py) picks it up within ~15 seconds."""
    from app.telegram_shared_bot import generate_connect_code, build_connect_link

    if not app_settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="No shared Telegram bot configured. Add TELEGRAM_BOT_TOKEN to your .env file first.",
        )

    settings_row = db.query(models.Settings).filter(models.Settings.user_id == current_user.id).first()
    if not settings_row:
        settings_row = models.Settings(user_id=current_user.id)
        db.add(settings_row)

    code = generate_connect_code()
    settings_row.telegram_connect_code = code
    db.commit()

    link = build_connect_link(app_settings.TELEGRAM_BOT_TOKEN, code)
    if not link:
        raise HTTPException(
            status_code=500,
            detail="Could not reach Telegram to build the connect link. Double-check TELEGRAM_BOT_TOKEN in .env.",
        )

    return schemas.TelegramConnectOut(connect_link=link, code=code)


@router.post("/telegram/disconnect", response_model=schemas.SettingsOut)
def disconnect_telegram(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    settings_row = db.query(models.Settings).filter(models.Settings.user_id == current_user.id).first()
    if settings_row:
        settings_row.telegram_chat_id = None
        settings_row.telegram_connect_code = None
        db.commit()
        db.refresh(settings_row)
    return _to_out(settings_row)


@router.post("/google/disconnect", response_model=schemas.SettingsOut)
def disconnect_google(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    settings_row = db.query(models.Settings).filter(models.Settings.user_id == current_user.id).first()
    if settings_row:
        settings_row.google_credentials_json = None
        db.commit()
        db.refresh(settings_row)
    return _to_out(settings_row)

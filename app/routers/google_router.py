from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError

from app.database import SessionLocal
from app import models
from app.config import settings as app_settings
from app import google_oauth

router = APIRouter(prefix="/google", tags=["google"])


@router.get("/connect")
def connect(token: str = Query(..., description="Your AutoFlow login token")):
    """
    Called from a plain link (not a fetch request), since this needs to do a
    full-page redirect to Google's consent screen. The token is passed as a
    query param instead of a header for that reason.
    """
    try:
        payload = jwt.decode(token, app_settings.SECRET_KEY, algorithms=[app_settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token. Log in again.")

    try:
        auth_url = google_oauth.get_authorization_url(state=user_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=(
                "credentials.json not found in your project folder. "
                "Follow the 'Google OAuth setup' steps in the README, then try again."
            ),
        )
    return RedirectResponse(auth_url)


@router.get("/callback")
def callback(code: str = Query(...), state: str = Query(...)):
    """Google redirects here after the user approves access. Exchanges the code
    for real credentials and saves them for that user."""
    db = SessionLocal()
    try:
        creds = google_oauth.exchange_code_for_credentials(code)
        user_id = int(state)

        settings_row = db.query(models.Settings).filter(models.Settings.user_id == user_id).first()
        if not settings_row:
            settings_row = models.Settings(user_id=user_id)
            db.add(settings_row)

        settings_row.google_credentials_json = google_oauth.credentials_to_json(creds)
        db.commit()
    except Exception as e:
        return RedirectResponse(f"/app/#google-error={str(e)[:100]}")
    finally:
        db.close()

    return RedirectResponse("/app/#google-connected")

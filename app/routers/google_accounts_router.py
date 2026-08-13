from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/google-accounts", tags=["google-accounts"])


@router.get("/", response_model=list[schemas.GoogleAccountOut])
def list_google_accounts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return (
        db.query(models.GoogleAccount)
        .filter(models.GoogleAccount.user_id == current_user.id)
        .order_by(models.GoogleAccount.created_at)
        .all()
    )


@router.delete("/{account_id}")
def disconnect_google_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    account = (
        db.query(models.GoogleAccount)
        .filter(models.GoogleAccount.id == account_id, models.GoogleAccount.user_id == current_user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Google account not found")

    # Un-link any workflows pointing at this account first, so deleting it
    # doesn't hit a foreign key error - those workflows will just fail with a
    # clear "no Google account configured" message next time they run.
    db.query(models.Workflow).filter(models.Workflow.google_account_id == account.id).update(
        {"google_account_id": None}
    )
    db.delete(account)
    db.commit()
    return {"deleted": True}

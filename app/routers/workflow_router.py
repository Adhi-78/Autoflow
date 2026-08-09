import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.scheduler_engine import build_user_context, run_actions_and_log

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/", response_model=schemas.WorkflowOut)
def create_workflow(
    workflow_in: schemas.WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    workflow = models.Workflow(
        user_id=current_user.id,
        name=workflow_in.name,
        trigger_type=workflow_in.trigger_type,
        trigger_config=json.dumps(workflow_in.trigger_config),
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    for action_in in workflow_in.actions:
        action = models.Action(
            workflow_id=workflow.id,
            action_type=action_in.action_type,
            action_config=json.dumps(action_in.action_config),
            step_order=action_in.step_order,
        )
        db.add(action)

    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("/", response_model=list[schemas.WorkflowOut])
def list_workflows(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.Workflow).filter(models.Workflow.user_id == current_user.id).all()


@router.delete("/{workflow_id}")
def delete_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    workflow = (
        db.query(models.Workflow)
        .filter(models.Workflow.id == workflow_id, models.Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(workflow)
    db.commit()
    return {"deleted": True}


@router.get("/{workflow_id}/logs", response_model=list[schemas.ExecutionOut])
def get_logs(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    workflow = (
        db.query(models.Workflow)
        .filter(models.Workflow.id == workflow_id, models.Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return (
        db.query(models.Execution)
        .filter(models.Execution.workflow_id == workflow_id)
        .order_by(models.Execution.started_at.desc())
        .all()
    )


@router.post("/{workflow_id}/run-now", response_model=schemas.ExecutionOut)
def run_now(
    workflow_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Manually trigger a workflow immediately, without waiting for its schedule. Useful for testing.
    For a Gmail-trigger workflow, this runs the actions once using placeholder context rather than
    fetching real unread mail - use the scheduler (leave the server running) to see it react to real emails."""
    workflow = (
        db.query(models.Workflow)
        .filter(models.Workflow.id == workflow_id, models.Workflow.user_id == current_user.id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    context = build_user_context(db, workflow.user_id, f"Manual run for '{workflow.name}'")
    if workflow.trigger_type == "gmail":
        context.update({
            "subject": "(manual test run - no real email)",
            "sender": "(manual test run)",
            "snippet": "(manual test run)",
        })

    execution = run_actions_and_log(db, workflow, context)
    workflow.last_run_at = datetime.now()
    db.commit()
    db.refresh(execution)
    return execution

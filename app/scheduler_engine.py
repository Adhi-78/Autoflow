import json
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app import models
from app.actions.action_runner import run_action

scheduler = BackgroundScheduler()


def build_user_context(db, user_id: int, base_message: str) -> dict:
    """Gathers a user's saved credentials/settings into the context dict that
    gets passed through a workflow's actions. Shared by manual runs, schedule
    triggers, and Gmail triggers so all three behave identically."""
    user_settings = db.query(models.Settings).filter(models.Settings.user_id == user_id).first()
    return {
        "trigger_message": base_message,
        "telegram_bot_token": user_settings.telegram_bot_token if user_settings else None,
        "telegram_chat_id": user_settings.telegram_chat_id if user_settings else None,
        "google_credentials": user_settings.google_credentials_json if user_settings else None,
        "sheets_spreadsheet_id": user_settings.sheets_spreadsheet_id if user_settings else None,
        "openai_api_key": user_settings.openai_api_key if user_settings else None,
        "last_action_result": "",
    }


def run_actions_and_log(db, workflow, context: dict):
    """Runs every action in a workflow in order, feeding each action's output
    into the next one via context['last_action_result'], and records a single
    Execution log entry for the whole run."""
    start = time.time()
    execution = models.Execution(workflow_id=workflow.id, status="running")
    db.add(execution)
    db.commit()
    db.refresh(execution)

    try:
        log_messages = []
        for action in workflow.actions:
            log_msg, chain_value = run_action(action.action_type, action.action_config, context)
            log_messages.append(log_msg)
            if chain_value == "__SKIP__":
                log_messages.append("Remaining actions skipped")
                break
            context["last_action_result"] = chain_value

        execution.status = "success"
        execution.message = " | ".join(log_messages) if log_messages else "No actions configured"
    except Exception as e:
        execution.status = "failed"
        execution.message = str(e)
    finally:
        execution.duration_seconds = round(time.time() - start, 2)
        db.commit()

    return execution


def _is_due(workflow, default_interval_minutes: int) -> bool:
    config = json.loads(workflow.trigger_config or "{}")

    run_at = config.get("run_at")  # e.g. "07:30" - fixed daily time, takes priority if set
    if run_at:
        return _is_due_daily_time(workflow, run_at)

    interval_minutes = config.get("interval_minutes") or config.get("poll_interval_minutes") or default_interval_minutes
    if workflow.last_run_at is None:
        return True
    elapsed_minutes = (datetime.now() - workflow.last_run_at).total_seconds() / 60
    return elapsed_minutes >= interval_minutes


def _is_due_daily_time(workflow, run_at_str: str) -> bool:
    """For workflows set to run at a fixed clock time (e.g. '07:30') every day,
    rather than every N minutes. Uses the server's local time - since this app
    runs on your own machine, that's whatever timezone you're actually in."""
    try:
        run_hour, run_minute = map(int, run_at_str.split(":"))
    except (ValueError, AttributeError):
        return False  # malformed config - don't fire rather than crash the scheduler

    now = datetime.now()
    target_today = now.replace(hour=run_hour, minute=run_minute, second=0, microsecond=0)

    if now < target_today:
        return False  # hasn't reached that time yet today

    if workflow.last_run_at is None:
        return True

    # Already ran today if the last run happened on today's date, at/after the target time
    already_ran_today = (
        workflow.last_run_at.date() == now.date()
        and workflow.last_run_at >= target_today
    )
    return not already_ran_today


def _check_schedule_workflow(db, workflow):
    if not _is_due(workflow, default_interval_minutes=60):
        return
    context = build_user_context(db, workflow.user_id, f"Scheduled trigger for '{workflow.name}'")
    run_actions_and_log(db, workflow, context)
    workflow.last_run_at = datetime.now()
    db.commit()


def _check_gmail_workflow(db, workflow):
    if not _is_due(workflow, default_interval_minutes=5):
        return

    user_settings = db.query(models.Settings).filter(models.Settings.user_id == workflow.user_id).first()
    workflow.last_run_at = datetime.now()

    if not user_settings or not user_settings.google_credentials_json:
        # Not connected yet - nothing to check, try again next poll instead of erroring
        db.commit()
        return

    from app.google_oauth import credentials_from_json
    from app.actions.gmail_sheets_action import fetch_unread_emails

    config = json.loads(workflow.trigger_config or "{}")
    query = config.get("query", "is:unread")

    try:
        creds = credentials_from_json(user_settings.google_credentials_json)
        emails = fetch_unread_emails(creds, query=query, max_results=5)
    except Exception:
        # Auth hiccup or network issue - skip this poll, try again next time
        # rather than crashing the whole scheduler loop.
        db.commit()
        return

    seen_ids = json.loads(workflow.gmail_seen_ids or "[]")
    new_emails = [e for e in emails if e["id"] not in seen_ids]

    for email in new_emails:
        context = build_user_context(db, workflow.user_id, f"New email: {email['subject']}")
        context.update({
            "subject": email["subject"],
            "sender": email["sender"],
            "snippet": email["snippet"],
        })
        run_actions_and_log(db, workflow, context)

    # Keep the seen-list capped so it doesn't grow forever
    seen_ids = (seen_ids + [e["id"] for e in new_emails])[-50:]
    workflow.gmail_seen_ids = json.dumps(seen_ids)
    db.commit()


def check_and_run_due_workflows():
    """Called every 60 seconds by APScheduler. Each workflow's own interval
    decides whether it actually fires when checked."""
    db = SessionLocal()
    try:
        workflows = db.query(models.Workflow).filter(models.Workflow.is_active == True).all()  # noqa: E712
        for workflow in workflows:
            if workflow.trigger_type == "schedule":
                _check_schedule_workflow(db, workflow)
            elif workflow.trigger_type == "gmail":
                _check_gmail_workflow(db, workflow)
    finally:
        db.close()


def _poll_telegram_connect_job():
    """Checks every ~15 seconds for anyone who tapped a 'Connect Telegram' link."""
    db = SessionLocal()
    try:
        from app.telegram_shared_bot import poll_telegram_updates
        poll_telegram_updates(db)
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(check_and_run_due_workflows, "interval", seconds=60, id="poll_workflows")
    scheduler.add_job(_poll_telegram_connect_job, "interval", seconds=15, id="poll_telegram_connect")
    scheduler.start()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import auth_router, workflow_router, settings_router, google_router, google_accounts_router
from app.scheduler_engine import start_scheduler

# Creates tables on first run (fine for SQLite dev; use Alembic migrations later for Postgres)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AutoFlow", description="Personal automation platform", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(workflow_router.router)
app.include_router(settings_router.router)
app.include_router(google_router.router)
app.include_router(google_accounts_router.router)


@app.on_event("startup")
def on_startup():
    start_scheduler()


# Serves the frontend at http://127.0.0.1:8000/app
app.mount("/app", StaticFiles(directory="app/static", html=True), name="frontend")


@app.get("/")
def root():
    return {"status": "AutoFlow is running", "docs": "/docs", "app": "/app"}

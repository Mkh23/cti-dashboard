import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, me, webhooks, scans, s3_admin, farms, cattle, animals, announcements
from .routers import admin as admin_router
from .db import engine
from sqlalchemy import text

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app = FastAPI(title="CTI Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(me.router, prefix="/me", tags=["me"])
app.include_router(admin_router.router, prefix="/admin", tags=["admin"])
app.include_router(farms.router, prefix="/farms", tags=["farms"])
app.include_router(scans.router, prefix="/scans", tags=["scans"])
app.include_router(cattle.router, prefix="/cattle", tags=["cattle"])
app.include_router(animals.router, prefix="/animals", tags=["animals"])
app.include_router(announcements.router, tags=["announcements"])
app.include_router(webhooks.router, prefix="/ingest", tags=["ingest"])
app.include_router(s3_admin.router)

@app.get("/healthz")
def healthz():
    """Health check endpoint."""
    return {"ok": True, "service": "cti-api"}

@app.get("/readyz")
def readyz():
    """Readiness check - verify database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "db": "connected"}
    except Exception as e:
        return {"ok": False, "db": "disconnected", "error": str(e)}

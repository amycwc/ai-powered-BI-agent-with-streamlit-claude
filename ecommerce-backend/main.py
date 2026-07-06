# App initialization & core config
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import create_tables
from app.routers import analytics, chat, config

app = FastAPI(
    title="Business Intelligence API",
    description="AI-powered BI agent for retail analytics",
    version="1.0.0",
)

# CORS — allow Streamlit frontend (and any configured origins)
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat.router)
app.include_router(analytics.router)
app.include_router(config.router)


@app.on_event("startup")
def on_startup():
    # Tables created by populate_db.py; this is a no-op if they already exist
    create_tables()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Business Intelligence API"}


@app.get("/")
def root():
    return {"message": "Business Intelligence API — visit /docs for Swagger UI"}

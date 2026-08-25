import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, jobs, profile, settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
)

app = FastAPI(title="AI Job Intelligence", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(profile.router)
app.include_router(settings.router)
app.include_router(admin.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

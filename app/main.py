from fastapi import FastAPI
from app.routers import auth
from app.config import get_settings

settings = get_settings()
app = FastAPI(title="Auth Service", version="1.0.0")
app.include_router(auth.router, prefix="/api/v1/auth")

@app.get("/healthz")
async def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}

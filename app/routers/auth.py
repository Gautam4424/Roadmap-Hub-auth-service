from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app.models.models import User, UserSession
from app.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, UserOut
from app.events import publish_user_registered
from app.config import get_settings
import uuid

router = APIRouter(tags=["auth"])
settings = get_settings()

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Check duplicates
    r = await db.execute(select(User).where(User.email == body.email))
    if r.scalar_one_or_none(): raise HTTPException(400, "Email already registered")
    r = await db.execute(select(User).where(User.username == body.username))
    if r.scalar_one_or_none(): raise HTTPException(400, "Username already taken")

    user = User(email=body.email, username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    await db.flush()

    refresh = create_refresh_token()
    session = UserSession(user_id=user.id, refresh_token=refresh,
        ip_address=request.client.host if request.client else None,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    db.add(session)

    # Publish event — notification service will send welcome email
    await publish_user_registered(str(user.id), user.email, user.username)

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.email, user.is_admin),
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(User).where(User.email == body.email))
    user = r.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if not user.is_active: raise HTTPException(403, "Account deactivated")

    refresh = create_refresh_token()
    session = UserSession(user_id=user.id, refresh_token=refresh,
        ip_address=request.client.host if request.client else None,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    db.add(session)

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.email, user.is_admin),
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(UserSession).where(and_(
        UserSession.refresh_token == body.refresh_token,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow())))
    session = r.scalar_one_or_none()
    if not session: raise HTTPException(401, "Invalid or expired refresh token")

    r = await db.execute(select(User).where(User.id == session.user_id))
    user = r.scalar_one_or_none()
    if not user: raise HTTPException(401, "User not found")

    new_refresh = create_refresh_token()
    session.refresh_token = new_refresh
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.email, user.is_admin),
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

@router.post("/logout", status_code=204)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(UserSession).where(UserSession.refresh_token == body.refresh_token))
    session = r.scalar_one_or_none()
    if session: session.is_active = False

@router.get("/me", response_model=UserOut)
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.headers.get("X-User-ID")
    if not user_id: raise HTTPException(401, "Missing user context")
    r = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = r.scalar_one_or_none()
    if not user: raise HTTPException(404, "User not found")
    return user

@router.get("/validate")
async def validate_token(authorization: str = Header(None)):
    """Called by api-gateway to validate tokens. Internal use only."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    return {"user_id": payload["sub"], "email": payload["email"], "is_admin": payload.get("is_admin", False)}

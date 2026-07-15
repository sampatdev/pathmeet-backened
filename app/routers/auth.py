from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import OAuth2PasswordRequestForm


from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.core.security import hash_password, verify_password, create_access_token, get_current_user, oauth2_scheme
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.core.rate_limit import rate_limiter
from fastapi import Request
from jose import jwt
from app.core.token_blocklist import block_token
from datetime import datetime, timedelta, timezone




router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        display_name=user_in.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token, dependencies=[Depends(rate_limiter(5, 60))])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        data={"sub": str(user.id)},
        expires_minutes=settings.access_token_expire_minutes,
    )
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    jti = payload["jti"]
    exp = payload["exp"]

    now = datetime.now(timezone.utc).timestamp()
    seconds_remaining = max(int(exp - now), 1)

    await block_token(jti, seconds_remaining)
    return {"message": "Logged out successfully"}
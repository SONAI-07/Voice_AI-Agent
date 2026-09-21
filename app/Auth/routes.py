from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.Auth.dependencies import (
    get_current_tenant,
    get_current_user,
)

from app.Auth.schemas import (
    LoginRequest,
    MeResponse,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.tenant import Tenant
from app.models.user import User


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(
        payload: SignupRequest,
        db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == payload.email)
    )

    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
    )

    db.add(user)

    try:
        await db.flush()

        tenant = Tenant(
            name=payload.tenant_name,
            owner_user_id=user.id,
        )

        db.add(tenant)

        await db.commit()

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create account",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
        payload: LoginRequest,
        db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == payload.email)
    )

    user = result.scalar_one_or_none()

    if user is None or not verify_password(
            payload.password,
            user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
    )


@router.get(
    "/me",
    response_model=MeResponse,
)
async def me(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Tenant).where(
            Tenant.owner_user_id == current_user.id
        )
    )

    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return MeResponse(
        user=UserResponse.model_validate(current_user),
        tenant_id=tenant.id,
        tenant_name=tenant.name,
    )

# Temporary Function

@router.get("/test-tenant")
async def test_tenant(
        tenant: Tenant = Depends(get_current_tenant),
):
    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
    }
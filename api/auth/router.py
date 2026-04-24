from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.registration import register_user
from api.auth.schemas import RegisterRequest
from api.deps.db import get_db_session
from api.repositories.errors import ConflictError
from api.schemas.user import UserOut


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> UserOut:
    try:
        user = await register_user(
            db=db,
            email=str(payload.email),
            password=payload.password,
            name=payload.name,
        )
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to register user",
        ) from e

    return UserOut.model_validate(user)


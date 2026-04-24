from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.auth.registration import register_user
from api.auth.schemas import RegisterRequest
from api.deps.db import get_session_maker
from api.repositories.errors import ConflictError
from api.schemas.user import UserOut


router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserOut)
async def register(
    payload: RegisterRequest,
    response: Response,
    session_maker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> UserOut:
    try:
        user, created = await register_user(
            db=db,
            email=str(payload.email),
            password=payload.password,
            name=payload.name,
        )
    except ConflictError as e:
        logger.info(
            "auth_register_conflict",
            extra={"domain": "auth", "op": "register", "status_code": status.HTTP_409_CONFLICT},
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except Exception as e:
        logger.exception(
            "auth_register_unhandled_error",
            extra={"domain": "auth", "op": "register", "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to register user",
        ) from e

    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    logger.info(
        "auth_register_ok",
        extra={
            "domain": "auth",
            "op": "register",
            "status_code": response.status_code,
            "created_local_user": created,
            "entity_id": user.entity_id,
            "user_id": user.id,
        },
    )
    return UserOut.model_validate(user)

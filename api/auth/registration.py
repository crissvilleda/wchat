from __future__ import annotations

import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python import asyncio as supertokens_asyncio
from supertokens_python.recipe.emailpassword import asyncio as emailpassword_asyncio
from supertokens_python.recipe.emailpassword.interfaces import (
    EmailAlreadyExistsError,
    LinkingToSessionUserFailedError,
    SignUpOkResult,
)
from supertokens_python.types.base import AccountInfoInput

from api.repositories.entities import DbEntityRepository
from api.repositories.errors import ConflictError
from api.repositories.users import DbUserRepository
from api.services.users_service import UsersService
from orm_models.user import User

logger = logging.getLogger(__name__)


def _default_name_from_email(email: str) -> str:
    local = email.split("@", 1)[0].strip()
    return local or "user"


def _hash_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


async def _get_local_user_by_supertokens_user_id(db: AsyncSession, supertokens_user_id: str) -> User | None:
    stmt = select(User).where(
        User.supertokens_user_id == supertokens_user_id,
        User.deleted_at.is_(None),
    )
    return (await db.execute(stmt)).scalars().first()


async def _create_local_user_for_supertokens_user(
    *,
    db: AsyncSession,
    supertokens_user_id: str,
    email: str,
    display_name: str,
) -> User:
    entity_repo = DbEntityRepository(db)
    # Entity currently has no unique constraints; name collisions should be safe.
    entity = await entity_repo.create(name=f"{display_name}'s organization")

    users_service = UsersService(DbUserRepository(db))
    return await users_service.create(
        entity_id=entity.id,
        name=display_name,
        email=email,
        supertokens_user_id=supertokens_user_id,
    )


async def register_user(
    *,
    db: AsyncSession,
    email: str,
    password: str,
    name: str | None,
) -> tuple[User, bool]:
    display_name = name or _default_name_from_email(email)

    created_supertokens_user = False
    supertokens_user_id_hash: str | None = None

    st_res = await emailpassword_asyncio.sign_up(
        email=email,
        password=password,
        tenant_id=emailpassword_asyncio.DEFAULT_TENANT_ID,
    )

    if isinstance(st_res, EmailAlreadyExistsError):
        matches = await supertokens_asyncio.list_users_by_account_info(
            tenant_id=emailpassword_asyncio.DEFAULT_TENANT_ID,
            account_info=AccountInfoInput(email=email),
        )
        if not matches:
            logger.info(
                "auth_register_supertokens_email_exists_but_lookup_empty",
                extra={"domain": "auth", "op": "register", "path": "email_exists"},
            )
            raise ConflictError("Email already exists")

        supertokens_user_id = matches[0].id
        supertokens_user_id_hash = _hash_id(supertokens_user_id)
        existing = await _get_local_user_by_supertokens_user_id(db, supertokens_user_id)
        if existing is not None:
            logger.info(
                "auth_register_existing_linked_user",
                extra={
                    "domain": "auth",
                    "op": "register",
                    "path": "email_exists",
                    "linked_local_user": True,
                    "supertokens_user_id_hash": supertokens_user_id_hash,
                },
            )
            return existing, False

        user = await _create_local_user_for_supertokens_user(
            db=db,
            supertokens_user_id=supertokens_user_id,
            email=email,
            display_name=display_name,
        )
        logger.info(
            "auth_register_linked_local_user_created",
            extra={
                "domain": "auth",
                "op": "register",
                "path": "email_exists",
                "created_local_user": True,
                "created_supertokens_user": False,
                "supertokens_user_id_hash": supertokens_user_id_hash,
            },
        )
        return user, True
    if isinstance(st_res, LinkingToSessionUserFailedError):
        # This should not happen for a public unauthenticated signup.
        raise ConflictError("Unable to link signup to session user")
    if not isinstance(st_res, SignUpOkResult):
        raise RuntimeError(f"Unexpected SuperTokens signup result: {type(st_res)!r}")

    supertokens_user_id = st_res.user.id
    created_supertokens_user = True
    supertokens_user_id_hash = _hash_id(supertokens_user_id)

    try:
        user = await _create_local_user_for_supertokens_user(
            db=db,
            supertokens_user_id=supertokens_user_id,
            email=email,
            display_name=display_name,
        )
    except Exception:
        logger.exception(
            "auth_register_local_persist_failed",
            extra={
                "domain": "auth",
                "op": "register",
                "path": "new_signup",
                "created_supertokens_user": created_supertokens_user,
                "supertokens_user_id_hash": supertokens_user_id_hash,
            },
        )
        if created_supertokens_user:
            # Avoid orphan SuperTokens users if local persistence fails.
            await supertokens_asyncio.delete_user(supertokens_user_id)
        raise

    logger.info(
        "auth_register_new_user_created",
        extra={
            "domain": "auth",
            "op": "register",
            "path": "new_signup",
            "created_local_user": True,
            "created_supertokens_user": True,
            "supertokens_user_id_hash": supertokens_user_id_hash,
        },
    )
    return user, True


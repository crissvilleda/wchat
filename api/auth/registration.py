from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from supertokens_python import asyncio as supertokens_asyncio
from supertokens_python.recipe.emailpassword import asyncio as emailpassword_asyncio
from supertokens_python.recipe.emailpassword.interfaces import (
    EmailAlreadyExistsError,
    LinkingToSessionUserFailedError,
    SignUpOkResult,
)

from api.repositories.entities import DbEntityRepository
from api.repositories.errors import ConflictError
from api.repositories.users import DbUserRepository
from api.services.users_service import UsersService
from orm_models.user import User


def _default_name_from_email(email: str) -> str:
    local = email.split("@", 1)[0].strip()
    return local or "user"


async def register_user(
    *,
    db: AsyncSession,
    email: str,
    password: str,
    name: str | None,
) -> User:
    display_name = name or _default_name_from_email(email)

    st_res = await emailpassword_asyncio.sign_up(
        email=email,
        password=password,
        tenant_id=emailpassword_asyncio.DEFAULT_TENANT_ID,
    )

    if isinstance(st_res, EmailAlreadyExistsError):
        raise ConflictError("Email already exists")
    if isinstance(st_res, LinkingToSessionUserFailedError):
        # This should not happen for a public unauthenticated signup.
        raise ConflictError("Unable to link signup to session user")
    if not isinstance(st_res, SignUpOkResult):
        raise RuntimeError(f"Unexpected SuperTokens signup result: {type(st_res)!r}")

    supertokens_user_id = st_res.user.id

    try:
        entity_repo = DbEntityRepository(db)
        entity = await entity_repo.create(name=f"{display_name}'s organization")

        users_service = UsersService(DbUserRepository(db))
        user = await users_service.create(
            entity_id=entity.id,
            name=display_name,
            email=email,
            supertokens_user_id=supertokens_user_id,
        )
    except Exception:
        # Avoid orphan SuperTokens users if local persistence fails.
        await supertokens_asyncio.delete_user(supertokens_user_id)
        raise

    return user


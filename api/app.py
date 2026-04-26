import os

from api.logging_setup import configure_logging

configure_logging()

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from supertokens_python import get_all_cors_headers
from supertokens_python.framework.fastapi import get_middleware

from api.routers.me import router as me_router
from api.routers.whatsapp import router as whatsapp_router
from api.routers.users import router as users_router
from api.routers.customers import router as customers_router
from api.routers.mailboxes import router as mailboxes_router
from api.routers.customer_streaming_entitlements import (
    router as customer_streaming_entitlements_router,
)
from api.routers.streaming_services import router as streaming_services_router
from api.auth import auth_router
from api.supertokens_init import init_supertokens


init_supertokens()

fastapi_app = FastAPI(title="wchatv0")

fastapi_app.add_middleware(get_middleware())

# Apply the `/api` prefix once here (don’t repeat it in every router).
fastapi_app.include_router(whatsapp_router, prefix="/api")
fastapi_app.include_router(me_router, prefix="/api")
fastapi_app.include_router(auth_router, prefix="/api")
fastapi_app.include_router(users_router, prefix="/api")
fastapi_app.include_router(customers_router, prefix="/api")
fastapi_app.include_router(customer_streaming_entitlements_router, prefix="/api")
fastapi_app.include_router(mailboxes_router, prefix="/api")
fastapi_app.include_router(streaming_services_router, prefix="/api")

cors_origins = os.getenv("SUPERTOKENS_CORS_ORIGINS")
if cors_origins:
    allow_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
else:
    allow_origins = [
        os.getenv("SUPERTOKENS_WEBSITE_DOMAIN", "http://localhost:3000")]

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type"] + get_all_cors_headers(),
)

from fastapi import FastAPI

from api.routers.whatsapp import router as whatsapp_router


fastapi_app = FastAPI(title="wchatv0")

# Apply the `/api` prefix once here (don’t repeat it in every router).
fastapi_app.include_router(whatsapp_router, prefix="/api")

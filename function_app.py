import azure.functions as func

from api import fastapi_app

app = func.AsgiFunctionApp(
    app=fastapi_app,
    http_auth_level=func.AuthLevel.ANONYMOUS,
)

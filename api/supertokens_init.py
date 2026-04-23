import os

from supertokens_python import InputAppInfo, SupertokensConfig, init
from supertokens_python.recipe import emailpassword, session

_INITIALIZED = False


def init_supertokens() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    app_name = os.getenv("SUPERTOKENS_APP_NAME", "wchatv0")

    api_domain = os.getenv("SUPERTOKENS_API_DOMAIN", "http://localhost:8000")
    website_domain = os.getenv("SUPERTOKENS_WEBSITE_DOMAIN", "http://localhost:3000")

    api_base_path = os.getenv("SUPERTOKENS_API_BASE_PATH", "/auth")
    website_base_path = os.getenv("SUPERTOKENS_WEBSITE_BASE_PATH", "/auth")

    connection_uri = os.getenv("SUPERTOKENS_CONNECTION_URI", "https://try.supertokens.io")
    api_key = os.getenv("SUPERTOKENS_API_KEY")

    init(
        app_info=InputAppInfo(
            app_name=app_name,
            api_domain=api_domain,
            website_domain=website_domain,
            api_base_path=api_base_path,
            website_base_path=website_base_path,
        ),
        supertokens_config=SupertokensConfig(
            connection_uri=connection_uri,
            api_key=api_key,
        ),
        framework="fastapi",
        recipe_list=[
            session.init(),
            emailpassword.init(),
        ],
        mode="asgi",
    )

    _INITIALIZED = True

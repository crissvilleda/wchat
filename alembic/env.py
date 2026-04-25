import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from orm_models import BaseModel

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.BaseModel.metadata
target_metadata = BaseModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def _sync_url_for_alembic(url: str) -> str:
    """
    Alembic runs migrations through a synchronous SQLAlchemy Engine.

    The app may use an async URL (e.g. postgresql+asyncpg). When DB_URL_ASYNC is
    set, convert common async dialects to their sync counterparts.
    """

    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite+aiosqlite://", "sqlite+pysqlite://", 1)
    if url.startswith("mysql+aiomysql://"):
        return url.replace("mysql+aiomysql://", "mysql+pymysql://", 1)

    return url


def _get_database_url() -> str:
    env_url = os.getenv("DB_URL_ASYNC")
    if env_url:
        return _sync_url_for_alembic(env_url)

    return config.get_main_option("sqlalchemy.url")


def _pg_search_path_connect_args(url: str) -> dict[str, str] | None:
    if url.startswith("postgresql"):
        return {"options": "-c search_path=private,public"}
    return None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url = _get_database_url()
    connect_args = _pg_search_path_connect_args(url)
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
        **({"connect_args": connect_args} if connect_args else {}),
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

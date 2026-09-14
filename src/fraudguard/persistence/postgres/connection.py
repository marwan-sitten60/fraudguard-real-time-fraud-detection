from sqlalchemy import URL, Engine, create_engine

from fraudguard.core.config import Settings


def database_url(settings: Settings) -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )


def database_engine(settings: Settings) -> Engine:
    return create_engine(
        database_url(settings), pool_pre_ping=True, connect_args={"connect_timeout": 3}
    )

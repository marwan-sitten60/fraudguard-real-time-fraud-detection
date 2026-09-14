from alembic import context

from fraudguard.core.config import Settings
from fraudguard.persistence.postgres.connection import database_engine, database_url

settings = Settings()

if context.is_offline_mode():
    context.configure(
        url=database_url(settings), literal_binds=True, dialect_opts={"paramstyle": "named"}
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = database_engine(settings)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()

from alembic import context

from madrid.db import Base, data_dir, make_engine

config = context.config
target_metadata = Base.metadata


def run(connection):
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if config.attributes.get("connection") is not None:
    run(config.attributes["connection"])
else:
    engine = make_engine(data_dir() / "madrid.sqlite3")
    with engine.connect() as connection:
        run(connection)

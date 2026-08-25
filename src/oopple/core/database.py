"""Database engine, session management, and table lifecycle."""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from oopple.core.config import settings

DATABASE_URL = f"sqlite:///{settings.db_path}"
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db(custom_engine=None) -> None:
    """Initialize all database tables."""
    target_engine = custom_engine or engine
    SQLModel.metadata.create_all(target_engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI / Application session generator."""
    with Session(engine) as session:
        yield session

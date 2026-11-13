from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import settings

engine = create_engine(settings.database_url, pool_size=10, max_overflow=10, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

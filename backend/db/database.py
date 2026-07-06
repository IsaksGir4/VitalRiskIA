from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from settings.config import settings
engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
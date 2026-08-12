from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.utils.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    # Imported for the side effect of registering the models on Base.metadata
    # before create_all runs — without this the tables are never created.
    from app.models.session_model import TriageSession, Message  # noqa: F401
    Base.metadata.create_all(bind=engine)
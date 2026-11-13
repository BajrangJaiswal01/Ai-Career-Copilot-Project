import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DATABASE_URL = os.getenv(
    "DATABASE_URL"," ").strip()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={
        "ssl": {
            "ssl": True
        }
    } if DATABASE_URL.startswith("mysql") else {}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

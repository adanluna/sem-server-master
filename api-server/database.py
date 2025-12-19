import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Cargar .env.local
load_dotenv(".env.local")

# Leer variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "semefo")
DB_USER = os.getenv("DB_USER", "semefo_user")
DB_PASS = os.getenv("DB_PASS", "Claudia01$!")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Engine y sesión
engine = create_engine(
    DATABASE_URL,
    connect_args={"options": "-c timezone=UTC"}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para ORM
Base = declarative_base()

# Dependencia


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

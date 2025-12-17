import os
import argparse
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Index, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from dotenv import load_dotenv

load_dotenv()

# --- Database Configuration ---
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Connection String
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- SQLAlchemy Setup ---
engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 5})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- Database Model ---
class FitsFile(Base):
    """
    SQLAlchemy model for a FITS file record.
    """
    __tablename__ = 'fits_files'

    id = Column(Integer, primary_key=True)
    filepath = Column(String, unique=True, nullable=False)
    filename = Column(String, nullable=False)
    object_name = Column(String, index=True)
    date_obs = Column(DateTime)
    exptime = Column(Float)
    altitude = Column(Float)
    observatory = Column(String)
    header_dump = Column(JSONB)

    # Client information
    client_hostname = Column(String)
    client_os = Column(String)
    client_mac = Column(String, index=True)

    def __repr__(self):
        return f"<FitsFile(filename='{self.filename}', object='{self.object_name}', date='{self.date_obs}')>"

# Add a specific index for case-insensitive search on object_name
Index('idx_object_name_lower', func.lower(FitsFile.object_name), postgresql_using='btree')


def get_db_session():
    """
    Provides a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Creates the database tables if they don't exist.
    """
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully (if they didn't exist).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manage the database schema for the FITS catalog."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop the 'fits_files' table and recreate it. WARNING: This will delete all existing data.",
    )
    args = parser.parse_args()

    if args.reset:
        print("Resetting database: Dropping 'fits_files' table...")
        # Drop the specific table
        FitsFile.__table__.drop(engine, checkfirst=True)
        print("Table dropped. Recreating...")
        create_tables()
    else:
        # Default behavior: create tables if they don't exist
        create_tables()

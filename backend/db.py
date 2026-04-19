import datetime
from sqlalchemy import create_engine, Column, String, DateTime, LargeBinary, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./contracts.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class ContractDocument(Base):
    __tablename__ = "documents"
    doc_id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    text = Column(Text, nullable=False)

# Utility for creating tables

def init_db():
    Base.metadata.create_all(bind=engine)

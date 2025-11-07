from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

# Database configuration
DATABASE_URL = "sqlite:///./data/xtractor.db"
os.makedirs("data", exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class State(Base):
    """Model for Nigerian States"""
    __tablename__ = "states"
    
    id = Column(Integer, primary_key=True, index=True)
    state_name = Column(String(100), unique=True, nullable=False, index=True)
    state_code = Column(String(10), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    lgas = relationship("LGA", back_populates="state", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<State {self.state_name} ({self.state_code})>"


class LGA(Base):
    """Model for Local Government Areas"""
    __tablename__ = "lgas"
    
    id = Column(Integer, primary_key=True, index=True)
    lga_name = Column(String(150), nullable=False, index=True)
    lga_code = Column(String(20), nullable=False, index=True)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    state = relationship("State", back_populates="lgas")
    wards = relationship("Ward", back_populates="lga", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<LGA {self.lga_name} ({self.lga_code})>"


class Ward(Base):
    """Model for Electoral Wards"""
    __tablename__ = "wards"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_name = Column(String(150), nullable=False, index=True)
    ward_code = Column(String(20), nullable=False, index=True)
    lga_id = Column(Integer, ForeignKey("lgas.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    lga = relationship("LGA", back_populates="wards")
    
    def __repr__(self):
        return f"<Ward {self.ward_name} ({self.ward_code})>"


class ExtractionLog(Base):
    """Log for PDF extraction operations"""
    __tablename__ = "extraction_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    total_lgas_extracted = Column(Integer, default=0)
    total_wards_extracted = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending, success, failed
    error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<ExtractionLog {self.filename} - {self.status}>"


# Create all tables
Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

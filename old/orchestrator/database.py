import os
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import datetime
from swisper_core import get_logger

logger = get_logger(__name__)

Base = declarative_base()

class SwisperSession(Base):
    __tablename__ = 'swisper_sessions'
    
    session_id = Column(String, primary_key=True)
    title = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    message_count = Column(Integer, default=0)
    last_user_text = Column(Text, nullable=True)
    last_user_ts = Column(DateTime, nullable=True)
    short_summary = Column(Text, nullable=True)
    chat_history = Column(JSONB, nullable=False, default=list)
    session_metadata = Column(JSONB, nullable=False, default=dict)
    has_contract = Column(Boolean, default=False)

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        try:
            db_host = os.getenv('POSTGRES_HOST', 'localhost')
            db_port = os.getenv('POSTGRES_PORT', '5432')
            db_name = os.getenv('POSTGRES_DB', 'swisper')
            db_user = os.getenv('POSTGRES_USER', 'swisper')
            db_password = os.getenv('POSTGRES_PASSWORD', 'swisper')
            
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            
            self.engine = create_engine(
                database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False
            )
            
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            Base.metadata.create_all(bind=self.engine)
            
            logger.info(f"Database connection initialized successfully to {db_host}:{db_port}/{db_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}", exc_info=True)
            raise
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    def health_check(self) -> bool:
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

db_manager = DatabaseManager()

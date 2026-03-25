from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

Base = declarative_base()


class PipelineLog(Base):
    __tablename__ = "pipeline_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), nullable=False, index=True)
    document_name = Column(String(500), nullable=False)
    stage = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    latency_ms = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index('idx_document_stage', 'document_id', 'stage'),
        Index('idx_status_timestamp', 'status', 'timestamp'),
    )


class ChunkLog(Base):
    __tablename__ = "chunk_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), nullable=False, index=True)
    chunk_id = Column(String(255), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_type = Column(String(50), nullable=False)
    extraction_confidence = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index('idx_document_chunk', 'document_id', 'chunk_id'),
    )


class FieldLog(Base):
    __tablename__ = "field_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    field_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    source_chunks = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    validation_status = Column(String(20), nullable=True)
    metadata = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index('idx_document_field', 'document_id', 'field_name'),
        Index('idx_confidence', 'confidence'),
    )


class RetryLog(Base):
    __tablename__ = "retry_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), nullable=False, index=True)
    stage = Column(String(50), nullable=False)
    retry_count = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    success = Column(String(20), nullable=True)
    metadata = Column(JSON, nullable=True)


class CostLog(Base):
    __tablename__ = "cost_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), nullable=False, index=True)
    service = Column(String(50), nullable=False, index=True)
    operation = Column(String(100), nullable=False)
    tokens_used = Column(Integer, nullable=True)
    pages_processed = Column(Integer, nullable=True)
    queries_executed = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    metadata = Column(JSON, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    user_id = Column(String(255), nullable=True)
    user_email = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    ip_address = Column(String(50), nullable=True)
    template_version = Column(String(50), nullable=True)
    metadata = Column(JSON, nullable=True)


class PipelineLogSchema(BaseModel):
    document_id: str
    document_name: str
    stage: str
    status: str
    timestamp: Optional[datetime] = None
    latency_ms: Optional[int] = None
    confidence_score: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ChunkLogSchema(BaseModel):
    document_id: str
    chunk_id: str
    chunk_index: int
    chunk_type: str
    extraction_confidence: Optional[float] = None
    timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class FieldLogSchema(BaseModel):
    document_id: str
    field_name: str
    field_value: Optional[str] = None
    confidence: Optional[float] = None
    source_chunks: Optional[List[str]] = None
    timestamp: Optional[datetime] = None
    validation_status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

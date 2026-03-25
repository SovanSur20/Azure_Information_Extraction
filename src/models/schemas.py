from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    DIAGRAM = "diagram"
    MIXED = "mixed"


class ProcessingStage(str, Enum):
    UPLOADED = "uploaded"
    OCR = "ocr"
    CHUNKING = "chunking"
    EXTRACTION = "extraction"
    INDEXING = "indexing"
    RETRIEVAL = "retrieval"
    AGGREGATION = "aggregation"
    VALIDATION = "validation"
    COMPLETED = "completed"
    FAILED = "failed"


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    chunk_type: ChunkType
    content: str
    page_number: int
    bounding_box: Optional[BoundingBox] = None
    image_data: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractedField(BaseModel):
    field_name: str
    field_value: Optional[str] = None
    confidence: float
    source_chunks: List[str] = Field(default_factory=list)
    extraction_method: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OEMPartSpecification(BaseModel):
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    manufacturer: Optional[str] = None
    material: Optional[str] = None
    dimensions: Optional[str] = None
    weight: Optional[str] = None
    tolerance: Optional[str] = None
    surface_finish: Optional[str] = None
    coating: Optional[str] = None
    certifications: List[str] = Field(default_factory=list)
    technical_specifications: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    is_valid: bool
    confidence_score: float
    missing_fields: List[str] = Field(default_factory=list)
    low_confidence_fields: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class ProcessedDocument(BaseModel):
    document_id: str
    document_name: str
    document_url: str
    stage: ProcessingStage
    chunks: List[DocumentChunk] = Field(default_factory=list)
    extracted_fields: List[ExtractedField] = Field(default_factory=list)
    specification: Optional[OEMPartSpecification] = None
    validation_result: Optional[ValidationResult] = None
    processing_time_ms: Optional[int] = None
    total_cost_usd: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchQuery(BaseModel):
    query: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    top_k: int = 5
    include_semantic: bool = True
    include_keyword: bool = True
    min_confidence: float = 0.7


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    chunk_type: ChunkType
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationMetrics(BaseModel):
    document_id: str
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    extraction_accuracy: Dict[str, float] = Field(default_factory=dict)
    latency_ms: int
    cost_usd: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

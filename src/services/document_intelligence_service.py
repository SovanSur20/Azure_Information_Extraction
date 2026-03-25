from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import base64
from io import BytesIO

from src.config.settings import settings
from src.auth.azure_auth import auth_manager
from src.logging.logger import centralized_logger
from src.models.schemas import DocumentChunk, ChunkType, BoundingBox


class DocumentIntelligenceService:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._initialize_client()

    def _initialize_client(self) -> None:
        try:
            credential = auth_manager.get_credential()
            self.client = DocumentAnalysisClient(
                endpoint=settings.azure_document_intelligence_endpoint,
                credential=credential
            )
            self.logger.info("Document Intelligence service initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Document Intelligence: {str(e)}")
            raise

    def analyze_document(
        self,
        document_data: bytes,
        document_id: str,
        document_name: str
    ) -> List[DocumentChunk]:
        try:
            start_time = self._get_current_time_ms()
            
            self.logger.info(f"Starting OCR analysis for document: {document_name}")
            
            poller = self.client.begin_analyze_document(
                "prebuilt-layout",
                document=BytesIO(document_data)
            )
            result = poller.result()
            
            duration = self._get_current_time_ms() - start_time
            
            centralized_logger.log_pipeline(
                document_id=document_id,
                document_name=document_name,
                stage="ocr",
                status="success",
                latency_ms=duration,
                metadata={"pages": len(result.pages)}
            )
            
            centralized_logger.log_cost(
                document_id=document_id,
                service="document_intelligence",
                operation="analyze_layout",
                pages_processed=len(result.pages),
                estimated_cost_usd=len(result.pages) * 0.01
            )
            
            chunks = self._extract_chunks(result, document_id)
            
            self.logger.info(
                f"OCR completed: {len(chunks)} chunks extracted from {len(result.pages)} pages"
            )
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"OCR analysis failed: {str(e)}")
            centralized_logger.log_pipeline(
                document_id=document_id,
                document_name=document_name,
                stage="ocr",
                status="failed",
                error_message=str(e)
            )
            raise

    def _extract_chunks(self, result: Any, document_id: str) -> List[DocumentChunk]:
        chunks = []
        chunk_index = 0
        
        for page_idx, page in enumerate(result.pages):
            page_number = page_idx + 1
            
            for paragraph in page.lines if hasattr(page, 'lines') else []:
                if paragraph.content.strip():
                    chunk = DocumentChunk(
                        chunk_id=f"{document_id}_chunk_{chunk_index}",
                        document_id=document_id,
                        chunk_index=chunk_index,
                        chunk_type=ChunkType.TEXT,
                        content=paragraph.content,
                        page_number=page_number,
                        bounding_box=self._extract_bounding_box(paragraph.polygon) if hasattr(paragraph, 'polygon') else None,
                        confidence=paragraph.confidence if hasattr(paragraph, 'confidence') else None,
                        metadata={
                            "page_width": page.width,
                            "page_height": page.height,
                            "unit": page.unit
                        }
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    
                    centralized_logger.log_chunk(
                        document_id=document_id,
                        chunk_id=chunk.chunk_id,
                        chunk_index=chunk_index,
                        chunk_type=chunk.chunk_type.value,
                        extraction_confidence=chunk.confidence
                    )
        
        if hasattr(result, 'tables') and result.tables:
            for table_idx, table in enumerate(result.tables):
                table_content = self._format_table(table)
                chunk = DocumentChunk(
                    chunk_id=f"{document_id}_table_{table_idx}",
                    document_id=document_id,
                    chunk_index=chunk_index,
                    chunk_type=ChunkType.TABLE,
                    content=table_content,
                    page_number=table.bounding_regions[0].page_number if table.bounding_regions else 1,
                    confidence=None,
                    metadata={
                        "row_count": table.row_count,
                        "column_count": table.column_count
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
                
                centralized_logger.log_chunk(
                    document_id=document_id,
                    chunk_id=chunk.chunk_id,
                    chunk_index=chunk_index,
                    chunk_type=chunk.chunk_type.value,
                    metadata=chunk.metadata
                )
        
        return chunks

    def _extract_bounding_box(self, polygon: List[Any]) -> Optional[BoundingBox]:
        if not polygon or len(polygon) < 4:
            return None
        
        x_coords = [point.x for point in polygon]
        y_coords = [point.y for point in polygon]
        
        return BoundingBox(
            x=min(x_coords),
            y=min(y_coords),
            width=max(x_coords) - min(x_coords),
            height=max(y_coords) - min(y_coords)
        )

    def _format_table(self, table: Any) -> str:
        rows = {}
        for cell in table.cells:
            row_idx = cell.row_index
            col_idx = cell.column_index
            if row_idx not in rows:
                rows[row_idx] = {}
            rows[row_idx][col_idx] = cell.content
        
        formatted_rows = []
        for row_idx in sorted(rows.keys()):
            row = rows[row_idx]
            formatted_row = " | ".join([row.get(col_idx, "") for col_idx in sorted(row.keys())])
            formatted_rows.append(formatted_row)
        
        return "\n".join(formatted_rows)

    @staticmethod
    def _get_current_time_ms() -> int:
        return int(datetime.utcnow().timestamp() * 1000)


document_intelligence_service = DocumentIntelligenceService()

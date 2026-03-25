from typing import List, Dict, Any
import logging
import tiktoken
from datetime import datetime

from src.models.schemas import DocumentChunk, ChunkType
from src.config.settings import settings
from src.logging.logger import centralized_logger


class ChunkingService:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def chunk_document(
        self,
        chunks: List[DocumentChunk],
        document_id: str,
        document_name: str
    ) -> List[DocumentChunk]:
        try:
            start_time = self._get_current_time_ms()
            
            self.logger.info(f"Starting chunking for document: {document_name}")
            
            text_chunks = [c for c in chunks if c.chunk_type == ChunkType.TEXT]
            table_chunks = [c for c in chunks if c.chunk_type == ChunkType.TABLE]
            
            refined_text_chunks = self._refine_text_chunks(text_chunks, document_id)
            
            all_chunks = refined_text_chunks + table_chunks
            
            all_chunks.sort(key=lambda x: (x.page_number, x.chunk_index))
            
            for idx, chunk in enumerate(all_chunks):
                chunk.chunk_index = idx
                chunk.chunk_id = f"{document_id}_refined_{idx}"
            
            duration = self._get_current_time_ms() - start_time
            
            centralized_logger.log_pipeline(
                document_id=document_id,
                document_name=document_name,
                stage="chunking",
                status="success",
                latency_ms=duration,
                metadata={
                    "original_chunks": len(chunks),
                    "refined_chunks": len(all_chunks),
                    "text_chunks": len(refined_text_chunks),
                    "table_chunks": len(table_chunks)
                }
            )
            
            self.logger.info(
                f"Chunking completed: {len(chunks)} -> {len(all_chunks)} chunks"
            )
            
            return all_chunks
            
        except Exception as e:
            self.logger.error(f"Chunking failed: {str(e)}")
            centralized_logger.log_pipeline(
                document_id=document_id,
                document_name=document_name,
                stage="chunking",
                status="failed",
                error_message=str(e)
            )
            raise

    def _refine_text_chunks(
        self,
        chunks: List[DocumentChunk],
        document_id: str
    ) -> List[DocumentChunk]:
        refined_chunks = []
        current_chunk_text = ""
        current_page = 1
        chunk_index = 0
        
        for chunk in chunks:
            chunk_tokens = len(self.encoding.encode(chunk.content))
            current_tokens = len(self.encoding.encode(current_chunk_text))
            
            if current_tokens + chunk_tokens <= self.chunk_size:
                current_chunk_text += " " + chunk.content if current_chunk_text else chunk.content
                current_page = chunk.page_number
            else:
                if current_chunk_text:
                    refined_chunk = DocumentChunk(
                        chunk_id=f"{document_id}_text_{chunk_index}",
                        document_id=document_id,
                        chunk_index=chunk_index,
                        chunk_type=ChunkType.TEXT,
                        content=current_chunk_text.strip(),
                        page_number=current_page,
                        metadata={"token_count": len(self.encoding.encode(current_chunk_text))}
                    )
                    refined_chunks.append(refined_chunk)
                    chunk_index += 1
                
                overlap_text = self._get_overlap_text(current_chunk_text)
                current_chunk_text = overlap_text + " " + chunk.content
                current_page = chunk.page_number
        
        if current_chunk_text:
            refined_chunk = DocumentChunk(
                chunk_id=f"{document_id}_text_{chunk_index}",
                document_id=document_id,
                chunk_index=chunk_index,
                chunk_type=ChunkType.TEXT,
                content=current_chunk_text.strip(),
                page_number=current_page,
                metadata={"token_count": len(self.encoding.encode(current_chunk_text))}
            )
            refined_chunks.append(refined_chunk)
        
        return refined_chunks

    def _get_overlap_text(self, text: str) -> str:
        tokens = self.encoding.encode(text)
        if len(tokens) <= self.chunk_overlap:
            return text
        
        overlap_tokens = tokens[-self.chunk_overlap:]
        return self.encoding.decode(overlap_tokens)

    @staticmethod
    def _get_current_time_ms() -> int:
        return int(datetime.utcnow().timestamp() * 1000)


chunking_service = ChunkingService()

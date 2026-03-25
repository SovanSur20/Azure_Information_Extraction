from typing import Optional, Dict, Any
import logging
from datetime import datetime
import json
import random

from src.models.schemas import (
    ProcessedDocument,
    ProcessingStage,
    ExtractedField,
    OEMPartSpecification
)
from src.services.storage_service import storage_service
from src.services.document_intelligence_service import document_intelligence_service
from src.services.chunking_service import chunking_service
from src.services.openai_service import openai_service
from src.services.search_service import search_service
from src.services.validation_service import validation_service
from src.evaluation.evaluator import pipeline_evaluator
from src.logging.logger import centralized_logger
from src.config.settings import settings


class PipelineOrchestrator:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    async def process_document(
        self,
        blob_name: str,
        container_name: str,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        pipeline_start_time = self._get_current_time_ms()
        total_cost = 0.0
        
        try:
            self.logger.info(f"Starting pipeline for document: {blob_name}")
            
            centralized_logger.log_audit(
                document_id=document_id,
                action="document_uploaded",
                user_id=metadata.get("user_id") if metadata else None,
                user_email=metadata.get("user_email") if metadata else None,
                template_version="v1.0.0",
                metadata=metadata
            )
            
            processed_doc = ProcessedDocument(
                document_id=document_id,
                document_name=blob_name,
                document_url=storage_service.get_blob_url(container_name, blob_name),
                stage=ProcessingStage.UPLOADED,
                metadata=metadata or {}
            )
            
            document_data = storage_service.download_blob(container_name, blob_name)
            
            chunks = document_intelligence_service.analyze_document(
                document_data=document_data,
                document_id=document_id,
                document_name=blob_name
            )
            processed_doc.chunks = chunks
            processed_doc.stage = ProcessingStage.OCR
            
            refined_chunks = chunking_service.chunk_document(
                chunks=chunks,
                document_id=document_id,
                document_name=blob_name
            )
            processed_doc.chunks = refined_chunks
            processed_doc.stage = ProcessingStage.CHUNKING
            
            all_extracted_fields = []
            for chunk in refined_chunks:
                try:
                    fields = openai_service.extract_fields_from_chunk(
                        chunk=chunk,
                        document_id=document_id
                    )
                    all_extracted_fields.extend(fields)
                except Exception as e:
                    self.logger.warning(f"Failed to extract from chunk {chunk.chunk_id}: {str(e)}")
                    continue
            
            processed_doc.extracted_fields = all_extracted_fields
            processed_doc.stage = ProcessingStage.EXTRACTION
            
            search_service.index_chunks(
                chunks=refined_chunks,
                document_id=document_id,
                document_name=blob_name
            )
            processed_doc.stage = ProcessingStage.INDEXING
            
            specification = openai_service.aggregate_fields(
                all_fields=all_extracted_fields,
                document_id=document_id,
                document_name=blob_name
            )
            processed_doc.specification = specification
            processed_doc.stage = ProcessingStage.AGGREGATION
            
            validation_result = validation_service.validate_specification(
                specification=specification,
                extracted_fields=all_extracted_fields,
                document_id=document_id,
                document_name=blob_name
            )
            processed_doc.validation_result = validation_result
            processed_doc.stage = ProcessingStage.VALIDATION
            
            if settings.enable_evaluation and random.random() < settings.evaluation_sample_rate:
                try:
                    evaluation_metrics = pipeline_evaluator.evaluate_extraction(
                        processed_doc=processed_doc,
                        ground_truth=None
                    )
                    processed_doc.metadata["evaluation_metrics"] = evaluation_metrics.model_dump()
                except Exception as e:
                    self.logger.warning(f"Evaluation failed: {str(e)}")
            
            pipeline_duration = self._get_current_time_ms() - pipeline_start_time
            processed_doc.processing_time_ms = pipeline_duration
            processed_doc.stage = ProcessingStage.COMPLETED
            
            centralized_logger.log_pipeline(
                document_id=document_id,
                document_name=blob_name,
                stage="completed",
                status="success",
                latency_ms=pipeline_duration,
                confidence_score=validation_result.confidence_score,
                metadata={
                    "total_chunks": len(refined_chunks),
                    "extracted_fields": len(all_extracted_fields),
                    "is_valid": validation_result.is_valid
                }
            )
            
            centralized_logger.log_audit(
                document_id=document_id,
                action="document_processed",
                template_version="v1.0.0",
                metadata={
                    "processing_time_ms": pipeline_duration,
                    "validation_status": "valid" if validation_result.is_valid else "invalid"
                }
            )
            
            self.logger.info(
                f"Pipeline completed successfully for {blob_name} in {pipeline_duration}ms"
            )
            
            return processed_doc
            
        except Exception as e:
            self.logger.error(f"Pipeline failed for {blob_name}: {str(e)}")
            
            centralized_logger.log_pipeline(
                document_id=document_id,
                document_name=blob_name,
                stage="failed",
                status="failed",
                error_message=str(e),
                latency_ms=self._get_current_time_ms() - pipeline_start_time
            )
            
            raise

    async def query_document(
        self,
        document_id: str,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        try:
            from src.models.schemas import SearchQuery
            
            search_query = SearchQuery(
                query=query,
                top_k=top_k,
                include_semantic=True,
                include_keyword=True
            )
            
            results = search_service.hybrid_search(
                query=search_query,
                document_id=document_id
            )
            
            contexts = [result.content for result in results]
            
            answer = await self._generate_answer(query, contexts)
            
            if settings.enable_evaluation:
                try:
                    rag_scores = pipeline_evaluator.evaluate_rag_quality(
                        question=query,
                        retrieved_contexts=contexts,
                        generated_answer=answer,
                        ground_truth_answer=None
                    )
                except Exception as e:
                    self.logger.warning(f"RAG evaluation failed: {str(e)}")
                    rag_scores = {}
            else:
                rag_scores = {}
            
            return {
                "query": query,
                "answer": answer,
                "contexts": contexts,
                "sources": [
                    {
                        "chunk_id": r.chunk_id,
                        "page_number": r.metadata.get("page_number"),
                        "score": r.score
                    }
                    for r in results
                ],
                "evaluation_scores": rag_scores
            }
            
        except Exception as e:
            self.logger.error(f"Query failed: {str(e)}")
            raise

    async def _generate_answer(self, query: str, contexts: list) -> str:
        try:
            context_text = "\n\n".join(contexts)
            
            prompt = f"""
Based on the following context from technical documentation, answer the question.

Context:
{context_text}

Question: {query}

Provide a clear, accurate answer based only on the information in the context.
If the answer is not in the context, say so.
"""
            
            response = openai_service.client.chat.completions.create(
                model=settings.azure_openai_deployment_gpt4,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical documentation assistant. Provide accurate answers based on the given context."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Answer generation failed: {str(e)}")
            return "Unable to generate answer due to an error."

    @staticmethod
    def _get_current_time_ms() -> int:
        return int(datetime.utcnow().timestamp() * 1000)


pipeline_orchestrator = PipelineOrchestrator()

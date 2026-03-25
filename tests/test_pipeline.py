import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json

from src.models.schemas import (
    DocumentChunk,
    ChunkType,
    ExtractedField,
    OEMPartSpecification,
    ValidationResult,
    ProcessedDocument,
    ProcessingStage
)
from src.services.validation_service import validation_service


class TestValidationService:
    def test_check_missing_fields(self):
        spec = OEMPartSpecification(
            part_number="ABC123",
            part_name="Test Part",
            material=None,
            dimensions=None
        )
        
        missing = validation_service._check_missing_fields(spec)
        
        assert "material" in missing
        assert "dimensions" in missing
        assert "part_number" not in missing

    def test_validate_dimensions_format(self):
        assert validation_service._validate_dimensions_format("120x45x15 mm") == True
        assert validation_service._validate_dimensions_format("5 inches diameter") == True
        assert validation_service._validate_dimensions_format("random text") == False

    def test_validate_weight_format(self):
        assert validation_service._validate_weight_format("2.5 kg") == True
        assert validation_service._validate_weight_format("500 grams") == True
        assert validation_service._validate_weight_format("random text") == False

    def test_calculate_overall_confidence(self):
        spec = OEMPartSpecification(
            part_number="ABC123",
            part_name="Test Part",
            material="Steel",
            dimensions="120x45x15 mm"
        )
        
        fields = [
            ExtractedField(
                field_name="part_number",
                field_value="ABC123",
                confidence=0.95,
                source_chunks=["chunk1"],
                extraction_method="gpt4"
            ),
            ExtractedField(
                field_name="material",
                field_value="Steel",
                confidence=0.90,
                source_chunks=["chunk2"],
                extraction_method="gpt4"
            )
        ]
        
        confidence = validation_service._calculate_overall_confidence(
            spec, fields, [], []
        )
        
        assert confidence > 0.8
        assert confidence <= 1.0


class TestChunkingService:
    def test_chunk_document(self):
        from src.services.chunking_service import chunking_service
        
        chunks = [
            DocumentChunk(
                chunk_id="test_1",
                document_id="doc1",
                chunk_index=0,
                chunk_type=ChunkType.TEXT,
                content="This is a test chunk with some content.",
                page_number=1
            ),
            DocumentChunk(
                chunk_id="test_2",
                document_id="doc1",
                chunk_index=1,
                chunk_type=ChunkType.TEXT,
                content="Another test chunk with more content.",
                page_number=1
            )
        ]
        
        refined = chunking_service.chunk_document(
            chunks=chunks,
            document_id="doc1",
            document_name="test.pdf"
        )
        
        assert len(refined) > 0
        assert all(isinstance(c, DocumentChunk) for c in refined)


class TestHTMLGenerator:
    def test_generate_specification_html(self):
        from src.templates.html_generator import html_generator
        
        spec = OEMPartSpecification(
            part_number="ABC123",
            part_name="Test Part",
            manufacturer="Test Manufacturer",
            material="Steel",
            dimensions="120x45x15 mm",
            weight="2.5 kg",
            certifications=["ISO 9001", "CE"]
        )
        
        validation = ValidationResult(
            is_valid=True,
            confidence_score=0.92,
            missing_fields=[],
            low_confidence_fields=[],
            validation_errors=[],
            suggestions=["Specification appears complete"]
        )
        
        doc = ProcessedDocument(
            document_id="test123",
            document_name="test.pdf",
            document_url="https://test.blob.core.windows.net/test.pdf",
            stage=ProcessingStage.COMPLETED,
            specification=spec,
            validation_result=validation,
            processing_time_ms=5000
        )
        
        html = html_generator.generate_specification_html(doc)
        
        assert "ABC123" in html
        assert "Test Part" in html
        assert "Steel" in html
        assert "ISO 9001" in html


@pytest.mark.asyncio
class TestPipelineOrchestrator:
    @patch('src.services.storage_service.storage_service.download_blob')
    @patch('src.services.document_intelligence_service.document_intelligence_service.analyze_document')
    @patch('src.services.openai_service.openai_service.extract_fields_from_chunk')
    @patch('src.services.openai_service.openai_service.aggregate_fields')
    @patch('src.services.search_service.search_service.index_chunks')
    async def test_process_document(
        self,
        mock_index,
        mock_aggregate,
        mock_extract,
        mock_analyze,
        mock_download
    ):
        from src.pipeline.orchestrator import pipeline_orchestrator
        
        mock_download.return_value = b"fake pdf content"
        
        mock_analyze.return_value = [
            DocumentChunk(
                chunk_id="chunk1",
                document_id="doc1",
                chunk_index=0,
                chunk_type=ChunkType.TEXT,
                content="Test content",
                page_number=1
            )
        ]
        
        mock_extract.return_value = [
            ExtractedField(
                field_name="part_number",
                field_value="ABC123",
                confidence=0.95,
                source_chunks=["chunk1"],
                extraction_method="gpt4"
            )
        ]
        
        mock_aggregate.return_value = OEMPartSpecification(
            part_number="ABC123",
            part_name="Test Part",
            material="Steel"
        )
        
        result = await pipeline_orchestrator.process_document(
            blob_name="test.pdf",
            container_name="raw-documents",
            document_id="test123"
        )
        
        assert result.document_id == "test123"
        assert result.stage == ProcessingStage.COMPLETED
        assert result.specification is not None
        assert result.validation_result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

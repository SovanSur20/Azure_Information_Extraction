from openai import AzureOpenAI
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.auth.azure_auth import auth_manager
from src.logging.logger import centralized_logger
from src.models.schemas import DocumentChunk, ExtractedField, OEMPartSpecification


class OpenAIService:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._initialize_client()

    def _initialize_client(self) -> None:
        try:
            token_provider = lambda: auth_manager.get_cognitive_services_token()
            
            self.client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
                azure_ad_token_provider=token_provider
            )
            self.logger.info("OpenAI service initialized with Azure AD authentication")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI service: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def extract_fields_from_chunk(
        self,
        chunk: DocumentChunk,
        document_id: str,
        retry_count: int = 0
    ) -> List[ExtractedField]:
        try:
            start_time = self._get_current_time_ms()
            
            prompt = self._build_extraction_prompt(chunk)
            
            response = self.client.chat.completions.create(
                model=settings.azure_openai_deployment_gpt4,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured information from OEM technical documents. Extract all relevant fields with high precision."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            duration = self._get_current_time_ms() - start_time
            tokens_used = response.usage.total_tokens
            
            centralized_logger.log_cost(
                document_id=document_id,
                service="azure_openai",
                operation="extraction",
                tokens_used=tokens_used,
                estimated_cost_usd=self._calculate_cost(tokens_used, "gpt4")
            )
            
            extracted_data = json.loads(response.choices[0].message.content)
            fields = self._parse_extracted_fields(extracted_data, chunk.chunk_id)
            
            for field in fields:
                centralized_logger.log_field(
                    document_id=document_id,
                    field_name=field.field_name,
                    field_value=field.field_value,
                    confidence=field.confidence,
                    source_chunks=[chunk.chunk_id]
                )
            
            if retry_count > 0:
                centralized_logger.log_retry(
                    document_id=document_id,
                    stage="extraction",
                    retry_count=retry_count,
                    reason="low_confidence",
                    success="success"
                )
            
            return fields
            
        except Exception as e:
            self.logger.error(f"Field extraction failed for chunk {chunk.chunk_id}: {str(e)}")
            
            if retry_count < settings.max_retries:
                centralized_logger.log_retry(
                    document_id=document_id,
                    stage="extraction",
                    retry_count=retry_count + 1,
                    reason=str(e),
                    success="retrying"
                )
            
            raise

    def _build_extraction_prompt(self, chunk: DocumentChunk) -> str:
        return f"""
Extract structured information from the following OEM document chunk.

Chunk Type: {chunk.chunk_type.value}
Page Number: {chunk.page_number}
Content:
{chunk.content}

Extract the following fields if present:
- part_number: The part or model number
- part_name: Name or description of the part
- manufacturer: Manufacturer name
- material: Material composition
- dimensions: Physical dimensions (length, width, height, diameter, etc.)
- weight: Weight specifications
- tolerance: Manufacturing tolerances
- surface_finish: Surface finish specifications
- coating: Coating or plating information
- certifications: Any certifications or standards mentioned
- technical_specifications: Other technical details

Return a JSON object with the following structure:
{{
    "fields": [
        {{
            "field_name": "field_name",
            "field_value": "extracted_value",
            "confidence": 0.95
        }}
    ]
}}

Only include fields that are explicitly mentioned in the content. Set confidence based on clarity and certainty.
"""

    def _parse_extracted_fields(
        self,
        extracted_data: Dict[str, Any],
        chunk_id: str
    ) -> List[ExtractedField]:
        fields = []
        
        for field_data in extracted_data.get("fields", []):
            field = ExtractedField(
                field_name=field_data.get("field_name"),
                field_value=field_data.get("field_value"),
                confidence=field_data.get("confidence", 0.0),
                source_chunks=[chunk_id],
                extraction_method="gpt4_vision",
                metadata={"chunk_type": "text"}
            )
            fields.append(field)
        
        return fields

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def aggregate_fields(
        self,
        all_fields: List[ExtractedField],
        document_id: str,
        document_name: str
    ) -> OEMPartSpecification:
        try:
            start_time = self._get_current_time_ms()
            
            prompt = self._build_aggregation_prompt(all_fields)
            
            response = self.client.chat.completions.create(
                model=settings.azure_openai_deployment_gpt4,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at aggregating and consolidating extracted information from multiple sources. Resolve conflicts and provide the most accurate consolidated view."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            duration = self._get_current_time_ms() - start_time
            tokens_used = response.usage.total_tokens
            
            centralized_logger.log_cost(
                document_id=document_id,
                service="azure_openai",
                operation="aggregation",
                tokens_used=tokens_used,
                estimated_cost_usd=self._calculate_cost(tokens_used, "gpt4")
            )
            
            centralized_logger.log_pipeline(
                document_id=document_id,
                document_name=document_name,
                stage="aggregation",
                status="success",
                latency_ms=duration
            )
            
            aggregated_data = json.loads(response.choices[0].message.content)
            specification = self._parse_specification(aggregated_data)
            
            return specification
            
        except Exception as e:
            self.logger.error(f"Field aggregation failed: {str(e)}")
            centralized_logger.log_pipeline(
                document_id=document_id,
                document_name=document_name,
                stage="aggregation",
                status="failed",
                error_message=str(e)
            )
            raise

    def _build_aggregation_prompt(self, fields: List[ExtractedField]) -> str:
        fields_json = [
            {
                "field_name": f.field_name,
                "field_value": f.field_value,
                "confidence": f.confidence,
                "source_chunks": f.source_chunks
            }
            for f in fields
        ]
        
        return f"""
Aggregate and consolidate the following extracted fields from multiple document chunks.

Extracted Fields:
{json.dumps(fields_json, indent=2)}

Rules:
1. For duplicate fields, choose the value with highest confidence
2. If values conflict, use context to determine the most accurate one
3. Combine related information (e.g., multiple dimension mentions)
4. Extract certifications as a list
5. Group technical specifications into a structured object

Return a JSON object with this structure:
{{
    "part_number": "value or null",
    "part_name": "value or null",
    "manufacturer": "value or null",
    "material": "value or null",
    "dimensions": "value or null",
    "weight": "value or null",
    "tolerance": "value or null",
    "surface_finish": "value or null",
    "coating": "value or null",
    "certifications": ["cert1", "cert2"],
    "technical_specifications": {{"key": "value"}},
    "metadata": {{"confidence_score": 0.95}}
}}
"""

    def _parse_specification(self, data: Dict[str, Any]) -> OEMPartSpecification:
        return OEMPartSpecification(
            part_number=data.get("part_number"),
            part_name=data.get("part_name"),
            manufacturer=data.get("manufacturer"),
            material=data.get("material"),
            dimensions=data.get("dimensions"),
            weight=data.get("weight"),
            tolerance=data.get("tolerance"),
            surface_finish=data.get("surface_finish"),
            coating=data.get("coating"),
            certifications=data.get("certifications", []),
            technical_specifications=data.get("technical_specifications", {}),
            metadata=data.get("metadata", {})
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            response = self.client.embeddings.create(
                model=settings.azure_openai_deployment_embedding,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {str(e)}")
            raise

    def _calculate_cost(self, tokens: int, model: str) -> float:
        cost_per_1k = {
            "gpt4": 0.03,
            "embedding": 0.0001
        }
        return (tokens / 1000) * cost_per_1k.get(model, 0.01)

    @staticmethod
    def _get_current_time_ms() -> int:
        return int(datetime.utcnow().timestamp() * 1000)


openai_service = OpenAIService()

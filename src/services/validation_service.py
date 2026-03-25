from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from src.models.schemas import (
    OEMPartSpecification,
    ValidationResult,
    ExtractedField
)
from src.config.settings import settings
from src.logging.logger import centralized_logger


class ValidationService:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.confidence_threshold = settings.confidence_threshold
        
        self.required_fields = [
            "part_number",
            "part_name",
            "material",
            "dimensions"
        ]
        
        self.important_fields = [
            "manufacturer",
            "weight",
            "tolerance",
            "surface_finish"
        ]

    def validate_specification(
        self,
        specification: OEMPartSpecification,
        extracted_fields: List[ExtractedField],
        document_id: str,
        document_name: str
    ) -> ValidationResult:
        try:
            start_time = self._get_current_time_ms()
            
            self.logger.info(f"Validating specification for document: {document_name}")
            
            missing_fields = self._check_missing_fields(specification)
            low_confidence_fields = self._check_field_confidence(extracted_fields)
            validation_errors = self._check_data_quality(specification)
            suggestions = self._generate_suggestions(
                missing_fields,
                low_confidence_fields,
                validation_errors
            )
            
            overall_confidence = self._calculate_overall_confidence(
                specification,
                extracted_fields,
                missing_fields,
                low_confidence_fields
            )
            
            is_valid = (
                len(missing_fields) == 0 and
                len(validation_errors) == 0 and
                overall_confidence >= self.confidence_threshold
            )
            
            validation_result = ValidationResult(
                is_valid=is_valid,
                confidence_score=overall_confidence,
                missing_fields=missing_fields,
                low_confidence_fields=low_confidence_fields,
                validation_errors=validation_errors,
                suggestions=suggestions
            )
            
            duration = self._get_current_time_ms() - start_time
            
            centralized_logger.log_pipeline(
                document_id=document_id,
                document_name=document_name,
                stage="validation",
                status="success" if is_valid else "warning",
                latency_ms=duration,
                confidence_score=overall_confidence,
                metadata={
                    "missing_fields": len(missing_fields),
                    "low_confidence_fields": len(low_confidence_fields),
                    "validation_errors": len(validation_errors)
                }
            )
            
            self.logger.info(
                f"Validation completed - Valid: {is_valid}, "
                f"Confidence: {overall_confidence:.2f}, "
                f"Missing: {len(missing_fields)}, "
                f"Errors: {len(validation_errors)}"
            )
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            centralized_logger.log_pipeline(
                document_id=document_id,
                document_name=document_name,
                stage="validation",
                status="failed",
                error_message=str(e)
            )
            raise

    def _check_missing_fields(self, specification: OEMPartSpecification) -> List[str]:
        missing = []
        
        for field in self.required_fields:
            value = getattr(specification, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)
                centralized_logger.log_field(
                    document_id="validation",
                    field_name=field,
                    field_value=None,
                    confidence=0.0,
                    validation_status="missing"
                )
        
        return missing

    def _check_field_confidence(self, extracted_fields: List[ExtractedField]) -> List[str]:
        low_confidence = []
        
        field_confidence_map = {}
        for field in extracted_fields:
            if field.field_name not in field_confidence_map:
                field_confidence_map[field.field_name] = []
            field_confidence_map[field.field_name].append(field.confidence)
        
        for field_name, confidences in field_confidence_map.items():
            avg_confidence = sum(confidences) / len(confidences)
            if avg_confidence < self.confidence_threshold:
                low_confidence.append(field_name)
                self.logger.warning(
                    f"Low confidence for field '{field_name}': {avg_confidence:.2f}"
                )
        
        return low_confidence

    def _check_data_quality(self, specification: OEMPartSpecification) -> List[str]:
        errors = []
        
        if specification.dimensions:
            if not self._validate_dimensions_format(specification.dimensions):
                errors.append("Dimensions format appears invalid or incomplete")
        
        if specification.weight:
            if not self._validate_weight_format(specification.weight):
                errors.append("Weight format appears invalid")
        
        if specification.part_number:
            if len(specification.part_number) < 3:
                errors.append("Part number seems too short")
        
        if specification.tolerance:
            if not any(char in specification.tolerance for char in ['±', '+', '-', '±']):
                errors.append("Tolerance format may be invalid")
        
        return errors

    def _validate_dimensions_format(self, dimensions: str) -> bool:
        dimension_indicators = ['mm', 'cm', 'in', 'inch', 'x', '×', 'diameter', 'length', 'width', 'height']
        return any(indicator in dimensions.lower() for indicator in dimension_indicators)

    def _validate_weight_format(self, weight: str) -> bool:
        weight_units = ['kg', 'g', 'lb', 'oz', 'gram', 'kilogram', 'pound']
        return any(unit in weight.lower() for unit in weight_units)

    def _generate_suggestions(
        self,
        missing_fields: List[str],
        low_confidence_fields: List[str],
        validation_errors: List[str]
    ) -> List[str]:
        suggestions = []
        
        if missing_fields:
            suggestions.append(
                f"Review document for missing required fields: {', '.join(missing_fields)}"
            )
        
        if low_confidence_fields:
            suggestions.append(
                f"Manual verification recommended for low-confidence fields: {', '.join(low_confidence_fields)}"
            )
        
        if validation_errors:
            suggestions.append(
                "Data quality issues detected - consider re-extraction or manual review"
            )
        
        if not missing_fields and not low_confidence_fields and not validation_errors:
            suggestions.append("Specification appears complete and accurate")
        
        return suggestions

    def _calculate_overall_confidence(
        self,
        specification: OEMPartSpecification,
        extracted_fields: List[ExtractedField],
        missing_fields: List[str],
        low_confidence_fields: List[str]
    ) -> float:
        if not extracted_fields:
            return 0.0
        
        total_confidence = sum(field.confidence for field in extracted_fields)
        avg_confidence = total_confidence / len(extracted_fields)
        
        completeness_penalty = len(missing_fields) * 0.1
        quality_penalty = len(low_confidence_fields) * 0.05
        
        overall_confidence = max(0.0, avg_confidence - completeness_penalty - quality_penalty)
        
        return round(overall_confidence, 2)

    @staticmethod
    def _get_current_time_ms() -> int:
        return int(datetime.utcnow().timestamp() * 1000)


validation_service = ValidationService()

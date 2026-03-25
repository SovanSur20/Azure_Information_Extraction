from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Optional
import logging
from pathlib import Path
import json
from datetime import datetime

from src.models.schemas import ProcessedDocument, OEMPartSpecification, ValidationResult
from src.services.storage_service import storage_service
from src.config.settings import settings


class HTMLGenerator:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.template_dir = Path(__file__).parent / "templates"
        self.template_dir.mkdir(exist_ok=True)
        
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def generate_specification_html(
        self,
        processed_doc: ProcessedDocument
    ) -> str:
        try:
            self.logger.info(f"Generating HTML for document: {processed_doc.document_id}")
            
            template = self.env.get_template("specification_template.html")
            
            html_content = template.render(
                document=processed_doc,
                specification=processed_doc.specification,
                validation=processed_doc.validation_result,
                generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                version="1.0.0"
            )
            
            self.logger.info("HTML generated successfully")
            return html_content
            
        except Exception as e:
            self.logger.error(f"HTML generation failed: {str(e)}")
            return self._generate_fallback_html(processed_doc)

    def _generate_fallback_html(self, processed_doc: ProcessedDocument) -> str:
        spec = processed_doc.specification
        validation = processed_doc.validation_result
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OEM Part Specification - {processed_doc.document_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        .field {{
            margin: 15px 0;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
        }}
        .field-label {{
            font-weight: bold;
            color: #555;
            display: inline-block;
            width: 200px;
        }}
        .field-value {{
            color: #333;
        }}
        .validation {{
            margin: 20px 0;
            padding: 15px;
            border-radius: 4px;
        }}
        .validation.valid {{
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }}
        .validation.invalid {{
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }}
        .confidence-score {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin-left: 10px;
        }}
        .confidence-high {{
            background-color: #28a745;
            color: white;
        }}
        .confidence-medium {{
            background-color: #ffc107;
            color: black;
        }}
        .confidence-low {{
            background-color: #dc3545;
            color: white;
        }}
        .metadata {{
            margin-top: 30px;
            padding: 15px;
            background-color: #e9ecef;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        li {{
            padding: 5px 0;
        }}
        li:before {{
            content: "✓ ";
            color: #28a745;
            font-weight: bold;
        }}
        .warning-list li:before {{
            content: "⚠ ";
            color: #ffc107;
        }}
        .error-list li:before {{
            content: "✗ ";
            color: #dc3545;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>OEM Part Specification</h1>
        
        <div class="field">
            <span class="field-label">Document:</span>
            <span class="field-value">{processed_doc.document_name}</span>
        </div>
        
        <div class="field">
            <span class="field-label">Document ID:</span>
            <span class="field-value">{processed_doc.document_id}</span>
        </div>
        
        <div class="field">
            <span class="field-label">Processing Date:</span>
            <span class="field-value">{processed_doc.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")}</span>
        </div>
        
        {"<h2>Validation Status</h2>" if validation else ""}
        {self._render_validation(validation) if validation else ""}
        
        <h2>Part Information</h2>
        
        {self._render_field("Part Number", spec.part_number)}
        {self._render_field("Part Name", spec.part_name)}
        {self._render_field("Manufacturer", spec.manufacturer)}
        
        <h2>Material & Specifications</h2>
        
        {self._render_field("Material", spec.material)}
        {self._render_field("Dimensions", spec.dimensions)}
        {self._render_field("Weight", spec.weight)}
        {self._render_field("Tolerance", spec.tolerance)}
        {self._render_field("Surface Finish", spec.surface_finish)}
        {self._render_field("Coating", spec.coating)}
        
        {self._render_certifications(spec.certifications) if spec.certifications else ""}
        {self._render_technical_specs(spec.technical_specifications) if spec.technical_specifications else ""}
        
        <div class="metadata">
            <strong>Processing Metadata</strong><br>
            Processing Time: {processed_doc.processing_time_ms}ms<br>
            Total Chunks: {len(processed_doc.chunks)}<br>
            Extracted Fields: {len(processed_doc.extracted_fields)}<br>
            Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
        </div>
    </div>
</body>
</html>
"""
        return html

    def _render_validation(self, validation: ValidationResult) -> str:
        status_class = "valid" if validation.is_valid else "invalid"
        status_text = "Valid" if validation.is_valid else "Needs Review"
        
        confidence_class = "confidence-high" if validation.confidence_score >= 0.85 else \
                          "confidence-medium" if validation.confidence_score >= 0.70 else \
                          "confidence-low"
        
        html = f"""
        <div class="validation {status_class}">
            <strong>Status: {status_text}</strong>
            <span class="confidence-score {confidence_class}">
                Confidence: {validation.confidence_score:.2%}
            </span>
        """
        
        if validation.missing_fields:
            html += "<h3>Missing Fields:</h3><ul class='error-list'>"
            for field in validation.missing_fields:
                html += f"<li>{field}</li>"
            html += "</ul>"
        
        if validation.low_confidence_fields:
            html += "<h3>Low Confidence Fields:</h3><ul class='warning-list'>"
            for field in validation.low_confidence_fields:
                html += f"<li>{field}</li>"
            html += "</ul>"
        
        if validation.suggestions:
            html += "<h3>Suggestions:</h3><ul>"
            for suggestion in validation.suggestions:
                html += f"<li>{suggestion}</li>"
            html += "</ul>"
        
        html += "</div>"
        return html

    def _render_field(self, label: str, value: Optional[str]) -> str:
        if value:
            return f"""
        <div class="field">
            <span class="field-label">{label}:</span>
            <span class="field-value">{value}</span>
        </div>
"""
        return ""

    def _render_certifications(self, certifications: list) -> str:
        if not certifications:
            return ""
        
        html = "<h2>Certifications</h2><ul>"
        for cert in certifications:
            html += f"<li>{cert}</li>"
        html += "</ul>"
        return html

    def _render_technical_specs(self, specs: dict) -> str:
        if not specs:
            return ""
        
        html = "<h2>Technical Specifications</h2>"
        for key, value in specs.items():
            html += self._render_field(key.replace("_", " ").title(), str(value))
        return html

    def save_html_to_storage(
        self,
        html_content: str,
        document_id: str,
        document_name: str
    ) -> str:
        try:
            blob_name = f"{document_id}/specification.html"
            
            html_bytes = html_content.encode('utf-8')
            
            url = storage_service.upload_blob(
                container_name=settings.azure_storage_container_processed,
                blob_name=blob_name,
                data=html_bytes,
                content_type="text/html",
                metadata={
                    "document_id": document_id,
                    "document_name": document_name,
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(f"HTML saved to storage: {blob_name}")
            return url
            
        except Exception as e:
            self.logger.error(f"Failed to save HTML to storage: {str(e)}")
            raise

    def save_json_to_storage(
        self,
        processed_doc: ProcessedDocument
    ) -> str:
        try:
            blob_name = f"{processed_doc.document_id}/specification.json"
            
            json_data = processed_doc.model_dump_json(indent=2)
            json_bytes = json_data.encode('utf-8')
            
            url = storage_service.upload_blob(
                container_name=settings.azure_storage_container_processed,
                blob_name=blob_name,
                data=json_bytes,
                content_type="application/json",
                metadata={
                    "document_id": processed_doc.document_id,
                    "document_name": processed_doc.document_name
                }
            )
            
            self.logger.info(f"JSON saved to storage: {blob_name}")
            return url
            
        except Exception as e:
            self.logger.error(f"Failed to save JSON to storage: {str(e)}")
            raise


html_generator = HTMLGenerator()

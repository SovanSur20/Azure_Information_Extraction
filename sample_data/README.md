# Sample Input Files

This directory contains sample OEM technical documents for testing the multimodal RAG pipeline.

## File Types Supported

- ✅ PDF documents
- ✅ Images (PNG, JPG, TIFF)
- ✅ Scanned documents
- ✅ Multi-page technical specifications

## Sample Documents Included

1. **sample_oem_specification.txt** - Text-based specification (for creating test PDFs)
2. **sample_part_datasheet.txt** - Detailed part datasheet example
3. **sample_technical_drawing.txt** - Technical drawing specifications
4. **test_queries.json** - Sample queries for testing RAG retrieval

## How to Use

### Option 1: Upload to Azure Blob Storage

```bash
az storage blob upload \
  --account-name <your-storage-account> \
  --container-name raw-documents \
  --name sample_oem_specification.pdf \
  --file sample_data/sample_oem_specification.pdf \
  --auth-mode login
```

### Option 2: Test Locally

```python
from src.pipeline.orchestrator import pipeline_orchestrator

# Process a sample document
result = await pipeline_orchestrator.process_document(
    blob_name="sample_oem_specification.pdf",
    container_name="raw-documents",
    document_id="test-001"
)
```

## Expected Output

After processing, you should see:
- HTML specification in `processed-documents/<document_id>/specification.html`
- JSON data in `processed-documents/<document_id>/specification.json`
- Logs in SQL Database
- Metrics in Application Insights

## Creating Your Own Test Files

Convert the `.txt` samples to PDF using:
- Microsoft Word → Save as PDF
- LibreOffice → Export as PDF
- Online converters (e.g., https://www.ilovepdf.com/txt_to_pdf)

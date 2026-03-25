# 🚀 Enterprise Multimodal RAG Pipeline for OEM Document Processing

[![Azure](https://img.shields.io/badge/Azure-0078D4?style=flat&logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com)
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Production-grade multimodal RAG system for extracting structured information from OEM technical documents with **enterprise security (Azure AD)**, **centralized logging**, and **automated evaluation**.

---

## 🏗️ Architecture Overview

```
┌─────────────────┐
│  Azure Blob     │  ← Document Upload
│  Storage        │
└────────┬────────┘
         │ (Event Trigger)
         ▼
┌─────────────────┐
│ Azure Function  │  ← Managed Identity
│ (Orchestrator)  │
└────────┬────────┘
         │
         ├──→ Document Intelligence (OCR)
         ├──→ Chunking Layer
         ├──→ Azure OpenAI (Extraction)
         ├──→ Azure AI Search (Indexing)
         ├──→ Aggregation & Validation
         ├──→ Evaluation (RAGAS)
         └──→ HTML/JSON Output
              │
              ├──→ Application Insights (Real-time)
              └──→ SQL Database (Persistent Logs)
```

---

## ✨ Key Features

### 🔐 Enterprise Security
- **Azure AD Authentication** with Managed Identity
- **RBAC** for all Azure services
- **No secrets/keys** in code
- **Audit trail** for compliance

### 📊 Centralized Logging
- **Application Insights** for real-time monitoring
- **SQL Database** for persistent logs
- **Multi-level tracking**: Pipeline → Chunk → Field
- **Cost monitoring** and **retry tracking**

### 🎯 Evaluation Framework
- **RAGAS** integration for RAG quality
- **Field-level accuracy** tracking
- **Confidence scoring** at every stage
- **Automated validation** with suggestions

### 🔄 Multimodal Processing
- **OCR** with Azure Document Intelligence
- **Text + Table + Image** extraction
- **Hybrid search** (keyword + semantic)
- **GPT-4 Vision** for complex layouts

---

## 📋 Prerequisites

- **Azure Subscription** with appropriate permissions
- **Azure CLI** installed and configured
- **Python 3.11+**
- **Azure Functions Core Tools** v4

---

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd Azure_Information_Extraction
```

### 2. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Azure resource details
```

### 4. Deploy Azure Resources

**Linux/Mac:**
```bash
chmod +x deployment/setup_azure_resources.sh
./deployment/setup_azure_resources.sh
```

**Windows:**
```powershell
.\deployment\setup_azure_resources.ps1
```

### 5. Run Database Migrations

```bash
alembic upgrade head
```

### 6. Deploy Function App

```bash
func azure functionapp publish <your-function-app-name>
```

### 7. Create Search Index

```bash
curl -X POST https://<your-function-app>.azurewebsites.net/api/create-index
```

---

## 📁 Project Structure

```
Azure_Information_Extraction/
├── src/
│   ├── auth/                    # Azure AD authentication
│   │   └── azure_auth.py        # Managed identity manager
│   ├── config/                  # Configuration management
│   │   └── settings.py          # Pydantic settings
│   ├── logging/                 # Centralized logging
│   │   ├── models.py            # SQLAlchemy models
│   │   └── logger.py            # Logger implementation
│   ├── models/                  # Data schemas
│   │   └── schemas.py           # Pydantic models
│   ├── services/                # Core services
│   │   ├── storage_service.py   # Blob storage operations
│   │   ├── document_intelligence_service.py  # OCR
│   │   ├── chunking_service.py  # Document chunking
│   │   ├── openai_service.py    # LLM extraction
│   │   ├── search_service.py    # Hybrid search
│   │   └── validation_service.py # Data validation
│   ├── pipeline/                # Pipeline orchestration
│   │   └── orchestrator.py      # Main pipeline logic
│   ├── evaluation/              # Evaluation framework
│   │   └── evaluator.py         # RAGAS integration
│   └── templates/               # HTML generation
│       ├── html_generator.py    # Template renderer
│       └── templates/
│           └── specification_template.html
├── deployment/                  # Deployment scripts
│   ├── setup_azure_resources.sh
│   └── setup_azure_resources.ps1
├── alembic/                     # Database migrations
│   └── versions/
│       └── 001_initial_schema.py
├── tests/                       # Unit tests
│   └── test_pipeline.py
├── function_app.py              # Azure Function entry point
├── requirements.txt             # Python dependencies
├── host.json                    # Function app configuration
└── README.md                    # This file
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_TENANT_ID` | Azure AD Tenant ID | ✅ |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID | ✅ |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account name | ✅ |
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Document Intelligence endpoint | ✅ |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | ✅ |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search endpoint | ✅ |
| `AZURE_SQL_SERVER` | SQL Server hostname | ✅ |
| `AZURE_SQL_DATABASE` | Database name | ✅ |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights connection | ✅ |
| `USE_MANAGED_IDENTITY` | Enable managed identity | ✅ |
| `CONFIDENCE_THRESHOLD` | Validation threshold (0-1) | ❌ (default: 0.85) |
| `ENABLE_EVALUATION` | Enable RAGAS evaluation | ❌ (default: true) |

---

## 📊 Logging Schema

### Pipeline Logs
```json
{
  "document_id": "doc123",
  "stage": "extraction",
  "status": "success",
  "latency_ms": 1200,
  "confidence_score": 0.91,
  "timestamp": "2024-03-25T10:00:00Z"
}
```

### Field Logs
```json
{
  "document_id": "doc123",
  "field_name": "dimensions",
  "field_value": "120x45x15 mm",
  "confidence": 0.92,
  "source_chunks": ["chunk_3", "chunk_8"],
  "validation_status": "valid"
}
```

### Cost Logs
```json
{
  "document_id": "doc123",
  "service": "azure_openai",
  "operation": "extraction",
  "tokens_used": 2500,
  "estimated_cost_usd": 0.075
}
```

---

## 🧪 Testing

### Run Unit Tests

```bash
pytest tests/ -v --cov=src
```

### Run Specific Test

```bash
pytest tests/test_pipeline.py::TestValidationService -v
```

---

## 📈 Monitoring & Observability

### Application Insights Queries

**Pipeline Performance:**
```kusto
customEvents
| where name startswith "Pipeline_"
| summarize avg(customMeasurements.latency_ms) by name
| order by avg_customMeasurements_latency_ms desc
```

**Field Confidence Distribution:**
```kusto
customMetrics
| where name startswith "field_confidence_"
| summarize avg(value), percentile(value, 95) by name
```

### SQL Queries

**Failed Documents:**
```sql
SELECT document_id, stage, error_message, timestamp
FROM pipeline_logs
WHERE status = 'failed'
ORDER BY timestamp DESC;
```

**Cost Analysis:**
```sql
SELECT service, SUM(estimated_cost_usd) as total_cost
FROM cost_logs
WHERE timestamp >= DATEADD(day, -7, GETDATE())
GROUP BY service;
```

---

## 🔄 API Endpoints

### Process Document (Blob Trigger)
- **Trigger:** Blob upload to `raw-documents` container
- **Output:** HTML + JSON in `processed-documents` container

### Query Document
```bash
POST /api/query
Content-Type: application/json

{
  "document_id": "doc123",
  "query": "What are the dimensions?",
  "top_k": 5
}
```

### Health Check
```bash
GET /api/health
```

### Create Search Index
```bash
POST /api/create-index
```

---

## 🎯 Evaluation Metrics

### Extraction Quality
- **Precision**: Accuracy of extracted fields
- **Recall**: Completeness of extraction
- **F1 Score**: Harmonic mean of precision/recall
- **Field-level Accuracy**: Per-field confidence

### RAG Quality (RAGAS)
- **Faithfulness**: Answer grounded in context
- **Answer Relevancy**: Relevance to question
- **Context Precision**: Quality of retrieved chunks
- **Context Recall**: Coverage of relevant information

---

## 🔒 Security Best Practices

1. **Use Managed Identity** for all Azure services
2. **Enable Azure AD authentication** for SQL Database
3. **Restrict network access** with Private Endpoints
4. **Enable diagnostic logging** for all resources
5. **Implement RBAC** with least privilege
6. **Rotate credentials** regularly (if using keys)
7. **Enable Azure Defender** for threat protection

---

## 🐛 Troubleshooting

### Common Issues

**Issue:** Authentication failed
```bash
# Solution: Ensure managed identity has correct RBAC roles
az role assignment list --assignee <principal-id>
```

**Issue:** Database connection timeout
```bash
# Solution: Check firewall rules and enable Azure services access
az sql server firewall-rule create --resource-group <rg> --server <server> --name AllowAzure --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
```

**Issue:** Search index not found
```bash
# Solution: Create index via API
curl -X POST https://<function-app>.azurewebsites.net/api/create-index
```

---

## 📚 Additional Resources

- [Azure Functions Documentation](https://docs.microsoft.com/azure/azure-functions/)
- [Azure Document Intelligence](https://docs.microsoft.com/azure/applied-ai-services/form-recognizer/)
- [Azure OpenAI Service](https://docs.microsoft.com/azure/cognitive-services/openai/)
- [Azure AI Search](https://docs.microsoft.com/azure/search/)
- [RAGAS Framework](https://docs.ragas.io/)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📧 Support

For issues and questions:
- Create an issue in the repository
- Contact: support@example.com

---

**Built with ❤️ using Azure AI Services**

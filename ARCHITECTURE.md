# 🏗️ Architecture Documentation

## System Overview

This enterprise-grade multimodal RAG pipeline processes OEM technical documents with production-level security, observability, and evaluation capabilities.

---

## 🔄 Data Flow

### 1. Document Ingestion
```
User uploads PDF → Azure Blob Storage (raw-documents)
                 ↓
         Blob Trigger Event
                 ↓
         Azure Function Activated
```

### 2. Processing Pipeline
```
Azure Function (Managed Identity)
    ↓
[1] Document Intelligence (OCR)
    • Layout analysis
    • Text extraction
    • Table detection
    • Page segmentation
    ↓
[2] Chunking Layer
    • Token-based splitting
    • Overlap management
    • Semantic boundaries
    ↓
[3] Multimodal Extraction (GPT-4 Vision)
    • Field extraction per chunk
    • Confidence scoring
    • Metadata enrichment
    ↓
[4] Indexing (Azure AI Search)
    • Embedding generation
    • Vector indexing
    • Keyword indexing
    • Hybrid search setup
    ↓
[5] Aggregation (GPT-4)
    • Field consolidation
    • Conflict resolution
    • Specification building
    ↓
[6] Validation
    • Completeness check
    • Confidence analysis
    • Data quality validation
    ↓
[7] Evaluation (RAGAS)
    • Precision/Recall/F1
    • Field-level accuracy
    • RAG quality metrics
    ↓
[8] Output Generation
    • HTML template rendering
    • JSON serialization
    • Storage upload
```

### 3. Logging & Monitoring
```
Every Stage
    ↓
Application Insights (Real-time)
    • Latency tracking
    • Dependency monitoring
    • Exception tracking
    ↓
SQL Database (Persistent)
    • Pipeline logs
    • Chunk logs
    • Field logs
    • Cost logs
    • Audit logs
```

---

## 🔐 Security Architecture

### Azure AD Integration

```
┌─────────────────────────────────────┐
│     Azure Function App              │
│  (System Assigned Managed Identity) │
└──────────────┬──────────────────────┘
               │
               ├──→ Azure AD Token Request
               │
               ▼
┌─────────────────────────────────────┐
│      Microsoft Entra ID             │
│   (Token Provider)                  │
└──────────────┬──────────────────────┘
               │
               ├──→ Token (Storage)
               ├──→ Token (Cognitive Services)
               ├──→ Token (Search)
               └──→ Token (SQL)
               │
               ▼
┌─────────────────────────────────────┐
│      Azure Resources                │
│  • Blob Storage (RBAC)              │
│  • Document Intelligence (RBAC)     │
│  • Azure OpenAI (RBAC)              │
│  • Azure AI Search (RBAC)           │
│  • SQL Database (Azure AD Auth)     │
└─────────────────────────────────────┘
```

### RBAC Roles

| Service | Role | Purpose |
|---------|------|---------|
| Blob Storage | Storage Blob Data Contributor | Read/Write blobs |
| Document Intelligence | Cognitive Services User | OCR operations |
| Azure OpenAI | Cognitive Services User | LLM inference |
| Azure AI Search | Search Index Data Contributor | Index management |
| SQL Database | db_datareader, db_datawriter | Logging operations |

---

## 📊 Logging Architecture

### Multi-Tier Logging

```
┌─────────────────────────────────────┐
│        Application Layer            │
│  (Pipeline, Services, Functions)    │
└──────────────┬──────────────────────┘
               │
               ├──→ Python Logging
               │    (Console + Azure Handler)
               │
               ▼
┌─────────────────────────────────────┐
│    Application Insights             │
│  • Real-time telemetry              │
│  • Custom events                    │
│  • Dependencies                     │
│  • Metrics                          │
└─────────────────────────────────────┘
               │
               ├──→ Kusto Queries
               │    (Analytics)
               │
               ▼
┌─────────────────────────────────────┐
│      Centralized Logger             │
│  (src/logging/logger.py)            │
└──────────────┬──────────────────────┘
               │
               ├──→ Pipeline Logs
               ├──→ Chunk Logs
               ├──→ Field Logs
               ├──→ Retry Logs
               ├──→ Cost Logs
               └──→ Audit Logs
               │
               ▼
┌─────────────────────────────────────┐
│      SQL Database                   │
│  • Persistent storage               │
│  • Historical analysis              │
│  • Compliance records               │
└─────────────────────────────────────┘
```

### Log Levels

1. **Pipeline Level**: Document-wide tracking
   - Stage transitions
   - Overall latency
   - Success/failure status

2. **Chunk Level**: Granular processing
   - Individual chunk processing
   - OCR confidence
   - Extraction results

3. **Field Level**: Data quality
   - Field extraction confidence
   - Validation status
   - Source attribution

---

## 🎯 Evaluation Framework

### RAGAS Integration

```
Processed Document
    ↓
Evaluation Trigger (10% sample rate)
    ↓
┌─────────────────────────────────────┐
│      Ground Truth Available?        │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
       YES           NO
        │             │
        ▼             ▼
   [With GT]     [Without GT]
        │             │
        ├─ Precision  ├─ Completeness
        ├─ Recall     ├─ Quality Score
        ├─ F1 Score   └─ Confidence
        └─ Accuracy
        │
        ▼
┌─────────────────────────────────────┐
│      Evaluation Metrics             │
│  • Stored in metadata               │
│  • Logged to database               │
│  • Tracked in App Insights          │
└─────────────────────────────────────┘
```

### RAG Quality Metrics

```
User Query
    ↓
Hybrid Search (Retrieval)
    ↓
Retrieved Contexts
    ↓
LLM Answer Generation
    ↓
┌─────────────────────────────────────┐
│      RAGAS Evaluation               │
│  • Faithfulness                     │
│  • Answer Relevancy                 │
│  • Context Precision                │
│  • Context Recall (if GT)           │
└─────────────────────────────────────┘
```

---

## 🔍 Search Architecture

### Hybrid Search Strategy

```
User Query
    ↓
┌─────────────────────────────────────┐
│      Query Processing               │
│  • Text normalization               │
│  • Embedding generation             │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
   Keyword        Semantic
   Search         Search
        │             │
        ▼             ▼
   BM25 Scoring   Vector Similarity
        │             │
        └──────┬──────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Score Fusion                   │
│  • Reciprocal Rank Fusion           │
│  • Confidence filtering             │
└──────────────┬──────────────────────┘
               │
               ▼
        Top-K Results
```

### Index Schema

```json
{
  "chunk_id": "string (key)",
  "document_id": "string (filterable)",
  "content": "string (searchable)",
  "chunk_type": "string (filterable)",
  "page_number": "int (filterable, sortable)",
  "content_vector": "float[] (3072 dimensions)",
  "confidence": "float (filterable, sortable)",
  "metadata": "string (searchable)"
}
```

---

## 🧠 Extraction Strategy

### Multimodal Approach

```
Document Chunk
    ↓
┌─────────────────────────────────────┐
│      Chunk Type Detection           │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┬──────────┐
        │             │          │
      TEXT         TABLE      IMAGE
        │             │          │
        ▼             ▼          ▼
   GPT-4 Text    GPT-4 Table  GPT-4 Vision
   Extraction    Parsing      Analysis
        │             │          │
        └──────┬──────┴──────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Field Extraction               │
│  • part_number                      │
│  • material                         │
│  • dimensions                       │
│  • specifications                   │
│  • confidence scores                │
└─────────────────────────────────────┘
```

### Aggregation Logic

```
All Extracted Fields
    ↓
┌─────────────────────────────────────┐
│      Field Grouping                 │
│  Group by field_name                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Conflict Resolution            │
│  • Highest confidence wins          │
│  • Context-based selection          │
│  • Value consolidation              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Specification Building         │
│  • OEMPartSpecification object      │
│  • Metadata enrichment              │
└─────────────────────────────────────┘
```

---

## 📈 Performance Optimization

### Async Processing

```python
# Pipeline uses async/await for I/O operations
async def process_document():
    # Parallel chunk processing
    tasks = [extract_from_chunk(chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks)
```

### Caching Strategy

- **Token encoding**: Cached tiktoken encoder
- **Credentials**: Singleton pattern for auth manager
- **Database connections**: Connection pooling (5-10 connections)

### Retry Logic

```
Operation Failed
    ↓
Retry Count < Max (3)?
    │
    ├─ YES → Exponential Backoff (4s, 8s, 16s)
    │         ↓
    │    Retry Operation
    │
    └─ NO → Log Failure & Raise Exception
```

---

## 🚀 Scalability Considerations

### Horizontal Scaling

- **Azure Functions**: Auto-scale based on queue depth
- **Consumption Plan**: Up to 200 instances
- **Premium Plan**: Pre-warmed instances for lower latency

### Database Optimization

- **Indexes**: Multi-column indexes on frequently queried fields
- **Partitioning**: Consider partitioning by date for large datasets
- **Archival**: Move old logs to cold storage

### Cost Optimization

- **Batch Processing**: Process multiple chunks in parallel
- **Token Optimization**: Minimize prompt tokens
- **Caching**: Cache embeddings for repeated content
- **Sampling**: Evaluate only 10% of documents by default

---

## 🔄 Disaster Recovery

### Backup Strategy

1. **Database**: Automated daily backups (7-day retention)
2. **Blob Storage**: Geo-redundant storage (GRS)
3. **Configuration**: Infrastructure as Code (ARM/Bicep)

### Recovery Procedures

```
Failure Detected
    ↓
1. Check Application Insights for root cause
2. Review SQL logs for data integrity
3. Restore from backup if needed
4. Replay failed documents from blob storage
5. Validate outputs
```

---

## 📊 Monitoring Dashboards

### Key Metrics

1. **Throughput**: Documents processed per hour
2. **Latency**: P50, P95, P99 processing times
3. **Success Rate**: % of successful extractions
4. **Cost**: Daily/monthly Azure spend
5. **Quality**: Average confidence scores

### Alerts

- Pipeline failure rate > 5%
- Average latency > 30 seconds
- Cost spike > 20% above baseline
- Database connection failures
- Low confidence scores (< 0.70)

---

## 🔧 Maintenance

### Regular Tasks

- **Weekly**: Review error logs and retry patterns
- **Monthly**: Analyze cost trends and optimize
- **Quarterly**: Update models and dependencies
- **Annually**: Security audit and compliance review

---

## 📚 Technology Stack

| Layer | Technology |
|-------|-----------|
| Compute | Azure Functions (Python 3.11) |
| Storage | Azure Blob Storage |
| Database | Azure SQL Database |
| OCR | Azure Document Intelligence |
| LLM | Azure OpenAI (GPT-4 Vision) |
| Search | Azure AI Search |
| Monitoring | Application Insights |
| Auth | Azure AD + Managed Identity |
| Evaluation | RAGAS Framework |
| Templating | Jinja2 |
| Testing | Pytest |

---

**Last Updated**: 2024-03-25  
**Version**: 1.0.0

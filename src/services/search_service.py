from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)
from azure.core.credentials import AzureKeyCredential
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from src.config.settings import settings
from src.auth.azure_auth import auth_manager
from src.logging.logger import centralized_logger
from src.models.schemas import DocumentChunk, SearchQuery, SearchResult, ChunkType
from src.services.openai_service import openai_service


class SearchService:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._initialize_clients()

    def _initialize_clients(self) -> None:
        try:
            credential = auth_manager.get_credential()
            
            self.index_client = SearchIndexClient(
                endpoint=settings.azure_search_endpoint,
                credential=credential
            )
            
            self.search_client = SearchClient(
                endpoint=settings.azure_search_endpoint,
                index_name=settings.azure_search_index_name,
                credential=credential
            )
            
            self.logger.info("Search service initialized with Azure AD authentication")
        except Exception as e:
            self.logger.error(f"Failed to initialize search service: {str(e)}")
            raise

    def create_or_update_index(self) -> None:
        try:
            fields = [
                SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True),
                SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
                SimpleField(name="chunk_type", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
                SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, sortable=True),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=3072,
                    vector_search_profile_name="default-vector-profile"
                ),
                SimpleField(name="confidence", type=SearchFieldDataType.Double, filterable=True, sortable=True),
                SearchableField(name="metadata", type=SearchFieldDataType.String),
            ]
            
            vector_search = VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="default-vector-profile",
                        algorithm_configuration_name="hnsw-config"
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(name="hnsw-config")
                ]
            )
            
            index = SearchIndex(
                name=settings.azure_search_index_name,
                fields=fields,
                vector_search=vector_search
            )
            
            self.index_client.create_or_update_index(index)
            self.logger.info(f"Search index '{settings.azure_search_index_name}' created/updated")
            
        except Exception as e:
            self.logger.error(f"Failed to create/update index: {str(e)}")
            raise

    def index_chunks(
        self,
        chunks: List[DocumentChunk],
        document_id: str,
        document_name: str
    ) -> None:
        try:
            start_time = self._get_current_time_ms()
            
            self.logger.info(f"Indexing {len(chunks)} chunks for document: {document_name}")
            
            texts = [chunk.content for chunk in chunks]
            embeddings = openai_service.generate_embeddings(texts)
            
            documents = []
            for chunk, embedding in zip(chunks, embeddings):
                doc = {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "chunk_type": chunk.chunk_type.value,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "content_vector": embedding,
                    "confidence": chunk.confidence,
                    "metadata": str(chunk.metadata)
                }
                documents.append(doc)
            
            result = self.search_client.upload_documents(documents=documents)
            
            duration = self._get_current_time_ms() - start_time
            
            centralized_logger.log_pipeline(
                document_id=document_id,
                document_name=document_name,
                stage="indexing",
                status="success",
                latency_ms=duration,
                metadata={"chunks_indexed": len(chunks)}
            )
            
            centralized_logger.log_cost(
                document_id=document_id,
                service="azure_search",
                operation="index_documents",
                queries_executed=len(chunks),
                estimated_cost_usd=len(chunks) * 0.001
            )
            
            self.logger.info(f"Successfully indexed {len(chunks)} chunks")
            
        except Exception as e:
            self.logger.error(f"Indexing failed: {str(e)}")
            centralized_logger.log_pipeline(
                document_id=document_id,
                document_name=document_name,
                stage="indexing",
                status="failed",
                error_message=str(e)
            )
            raise

    def hybrid_search(
        self,
        query: SearchQuery,
        document_id: Optional[str] = None
    ) -> List[SearchResult]:
        try:
            start_time = self._get_current_time_ms()
            
            query_embedding = openai_service.generate_embeddings([query.query])[0]
            
            filter_expr = None
            if document_id:
                filter_expr = f"document_id eq '{document_id}'"
            
            if query.filters:
                additional_filters = " and ".join([
                    f"{k} eq '{v}'" for k, v in query.filters.items()
                ])
                filter_expr = f"{filter_expr} and {additional_filters}" if filter_expr else additional_filters
            
            results = self.search_client.search(
                search_text=query.query if query.include_keyword else None,
                vector_queries=[{
                    "vector": query_embedding,
                    "k_nearest_neighbors": query.top_k,
                    "fields": "content_vector"
                }] if query.include_semantic else None,
                filter=filter_expr,
                top=query.top_k,
                select=["chunk_id", "document_id", "content", "chunk_type", "page_number", "confidence", "metadata"]
            )
            
            search_results = []
            for result in results:
                if result.get("@search.score", 0) >= query.min_confidence:
                    search_result = SearchResult(
                        chunk_id=result["chunk_id"],
                        document_id=result["document_id"],
                        content=result["content"],
                        score=result.get("@search.score", 0.0),
                        chunk_type=ChunkType(result["chunk_type"]),
                        metadata={
                            "page_number": result.get("page_number"),
                            "confidence": result.get("confidence")
                        }
                    )
                    search_results.append(search_result)
            
            duration = self._get_current_time_ms() - start_time
            
            centralized_logger.track_dependency(
                name="Azure AI Search",
                data=f"Hybrid search: {query.query}",
                duration=duration,
                success=True
            )
            
            self.logger.info(f"Hybrid search returned {len(search_results)} results")
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {str(e)}")
            raise

    def delete_document_chunks(self, document_id: str) -> None:
        try:
            filter_expr = f"document_id eq '{document_id}'"
            results = self.search_client.search(
                search_text="*",
                filter=filter_expr,
                select=["chunk_id"]
            )
            
            chunk_ids = [{"chunk_id": r["chunk_id"]} for r in results]
            
            if chunk_ids:
                self.search_client.delete_documents(documents=chunk_ids)
                self.logger.info(f"Deleted {len(chunk_ids)} chunks for document {document_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to delete document chunks: {str(e)}")
            raise

    @staticmethod
    def _get_current_time_ms() -> int:
        return int(datetime.utcnow().timestamp() * 1000)


search_service = SearchService()

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    azure_tenant_id: str
    azure_subscription_id: str
    azure_resource_group: str

    azure_storage_account_name: str
    azure_storage_container_raw: str = "raw-documents"
    azure_storage_container_processed: str = "processed-documents"

    azure_document_intelligence_endpoint: str
    
    azure_openai_endpoint: str
    azure_openai_deployment_gpt4: str = "gpt-4-vision-preview"
    azure_openai_deployment_embedding: str = "text-embedding-3-large"
    azure_openai_api_version: str = "2024-02-15-preview"

    azure_search_endpoint: str
    azure_search_index_name: str = "oem-documents"

    azure_sql_server: str
    azure_sql_database: str
    azure_sql_driver: str = "ODBC Driver 18 for SQL Server"

    applicationinsights_connection_string: str

    use_managed_identity: bool = True
    environment: Environment = Environment.PRODUCTION
    log_level: LogLevel = LogLevel.INFO
    
    max_retries: int = 3
    chunk_size: int = 1000
    chunk_overlap: int = 200
    confidence_threshold: float = 0.85
    
    batch_size: int = 10
    max_concurrent_requests: int = 5
    request_timeout: int = 300
    
    enable_evaluation: bool = True
    evaluation_sample_rate: float = 0.1

    @property
    def storage_account_url(self) -> str:
        return f"https://{self.azure_storage_account_name}.blob.core.windows.net"

    @property
    def sql_connection_string(self) -> str:
        return (
            f"Driver={{{self.azure_sql_driver}}};"
            f"Server=tcp:{self.azure_sql_server},1433;"
            f"Database={self.azure_sql_database};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )


settings = Settings()

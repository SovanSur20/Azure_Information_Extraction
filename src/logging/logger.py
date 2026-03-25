import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime
from opencensus.ext.azure.log_exporter import AzureLogHandler
from applicationinsights import TelemetryClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import pyodbc

from src.config.settings import settings
from src.auth.azure_auth import auth_manager
from src.logging.models import (
    Base, PipelineLog, ChunkLog, FieldLog, RetryLog, CostLog, AuditLog,
    PipelineLogSchema, ChunkLogSchema, FieldLogSchema
)


class CentralizedLogger:
    _instance: Optional['CentralizedLogger'] = None
    _engine = None
    _session_factory = None
    _telemetry_client: Optional[TelemetryClient] = None

    def __new__(cls) -> 'CentralizedLogger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, '_initialized'):
            self._setup_logging()
            self._setup_database()
            self._setup_application_insights()
            self._initialized = True

    def _setup_logging(self) -> None:
        self.logger = logging.getLogger("multimodal_rag")
        self.logger.setLevel(getattr(logging, settings.log_level.value))
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        try:
            azure_handler = AzureLogHandler(
                connection_string=settings.applicationinsights_connection_string
            )
            azure_handler.setLevel(logging.INFO)
            self.logger.addHandler(azure_handler)
            self.logger.info("Azure Application Insights logging enabled")
        except Exception as e:
            self.logger.warning(f"Failed to setup Azure logging: {str(e)}")

    def _setup_database(self) -> None:
        try:
            if settings.use_managed_identity:
                token = auth_manager.get_sql_token()
                connection_string = f"{settings.sql_connection_string}Authentication=ActiveDirectoryMsi;"
            else:
                connection_string = settings.sql_connection_string

            self._engine = create_engine(
                f"mssql+pyodbc:///?odbc_connect={connection_string}",
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )
            
            Base.metadata.create_all(self._engine)
            self._session_factory = sessionmaker(bind=self._engine)
            self.logger.info("Database connection established successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup database: {str(e)}")
            self._engine = None
            self._session_factory = None

    def _setup_application_insights(self) -> None:
        try:
            self._telemetry_client = TelemetryClient(
                settings.applicationinsights_connection_string
            )
            self.logger.info("Application Insights telemetry client initialized")
        except Exception as e:
            self.logger.warning(f"Failed to setup Application Insights client: {str(e)}")

    def get_session(self) -> Optional[Session]:
        if self._session_factory:
            return self._session_factory()
        return None

    def log_pipeline(
        self,
        document_id: str,
        document_name: str,
        stage: str,
        status: str,
        latency_ms: Optional[int] = None,
        confidence_score: Optional[float] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        log_data = PipelineLogSchema(
            document_id=document_id,
            document_name=document_name,
            stage=stage,
            status=status,
            timestamp=datetime.utcnow(),
            latency_ms=latency_ms,
            confidence_score=confidence_score,
            error_message=error_message,
            metadata=metadata
        )

        self.logger.info(
            f"Pipeline [{stage}] - Document: {document_id} - Status: {status} - "
            f"Latency: {latency_ms}ms - Confidence: {confidence_score}"
        )

        if self._telemetry_client:
            self._telemetry_client.track_event(
                f"Pipeline_{stage}",
                {
                    "document_id": document_id,
                    "status": status,
                    "confidence": confidence_score or 0.0
                },
                {"latency_ms": latency_ms or 0}
            )

        session = self.get_session()
        if session:
            try:
                pipeline_log = PipelineLog(**log_data.model_dump())
                session.add(pipeline_log)
                session.commit()
            except Exception as e:
                self.logger.error(f"Failed to write pipeline log to database: {str(e)}")
                session.rollback()
            finally:
                session.close()

    def log_chunk(
        self,
        document_id: str,
        chunk_id: str,
        chunk_index: int,
        chunk_type: str,
        extraction_confidence: Optional[float] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        log_data = ChunkLogSchema(
            document_id=document_id,
            chunk_id=chunk_id,
            chunk_index=chunk_index,
            chunk_type=chunk_type,
            extraction_confidence=extraction_confidence,
            timestamp=datetime.utcnow(),
            error_message=error_message,
            metadata=metadata
        )

        self.logger.debug(
            f"Chunk [{chunk_id}] - Type: {chunk_type} - Confidence: {extraction_confidence}"
        )

        session = self.get_session()
        if session:
            try:
                chunk_log = ChunkLog(**log_data.model_dump())
                session.add(chunk_log)
                session.commit()
            except Exception as e:
                self.logger.error(f"Failed to write chunk log to database: {str(e)}")
                session.rollback()
            finally:
                session.close()

    def log_field(
        self,
        document_id: str,
        field_name: str,
        field_value: Optional[str] = None,
        confidence: Optional[float] = None,
        source_chunks: Optional[list] = None,
        validation_status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        log_data = FieldLogSchema(
            document_id=document_id,
            field_name=field_name,
            field_value=field_value,
            confidence=confidence,
            source_chunks=source_chunks,
            timestamp=datetime.utcnow(),
            validation_status=validation_status,
            metadata=metadata
        )

        self.logger.info(
            f"Field [{field_name}] - Value: {field_value} - Confidence: {confidence} - "
            f"Validation: {validation_status}"
        )

        if self._telemetry_client and confidence:
            self._telemetry_client.track_metric(
                f"field_confidence_{field_name}",
                confidence
            )

        session = self.get_session()
        if session:
            try:
                field_log = FieldLog(**log_data.model_dump())
                session.add(field_log)
                session.commit()
            except Exception as e:
                self.logger.error(f"Failed to write field log to database: {str(e)}")
                session.rollback()
            finally:
                session.close()

    def log_retry(
        self,
        document_id: str,
        stage: str,
        retry_count: int,
        reason: str,
        success: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self.logger.warning(
            f"Retry [{stage}] - Document: {document_id} - Attempt: {retry_count} - "
            f"Reason: {reason}"
        )

        session = self.get_session()
        if session:
            try:
                retry_log = RetryLog(
                    document_id=document_id,
                    stage=stage,
                    retry_count=retry_count,
                    reason=reason,
                    timestamp=datetime.utcnow(),
                    success=success,
                    metadata=metadata
                )
                session.add(retry_log)
                session.commit()
            except Exception as e:
                self.logger.error(f"Failed to write retry log to database: {str(e)}")
                session.rollback()
            finally:
                session.close()

    def log_cost(
        self,
        document_id: str,
        service: str,
        operation: str,
        tokens_used: Optional[int] = None,
        pages_processed: Optional[int] = None,
        queries_executed: Optional[int] = None,
        estimated_cost_usd: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self.logger.info(
            f"Cost [{service}] - Operation: {operation} - Tokens: {tokens_used} - "
            f"Pages: {pages_processed} - Cost: ${estimated_cost_usd}"
        )

        if self._telemetry_client and estimated_cost_usd:
            self._telemetry_client.track_metric(
                f"cost_{service}_{operation}",
                estimated_cost_usd
            )

        session = self.get_session()
        if session:
            try:
                cost_log = CostLog(
                    document_id=document_id,
                    service=service,
                    operation=operation,
                    tokens_used=tokens_used,
                    pages_processed=pages_processed,
                    queries_executed=queries_executed,
                    estimated_cost_usd=estimated_cost_usd,
                    timestamp=datetime.utcnow(),
                    metadata=metadata
                )
                session.add(cost_log)
                session.commit()
            except Exception as e:
                self.logger.error(f"Failed to write cost log to database: {str(e)}")
                session.rollback()
            finally:
                session.close()

    def log_audit(
        self,
        document_id: str,
        action: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        template_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self.logger.info(
            f"Audit [{action}] - Document: {document_id} - User: {user_email} - "
            f"Template: {template_version}"
        )

        session = self.get_session()
        if session:
            try:
                audit_log = AuditLog(
                    document_id=document_id,
                    action=action,
                    user_id=user_id,
                    user_email=user_email,
                    timestamp=datetime.utcnow(),
                    ip_address=ip_address,
                    template_version=template_version,
                    metadata=metadata
                )
                session.add(audit_log)
                session.commit()
            except Exception as e:
                self.logger.error(f"Failed to write audit log to database: {str(e)}")
                session.rollback()
            finally:
                session.close()

    def track_dependency(
        self,
        name: str,
        data: str,
        duration: int,
        success: bool = True,
        result_code: Optional[str] = None
    ) -> None:
        if self._telemetry_client:
            self._telemetry_client.track_dependency(
                name=name,
                data=data,
                duration=duration,
                success=success,
                result_code=result_code
            )

    def flush(self) -> None:
        if self._telemetry_client:
            self._telemetry_client.flush()


centralized_logger = CentralizedLogger()

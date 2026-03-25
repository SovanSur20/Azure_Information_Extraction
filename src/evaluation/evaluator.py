from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from datasets import Dataset

from src.config.settings import settings
from src.auth.azure_auth import auth_manager
from src.logging.logger import centralized_logger
from src.models.schemas import (
    OEMPartSpecification,
    ProcessedDocument,
    EvaluationMetrics,
    ExtractedField
)


class PipelineEvaluator:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._initialize_ragas()

    def _initialize_ragas(self) -> None:
        try:
            token_provider = lambda: auth_manager.get_cognitive_services_token()
            
            self.llm = AzureChatOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
                azure_deployment=settings.azure_openai_deployment_gpt4,
                azure_ad_token_provider=token_provider
            )
            
            self.embeddings = AzureOpenAIEmbeddings(
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
                azure_deployment=settings.azure_openai_deployment_embedding,
                azure_ad_token_provider=token_provider
            )
            
            self.logger.info("RAGAS evaluation framework initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize RAGAS: {str(e)}")

    def evaluate_extraction(
        self,
        processed_doc: ProcessedDocument,
        ground_truth: Optional[Dict[str, Any]] = None
    ) -> EvaluationMetrics:
        try:
            start_time = self._get_current_time_ms()
            
            self.logger.info(f"Evaluating extraction for document: {processed_doc.document_id}")
            
            if ground_truth:
                metrics = self._evaluate_with_ground_truth(processed_doc, ground_truth)
            else:
                metrics = self._evaluate_without_ground_truth(processed_doc)
            
            duration = self._get_current_time_ms() - start_time
            
            centralized_logger.log_pipeline(
                document_id=processed_doc.document_id,
                document_name=processed_doc.document_name,
                stage="evaluation",
                status="success",
                latency_ms=duration,
                confidence_score=metrics.f1_score,
                metadata={
                    "precision": metrics.precision,
                    "recall": metrics.recall,
                    "accuracy": metrics.accuracy
                }
            )
            
            self._log_evaluation_results(processed_doc.document_id, metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Evaluation failed: {str(e)}")
            centralized_logger.log_pipeline(
                document_id=processed_doc.document_id,
                document_name=processed_doc.document_name,
                stage="evaluation",
                status="failed",
                error_message=str(e)
            )
            raise

    def _evaluate_with_ground_truth(
        self,
        processed_doc: ProcessedDocument,
        ground_truth: Dict[str, Any]
    ) -> EvaluationMetrics:
        spec = processed_doc.specification
        
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        extraction_accuracy = {}
        
        for field_name, expected_value in ground_truth.items():
            extracted_value = getattr(spec, field_name, None)
            
            if expected_value is not None:
                if extracted_value is not None:
                    if self._values_match(extracted_value, expected_value):
                        true_positives += 1
                        extraction_accuracy[field_name] = 1.0
                    else:
                        false_positives += 1
                        extraction_accuracy[field_name] = self._calculate_similarity(
                            extracted_value, expected_value
                        )
                else:
                    false_negatives += 1
                    extraction_accuracy[field_name] = 0.0
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = true_positives / len(ground_truth) if ground_truth else 0.0
        
        return EvaluationMetrics(
            document_id=processed_doc.document_id,
            precision=round(precision, 3),
            recall=round(recall, 3),
            f1_score=round(f1_score, 3),
            accuracy=round(accuracy, 3),
            extraction_accuracy=extraction_accuracy,
            latency_ms=processed_doc.processing_time_ms or 0,
            cost_usd=processed_doc.total_cost_usd or 0.0
        )

    def _evaluate_without_ground_truth(
        self,
        processed_doc: ProcessedDocument
    ) -> EvaluationMetrics:
        validation = processed_doc.validation_result
        
        if not validation:
            return EvaluationMetrics(
                document_id=processed_doc.document_id,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                accuracy=0.0,
                latency_ms=processed_doc.processing_time_ms or 0,
                cost_usd=processed_doc.total_cost_usd or 0.0
            )
        
        completeness = 1.0 - (len(validation.missing_fields) * 0.1)
        quality = 1.0 - (len(validation.low_confidence_fields) * 0.05)
        
        estimated_accuracy = (completeness + quality + validation.confidence_score) / 3
        estimated_precision = validation.confidence_score
        estimated_recall = completeness
        estimated_f1 = 2 * (estimated_precision * estimated_recall) / (estimated_precision + estimated_recall) if (estimated_precision + estimated_recall) > 0 else 0.0
        
        return EvaluationMetrics(
            document_id=processed_doc.document_id,
            precision=round(estimated_precision, 3),
            recall=round(estimated_recall, 3),
            f1_score=round(estimated_f1, 3),
            accuracy=round(estimated_accuracy, 3),
            latency_ms=processed_doc.processing_time_ms or 0,
            cost_usd=processed_doc.total_cost_usd or 0.0
        )

    def evaluate_rag_quality(
        self,
        question: str,
        retrieved_contexts: List[str],
        generated_answer: str,
        ground_truth_answer: Optional[str] = None
    ) -> Dict[str, float]:
        try:
            data = {
                "question": [question],
                "contexts": [retrieved_contexts],
                "answer": [generated_answer]
            }
            
            if ground_truth_answer:
                data["ground_truth"] = [ground_truth_answer]
            
            dataset = Dataset.from_dict(data)
            
            metrics_to_use = [faithfulness, answer_relevancy, context_precision]
            if ground_truth_answer:
                metrics_to_use.append(context_recall)
            
            result = evaluate(
                dataset,
                metrics=metrics_to_use,
                llm=self.llm,
                embeddings=self.embeddings
            )
            
            scores = {
                "faithfulness": result["faithfulness"],
                "answer_relevancy": result["answer_relevancy"],
                "context_precision": result["context_precision"]
            }
            
            if ground_truth_answer:
                scores["context_recall"] = result["context_recall"]
            
            self.logger.info(f"RAG quality evaluation: {scores}")
            
            return scores
            
        except Exception as e:
            self.logger.error(f"RAG quality evaluation failed: {str(e)}")
            return {}

    def _values_match(self, extracted: Any, expected: Any) -> bool:
        if isinstance(extracted, str) and isinstance(expected, str):
            return extracted.lower().strip() == expected.lower().strip()
        return extracted == expected

    def _calculate_similarity(self, extracted: Any, expected: Any) -> float:
        if not isinstance(extracted, str) or not isinstance(expected, str):
            return 0.0
        
        extracted_lower = extracted.lower().strip()
        expected_lower = expected.lower().strip()
        
        if extracted_lower == expected_lower:
            return 1.0
        
        if extracted_lower in expected_lower or expected_lower in extracted_lower:
            return 0.7
        
        common_words = set(extracted_lower.split()) & set(expected_lower.split())
        if common_words:
            return len(common_words) / max(len(extracted_lower.split()), len(expected_lower.split()))
        
        return 0.0

    def _log_evaluation_results(self, document_id: str, metrics: EvaluationMetrics) -> None:
        self.logger.info(
            f"Evaluation Results for {document_id}:\n"
            f"  Precision: {metrics.precision:.3f}\n"
            f"  Recall: {metrics.recall:.3f}\n"
            f"  F1 Score: {metrics.f1_score:.3f}\n"
            f"  Accuracy: {metrics.accuracy:.3f}\n"
            f"  Latency: {metrics.latency_ms}ms\n"
            f"  Cost: ${metrics.cost_usd:.4f}"
        )
        
        if metrics.extraction_accuracy:
            self.logger.info("Field-level accuracy:")
            for field, accuracy in metrics.extraction_accuracy.items():
                self.logger.info(f"  {field}: {accuracy:.3f}")

    @staticmethod
    def _get_current_time_ms() -> int:
        return int(datetime.utcnow().timestamp() * 1000)


pipeline_evaluator = PipelineEvaluator()

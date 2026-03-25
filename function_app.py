import azure.functions as func
import logging
import json
import asyncio
from datetime import datetime
import uuid

from src.pipeline.orchestrator import pipeline_orchestrator
from src.templates.html_generator import html_generator
from src.logging.logger import centralized_logger
from src.config.settings import settings

app = func.FunctionApp()


@app.blob_trigger(
    arg_name="myblob",
    path=f"{settings.azure_storage_container_raw}/{{name}}",
    connection="AzureWebJobsStorage"
)
async def process_oem_document(myblob: func.InputStream):
    logging.info(
        f"Blob trigger function processing blob\n"
        f"Name: {myblob.name}\n"
        f"Blob Size: {myblob.length} bytes"
    )
    
    try:
        blob_name = myblob.name.split('/')[-1]
        document_id = str(uuid.uuid4())
        
        centralized_logger.logger.info(
            f"Processing document: {blob_name} with ID: {document_id}"
        )
        
        processed_doc = await pipeline_orchestrator.process_document(
            blob_name=blob_name,
            container_name=settings.azure_storage_container_raw,
            document_id=document_id,
            metadata={
                "blob_size": myblob.length,
                "trigger_time": datetime.utcnow().isoformat()
            }
        )
        
        html_content = html_generator.generate_specification_html(processed_doc)
        html_url = html_generator.save_html_to_storage(
            html_content=html_content,
            document_id=document_id,
            document_name=blob_name
        )
        
        json_url = html_generator.save_json_to_storage(processed_doc)
        
        centralized_logger.logger.info(
            f"Document processing completed successfully\n"
            f"HTML URL: {html_url}\n"
            f"JSON URL: {json_url}"
        )
        
        centralized_logger.flush()
        
    except Exception as e:
        centralized_logger.logger.error(f"Function execution failed: {str(e)}")
        centralized_logger.flush()
        raise


@app.route(route="query", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def query_document(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Query endpoint called")
    
    try:
        req_body = req.get_json()
        document_id = req_body.get("document_id")
        query = req_body.get("query")
        top_k = req_body.get("top_k", 5)
        
        if not document_id or not query:
            return func.HttpResponse(
                json.dumps({"error": "document_id and query are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        result = await pipeline_orchestrator.query_document(
            document_id=document_id,
            query=query,
            top_k=top_k
        )
        
        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Query failed: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        status_code=200,
        mimetype="application/json"
    )


@app.route(route="create-index", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def create_search_index(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Creating search index")
    
    try:
        from src.services.search_service import search_service
        search_service.create_or_update_index()
        
        return func.HttpResponse(
            json.dumps({"message": "Search index created successfully"}),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Index creation failed: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

from fastapi import APIRouter, HTTPException, Depends
from app.models.pydantic_models import QueryRequest, QueryResponse
from app.services.query_engine import process_query
from app.core.security import get_api_key

router = APIRouter()

@router.post("/query/", response_model=QueryResponse, dependencies=[Depends(get_api_key)])
async def handle_query(request: QueryRequest):
    """
    Handles user queries.
    Interprets natural language, maps to data extraction tasks (RAG or structured query).
    Returns response, which might include text, lists, or table data with download option.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    # Sanitize query (basic example, more robust needed for production)
    sanitized_query = request.query # Add actual sanitization if needed
    
    try:
        result = await process_query(sanitized_query, file_context=request.file_context)
        # The `result` dict from process_query should align with QueryResponse fields
        return QueryResponse(**result)
    except Exception as e:
        # Log the full error for debugging
        print(f"Error in handle_query: {e}") # Use proper logging
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

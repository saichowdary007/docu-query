from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
import os
import shutil
from typing import List, Dict
from app.services.file_parser import get_documents_from_file, parse_excel, parse_csv
from app.services.vector_store import add_documents_to_store, initialize_vector_store, remove_documents_by_source
from app.services.data_handler import dataframe_to_excel_bytes, dataframe_to_csv_bytes, load_structured_file, STRUCTURED_DATA_CACHE, execute_filtered_query
from app.core.config import settings
from app.core.security import get_api_key
from app.models.pydantic_models import FileProcessRequest

router = APIRouter()

# Ensure temp_uploads directory exists
os.makedirs(settings.TEMP_UPLOAD_FOLDER, exist_ok=True)

# Track uploaded structured files (filename: type)
# This could be stored more persistently if needed (e.g. Redis, DB)
UPLOADED_STRUCTURED_FILES = {}

# Track all uploaded files, including non-structured ones
UPLOADED_FILES = {}

def process_single_file_sync(file_path: str, filename: str):
    """Synchronous processing for a single file."""
    print(f"Processing {filename}...")
    try:
        documents = get_documents_from_file(file_path, filename)
        if documents:
            add_documents_to_store(documents)
            print(f"Successfully processed and added {filename} to vector store.")
            
            # Track the file in our global list
            _, ext = os.path.splitext(filename.lower())
            file_type = ext[1:] if ext else "unknown"
            UPLOADED_FILES[filename] = {"type": file_type, "path": file_path}
            
            # If it's a structured file, add to our tracker and cache it
            if ext in ['.csv', '.xls', '.xlsx']:
                data = load_structured_file(filename) # This also caches it
                if data is not None:
                    UPLOADED_STRUCTURED_FILES[filename] = "excel" if ext in ['.xls', '.xlsx'] else "csv"
                    print(f"Cached structured file: {filename}")
                else:
                    print(f"Warning: Could not load/cache structured file: {filename} after processing.")

        else:
            print(f"No documents extracted from {filename}. It might be empty or an unsupported type not yielding text.")
    except ValueError as e: # Catch unsupported file type error from parser
        print(f"Skipping {filename}: {e}")
    except Exception as e:
        print(f"Error processing {filename}: {e}")
    # Do not delete from temp_uploads immediately if it's a structured file needed for data_handler
    # Deletion strategy needs care: maybe delete non-structured, or on session end, or LRU cache for structured.
    # For now, keep them in temp_uploads.

@router.post("/upload/", dependencies=[Depends(get_api_key)])
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """
    Uploads multiple files. Files are processed in the background.
    Textual content is chunked, embedded, and stored in a vector database.
    Structured files (CSV, XLS, XLSX) have their summaries/structure embedded,
    and the actual data is cached for direct querying via data_handler.py.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files sent.")

    processed_files = []
    errors = []

    for file in files:
        # Sanitize filename (important!)
        original_filename = file.filename
        sanitized_filename = "".join(c if c.isalnum() or c in ['.', '-', '_'] else '_' for c in original_filename)
        if not sanitized_filename: # handle cases where filename becomes empty
            sanitized_filename = f"uploaded_file_{hash(original_filename)}" 

        file_path = os.path.join(settings.TEMP_UPLOAD_FOLDER, sanitized_filename)
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Add processing to background tasks
            # For simplicity, doing it sequentially here. For true background,
            # you'd use Celery or FastAPI's BackgroundTasks if tasks are short.
            # For potentially long processing, Celery is better.
            # Let's use a simple synchronous call for this example,
            # but acknowledge BackgroundTasks for production.
            # background_tasks.add_task(process_single_file_sync, file_path, sanitized_filename)
            process_single_file_sync(file_path, sanitized_filename) # Call directly for now
            
            processed_files.append(sanitized_filename)
        except Exception as e:
            errors.append({"filename": original_filename, "error": str(e)})
            # Clean up file if save failed mid-way or processing failed critically
            if os.path.exists(file_path):
                os.remove(file_path)
        finally:
            file.file.close()
            
    if errors:
        return {"message": "Files processed with some errors.", "processed": processed_files, "errors": errors}
    return {"message": "Files uploaded and processing started.", "processed_files": processed_files}

@router.delete("/delete/{filename}", dependencies=[Depends(get_api_key)])
async def delete_file(filename: str):
    """
    Delete a file from the system and remove its documents from the vector store.
    """
    if filename not in UPLOADED_FILES:
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")
    
    file_path = os.path.join(settings.TEMP_UPLOAD_FOLDER, filename)
    
    try:
        # Remove from vector store
        remove_documents_by_source(filename)
        
        # Remove from structured files tracking if it's there
        if filename in UPLOADED_STRUCTURED_FILES:
            del UPLOADED_STRUCTURED_FILES[filename]
            # Also remove from cache if present
            if filename in STRUCTURED_DATA_CACHE:
                del STRUCTURED_DATA_CACHE[filename]
        
        # Remove from our tracking
        del UPLOADED_FILES[filename]
        
        # Delete the actual file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return {"message": f"File '{filename}' successfully deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

@router.get("/uploaded-files", dependencies=[Depends(get_api_key)])
async def get_all_uploaded_files():
    """Lists all files known to the system."""
    # Load files currently in the temp directory if not in our tracker
    # This ensures we find files even after server restart
    temp_files = os.listdir(settings.TEMP_UPLOAD_FOLDER)
    
    # Add files that exist but aren't tracked
    for filename in temp_files:
        if filename not in UPLOADED_FILES and os.path.isfile(os.path.join(settings.TEMP_UPLOAD_FOLDER, filename)):
            file_path = os.path.join(settings.TEMP_UPLOAD_FOLDER, filename)
            _, ext = os.path.splitext(filename.lower())
            file_type = ext[1:] if ext else "unknown"
            UPLOADED_FILES[filename] = {"type": file_type, "path": file_path}
    
    # Remove files that no longer exist
    for filename in list(UPLOADED_FILES.keys()):
        if filename not in temp_files:
            del UPLOADED_FILES[filename]
    
    return {
        "files": [
            {
                "filename": filename,
                "type": info["type"],
                "is_structured": filename in UPLOADED_STRUCTURED_FILES
            }
            for filename, info in UPLOADED_FILES.items()
        ]
    }

@router.post("/download-processed-file/", dependencies=[Depends(get_api_key)])
async def download_processed_file(request: FileProcessRequest):
    """
    Allows downloading of data processed from structured files (e.g., filtered Excel).
    The `request.filename` should be the one provided in the chat response
    (e.g., "filtered_original_data.xlsx").
    The `request.original_filename` is the source file (e.g. "original_data.xlsx").
    The `request.query_params` and `request.sheet_name` are used to re-generate the data.
    """
    try:
        # Re-execute the query to get the DataFrame
        # This ensures data freshness and avoids storing large filtered files.
        df = execute_filtered_query(
            filename=request.original_filename,
            query_params=request.query_params, # This needs to be passed from frontend if dynamic
            sheet_name=request.sheet_name,
            drop_duplicates=request.drop_duplicates,
            subset=request.subset
        )
        
        # Apply column filtering if specified
        if request.return_columns:
            # Handle both string and list formats
            return_cols = request.return_columns
            if isinstance(return_cols, str):
                return_cols = [return_cols]
                
            # Check for invalid columns and filter them out
            valid_cols = [col for col in return_cols if col in df.columns]
            if valid_cols:
                df = df[valid_cols]
            # If no valid columns remain, use all columns (default behavior)

        _, ext = os.path.splitext(request.filename.lower())
        content_type = ""
        file_bytes = None

        if ext in [".xls", ".xlsx"]:
            file_bytes = dataframe_to_excel_bytes(df)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif ext == ".csv":
            file_bytes = dataframe_to_csv_bytes(df)
            content_type = "text/csv"
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type for download.")

        return FileResponse(
            path=file_bytes, # This won't work directly, BytesIO needs to be handled by StreamingResponse
            media_type=content_type,
            filename=request.filename,
            # For BytesIO, use StreamingResponse:
            # return StreamingResponse(file_bytes, media_type=content_type, headers={"Content-Disposition": f"attachment; filename={request.filename}"})
        )
    except ValueError as e: # From execute_filtered_query or data_handler
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error preparing file for download: {str(e)}")


# A new endpoint for downloading filtered files using StreamingResponse for BytesIO
@router.post("/download-filtered/", dependencies=[Depends(get_api_key)])
async def download_filtered_data(request: FileProcessRequest):
    try:
        # More verbose logging for debugging
        print(f"Download request received: {request.model_dump()}")
        
        # Check each required parameter separately for better error messages
        errors = []
        if not request.original_filename:
            errors.append("Missing 'original_filename' parameter")
        
        # Allow empty list/dict for query_params, but not None
        if request.query_params is None:
            errors.append("Missing 'query_params' parameter")
        
        if not request.filename_to_download:
            errors.append("Missing 'filename_to_download' parameter")
            
        if errors:
            error_msg = "; ".join(errors)
            print(f"Parameter validation failed: {error_msg}")
            raise HTTPException(status_code=400, detail=f"Missing parameters for download: {error_msg}")

        # Handle both single condition and list of conditions
        query_params = request.query_params
        
        # Print data type of query_params for debugging
        print(f"query_params type: {type(query_params)}, value: {query_params}")
        
        # Normalize query_params to be a list if it's a dict
        if isinstance(query_params, dict):
            query_params = [query_params]  # Wrap single dict in a list
        elif query_params is None:
            query_params = []  # Default to empty list
            
        try:
            df = execute_filtered_query(
                filename=request.original_filename,
                query_params=query_params,
                sheet_name=request.sheet_name,
                drop_duplicates=request.drop_duplicates,
                subset=request.subset
            )
        except Exception as e:
            print(f"Execute_filtered_query failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error filtering data: {str(e)}")
        
        # Apply column filtering if specified
        if request.return_columns:
            print(f"Return columns specified: {request.return_columns}")
            # Handle both string and list formats
            return_cols = request.return_columns
            if isinstance(return_cols, str):
                return_cols = [return_cols]
                
            # Check for invalid columns and filter them out
            missing_cols = [col for col in return_cols if col not in df.columns]
            if missing_cols:
                print(f"Warning: Requested columns not found in data: {missing_cols}")
                
            # Filter to only include valid columns
            valid_cols = [col for col in return_cols if col in df.columns]
            if valid_cols:
                print(f"Filtering columns to: {valid_cols}")
                df = df[valid_cols]
            else:
                print(f"No valid columns to filter, using all columns")
            # If no valid columns remain, use all columns (default behavior)
        else:
            print("No return_columns specified, using all columns")

        _, ext = os.path.splitext(request.filename_to_download.lower())
        file_bytes_io = None
        content_type = ""

        if ext in [".xls", ".xlsx"]:
            file_bytes_io = dataframe_to_excel_bytes(df)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif ext == ".csv":
            file_bytes_io = dataframe_to_csv_bytes(df)
            content_type = "text/csv"
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type for download.")

        return StreamingResponse(
            file_bytes_io,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={request.filename_to_download}"}
        )
    except ValueError as e:
        print(f"Download ValueError: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Download error: {e}, type: {type(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error preparing file for download: {str(e)}")


@router.get("/uploaded-structured-files", dependencies=[Depends(get_api_key)])
async def get_uploaded_structured_files_list():
    """Lists structured files known to the system (for context or UI)."""
    return {"structured_files": UPLOADED_STRUCTURED_FILES}

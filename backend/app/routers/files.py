from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
import os
import shutil
from typing import List, Dict
from sqlalchemy.orm import Session
from app.services.file_parser import get_documents_from_file, parse_excel, parse_csv
from app.services.vector_store import add_documents_to_store, initialize_vector_store, remove_documents_by_source
from app.services.data_handler import dataframe_to_excel_bytes, dataframe_to_csv_bytes, load_structured_file, STRUCTURED_DATA_CACHE, execute_filtered_query
from app.services.file_service import (
    create_file_record, get_user_files, get_file_by_filename, delete_file_record, 
    file_record_to_dict, ensure_user_upload_dir, save_uploaded_file, delete_file
)
from app.core.config import settings
from app.core.security import get_api_key, get_current_user
from app.core.database import get_db
from app.models.pydantic_models import FileProcessRequest
from app.models.user import TokenPayload

router = APIRouter()

# We'll deprecate these global dictionaries in favor of the database
# But keep them temporarily for backward compatibility
UPLOADED_STRUCTURED_FILES = {}
UPLOADED_FILES = {}

def process_single_file_sync(file_path: str, filename: str, user_id: str, db: Session):
    """Synchronous processing for a single file."""
    print(f"Processing {filename} for user {user_id}...")
    try:
        documents = get_documents_from_file(file_path, filename)
        if documents:
            # Add user_id to document metadata for future filtering
            for doc in documents:
                if not hasattr(doc, 'metadata'):
                    doc.metadata = {}
                doc.metadata['user_id'] = user_id
                
            add_documents_to_store(documents)
            print(f"Successfully processed and added {filename} to vector store.")
            
            # Extract file type and determine if it's structured
            _, ext = os.path.splitext(filename.lower())
            file_type = ext[1:] if ext else "unknown"
            is_structured = ext in ['.csv', '.xls', '.xlsx']
            structure_type = None
            
            # If it's a structured file, add to our tracker and cache it
            if is_structured:
                data = load_structured_file(file_path, filename) # Modified to pass file_path
                if data is not None:
                    structure_type = "excel" if ext in ['.xls', '.xlsx'] else "csv"
                    UPLOADED_STRUCTURED_FILES[filename] = structure_type
                    print(f"Cached structured file: {filename}")
                else:
                    print(f"Warning: Could not load/cache structured file: {filename} after processing.")
            
            # Create a file record in the database
            create_file_record(
                db=db,
                filename=filename,
                file_path=file_path,
                file_type=file_type,
                user_id=user_id,
                is_structured=is_structured,
                structure_type=structure_type
            )
            
            # Keep in the global dictionary for backward compatibility
            UPLOADED_FILES[filename] = {
                "type": file_type, 
                "path": file_path, 
                "user_id": user_id
            }
            
            return True
        else:
            print(f"No documents extracted from {filename}. It might be empty or an unsupported type not yielding text.")
            return False
    except ValueError as e: # Catch unsupported file type error from parser
        print(f"Skipping {filename}: {e}")
        return False
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return False

@router.post("/upload/")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user: TokenPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    Uploads multiple files. Files are processed in the background.
    Files are associated with the current user for isolation.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files sent.")

    processed_files = []
    errors = []
    
    # Ensure user's upload directory exists
    user_upload_dir = ensure_user_upload_dir(current_user.sub)

    for file in files:
        # Sanitize filename (important!)
        original_filename = file.filename
        sanitized_filename = "".join(c if c.isalnum() or c in ['.', '-', '_'] else '_' for c in original_filename)
        if not sanitized_filename: # handle cases where filename becomes empty
            sanitized_filename = f"uploaded_file_{hash(original_filename)}" 

        # Store in user-specific directory
        file_path = os.path.join(user_upload_dir, sanitized_filename)
        
        try:
            # Save the file
            if save_uploaded_file(file.file, file_path):
                # Process the file
                success = process_single_file_sync(file_path, sanitized_filename, current_user.sub, db)
                
                if success:
                    processed_files.append(sanitized_filename)
                else:
                    errors.append({"filename": original_filename, "error": "Failed to process file"})
            else:
                errors.append({"filename": original_filename, "error": "Failed to save file"})
        except Exception as e:
            errors.append({"filename": original_filename, "error": str(e)})
            # Clean up file if save failed mid-way or processing failed critically
            delete_file(file_path)
        finally:
            file.file.close()
            
    if errors:
        return {"message": "Files processed with some errors.", "processed": processed_files, "errors": errors}
    return {"message": "Files uploaded and processing started.", "processed_files": processed_files}

@router.delete("/delete/{filename}")
async def delete_file_endpoint(
    filename: str,
    current_user: TokenPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    Delete a file from the system and remove its documents from the vector store.
    """
    # Check if file exists for this user
    file_record = get_file_by_filename(db, filename, current_user.sub)
    
    if not file_record:
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found or you don't have permission to delete it.")
    
    try:
        # Remove from vector store (will need to be updated to filter by user_id)
        remove_documents_by_source(filename)
        
        # Remove from structured files tracking if it's there
        if filename in UPLOADED_STRUCTURED_FILES:
            del UPLOADED_STRUCTURED_FILES[filename]
            # Also remove from cache if present
            if filename in STRUCTURED_DATA_CACHE:
                del STRUCTURED_DATA_CACHE[filename]
        
        # Remove from the global tracking dict (backward compatibility)
        if filename in UPLOADED_FILES:
            del UPLOADED_FILES[filename]
        
        # Delete the actual file
        delete_file(file_record.file_path)
        
        # Delete the database record
        delete_file_record(db, file_record.id)
            
        return {"message": f"File '{filename}' successfully deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

@router.get("/uploaded-files")
async def get_all_uploaded_files(
    current_user: TokenPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """Lists all files belonging to the current user."""
    # Get files from the database for this user
    user_files = get_user_files(db, current_user.sub)
    
    # Convert to API response format
    files_response = [file_record_to_dict(file) for file in user_files]
    
    return {
        "files": files_response
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
@router.post("/download-filtered/")
async def download_filtered_data(
    request: FileProcessRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    # First verify the user owns this file
    file_record = get_file_by_filename(db, request.original_filename, current_user.sub)
    if not file_record:
        raise HTTPException(
            status_code=404, 
            detail=f"File '{request.original_filename}' not found or you don't have permission to access it."
        )
    
    # Rest of your existing function...
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
            raise HTTPException(status_code=400, detail=", ".join(errors))
        
        # Load the file from the user's directory
        user_upload_dir = ensure_user_upload_dir(current_user.sub)
        file_path = os.path.join(user_upload_dir, request.original_filename)
        
        # Execute the query using the file_path rather than just filename
        df = execute_filtered_query(
            filename=file_path,  # Pass the full path
            source_filename=request.original_filename,  # Also pass the original filename for reference
            query_params=request.query_params,
            sheet_name=request.sheet_name,
            drop_duplicates=request.drop_duplicates,
            subset=request.subset
        )
        
        if request.return_columns:
            return_cols = request.return_columns
            if isinstance(return_cols, str):
                return_cols = [return_cols]
            valid_cols = [col for col in return_cols if col in df.columns]
            if valid_cols:
                df = df[valid_cols]
        
        _, ext = os.path.splitext(request.filename_to_download.lower())
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
        
        return StreamingResponse(
            file_bytes, 
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={request.filename_to_download}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error preparing filtered data: {str(e)}")


@router.get("/uploaded-structured-files", dependencies=[Depends(get_api_key)])
async def get_uploaded_structured_files_list():
    """Lists structured files known to the system (for context or UI)."""
    return {"structured_files": UPLOADED_STRUCTURED_FILES}

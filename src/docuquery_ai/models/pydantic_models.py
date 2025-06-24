from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User's natural language query")
    file_context: Optional[str] = Field(
        default=None, description="Specific file to query against"
    )
    # session_id: Optional[str] = None # For session management if needed


class QueryResponse(BaseModel):
    answer: str
    type: str = Field(
        default="text", description="Type of response: 'text', 'list', 'table'"
    )
    data: Optional[Any] = Field(
        default=None,
        description="Data for 'list' or 'table' type (e.g., list of strings, list of dicts for table)",
    )
    columns: Optional[List[str]] = Field(
        default=None, description="Column headers if type is 'table'"
    )
    download_available: Optional[bool] = Field(default=False)
    download_filename: Optional[str] = Field(
        default=None, description="Filename for downloadable content"
    )
    # For enabling download, we need original file context and query params that generated the table
    file_context: Optional[str] = Field(
        default=None,
        description="Original filename for context if data is from a structured file",
    )
    query_params_for_download: Optional[Union[Dict, List[Dict]]] = Field(
        default=None,
        description="Query parameters that generated this downloadable table (either a single condition or list of conditions)",
    )
    sheet_name_for_download: Optional[str] = Field(
        default=None, description="Sheet name, if applicable, for downloadable table"
    )
    drop_duplicates_for_download: Optional[bool] = Field(
        default=False,
        description="Whether to drop duplicate rows in the downloaded file",
    )
    subset_for_download: Optional[List[str]] = Field(
        default=None, description="List of columns to consider when removing duplicates"
    )
    return_columns_for_download: Optional[List[str]] = Field(
        default=None, description="Specific columns to include in the downloaded file"
    )
    sources: Optional[str] = None  # For RAG source documents


class FileProcessRequest(BaseModel):
    filename_to_download: str  # e.g. "filtered_data.xlsx"
    original_filename: str  # e.g. "source_data.xlsx"
    query_params: Union[
        Dict, List[Dict]
    ]  # The query params that generated the filtered data (either a single condition or list of conditions)
    sheet_name: Optional[str] = None
    drop_duplicates: Optional[bool] = Field(
        default=False, description="Whether to drop duplicate rows"
    )
    subset: Optional[List[str]] = Field(
        default=None, description="List of columns to consider when removing duplicates"
    )
    return_columns: Optional[List[str]] = Field(
        default=None, description="Specific columns to include in the downloaded file"
    )

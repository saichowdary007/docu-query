import pandas as pd
import os
from typing import Dict, List, Any, Union
from io import BytesIO
from app.core.config import settings

# Simple cache for loaded dataframes to avoid re-reading constantly
# Key: filename, Value: pd.DataFrame or Dict[str, pd.DataFrame] for Excel
# This should ideally be more robust (e.g., Redis, or manage lifetimes)
STRUCTURED_DATA_CACHE: Dict[str, Any] = {}

def load_structured_file(filename: str) -> Union[pd.DataFrame, Dict[str, pd.DataFrame], None]:
    if filename in STRUCTURED_DATA_CACHE:
        return STRUCTURED_DATA_CACHE[filename]

    file_path = os.path.join(settings.TEMP_UPLOAD_FOLDER, filename) # Assuming files are kept here
    if not os.path.exists(file_path):
        # This indicates a potential issue: file summary in vector DB, but original gone.
        # For a robust system, uploaded files (especially structured ones) should persist reliably.
        print(f"Warning: Original file {filename} not found in temp_uploads for direct querying.")
        return None

    _, ext = os.path.splitext(filename.lower())
    data = None
    if ext == ".csv":
        data = pd.read_csv(file_path)
    elif ext in [".xls", ".xlsx"]:
        data = pd.read_excel(file_path, sheet_name=None) # Load all sheets

    if data is not None:
        STRUCTURED_DATA_CACHE[filename] = data
    return data


def get_interactive_list(filename: str, column_name: str, sheet_name: str = None) -> List[Any]:
    data = load_structured_file(filename)
    if data is None:
        return ["Error: File not found or not loaded."]

    df_to_query = None
    if isinstance(data, pd.DataFrame): # CSV
        df_to_query = data
    elif isinstance(data, dict) and sheet_name: # Excel
        df_to_query = data.get(sheet_name)
    elif isinstance(data, dict) and not sheet_name: # Excel, but no sheet specified
        if len(data) == 1: # If only one sheet, use it
            df_to_query = next(iter(data.values()))
        else:
            return [f"Error: Excel file '{filename}' has multiple sheets. Please specify one from: {list(data.keys())}"]


    if df_to_query is None:
        return [f"Error: Sheet '{sheet_name}' not found in '{filename}' or data not loaded."]
    
    if column_name not in df_to_query.columns:
        return [f"Error: Column '{column_name}' not found. Available columns: {df_to_query.columns.tolist()}"]
    
    return df_to_query[column_name].unique().tolist()


def execute_filtered_query(filename: str, query_params: Dict, sheet_name: str = None) -> pd.DataFrame:
    """
    Executes a filtered query based on parameters.
    query_params example: {"column": "Salary", "operator": ">", "value": 50000}
                         {"column": "Department", "operator": "==", "value": "HR"}
    This is a simplified example. Real-world would need more robust query parsing.
    """
    data = load_structured_file(filename)
    if data is None:
        raise ValueError("File not found or not loaded for querying.")

    df_to_query = None
    if isinstance(data, pd.DataFrame): # CSV
        df_to_query = data
    elif isinstance(data, dict) and sheet_name: # Excel
        df_to_query = data.get(sheet_name)
    elif isinstance(data, dict) and not sheet_name and len(data) == 1:
         df_to_query = next(iter(data.values()))
    elif isinstance(data, dict) and not sheet_name and len(data) > 1:
        raise ValueError(f"Excel file '{filename}' has multiple sheets. Query must specify a sheet.")
    
    if df_to_query is None:
        raise ValueError(f"Sheet '{sheet_name}' not found in '{filename}' or data structure issue.")

    # Basic filtering - Sanitize inputs carefully!
    # A more advanced approach would be to use LLM function calling to get structured query params.
    col = query_params.get("column")
    op = query_params.get("operator")
    val = query_params.get("value")

    if not all([col, op, val]):
        raise ValueError("Invalid query parameters. Need column, operator, and value.")
    if col not in df_to_query.columns:
        raise ValueError(f"Column '{col}' not found in data.")

    # Ensure value has correct type for comparison
    # This is crucial and needs robust type handling based on df_to_query[col].dtype
    try:
        if pd.api.types.is_numeric_dtype(df_to_query[col]):
            val = float(val) if '.' in str(val) else int(val)
        elif pd.api.types.is_datetime64_any_dtype(df_to_query[col]):
            val = pd.to_datetime(val)
        # else: treat as string (default)
    except ValueError:
        raise ValueError(f"Could not convert value '{val}' to match column '{col}' type.")

    if op == ">":
        result_df = df_to_query[df_to_query[col] > val]
    elif op == "<":
        result_df = df_to_query[df_to_query[col] < val]
    elif op == ">=":
        result_df = df_to_query[df_to_query[col] >= val]
    elif op == "<=":
        result_df = df_to_query[df_to_query[col] <= val]
    elif op == "==":
        result_df = df_to_query[df_to_query[col] == val]
    elif op == "!=":
        result_df = df_to_query[df_to_query[col] != val]
    elif op == "contains" and isinstance(val, str): # Ensure column is string type
        if not pd.api.types.is_string_dtype(df_to_query[col]):
             raise ValueError(f"Column '{col}' must be of string type for 'contains' operator.")
        result_df = df_to_query[df_to_query[col].str.contains(val, case=False, na=False)]
    else:
        raise ValueError(f"Unsupported operator: {op}")
    
    return result_df

def dataframe_to_excel_bytes(df: pd.DataFrame) -> BytesIO:
    output = BytesIO()
    # Use xlsxwriter engine for better Excel compatibility
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            # Get the xlsxwriter workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            
            # Add some minimal formatting
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
            
            # Write the column headers with the defined format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
            # Adjust column widths to fit content
            for i, col in enumerate(df.columns):
                # Find the max length in the column
                max_len = max(
                    df[col].astype(str).map(len).max(),  # Max data length
                    len(str(col))  # Length of column name
                ) + 2  # Add a little extra space
                
                # Set the column width
                worksheet.set_column(i, i, max_len)
    except ImportError:
        # Fall back to openpyxl if xlsxwriter is not available
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
    
    output.seek(0)
    return output

def dataframe_to_csv_bytes(df: pd.DataFrame) -> BytesIO:
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return output

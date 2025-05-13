import pandas as pd
import os
from typing import Dict, List, Any, Union, Optional
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


def execute_filtered_query(filename: str, query_params: Dict, sheet_name: str = None, drop_duplicates: bool = False, 
                           subset: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Executes a filtered query based on parameters.
    query_params example: {"column": "Salary", "operator": ">", "value": 50000}
                         {"column": "Department", "operator": "==", "value": "HR"}
    Or for multiple conditions:
    query_params example: [
        {"column": "Gender", "operator": "==", "value": "Male"},
        {"column": "Age", "operator": ">", "value": 36}
    ]
    """
    data = load_structured_file(filename)
    if data is None:
        raise ValueError("File not found or not loaded for querying.")

    # Determine if this is a CSV file
    _, ext = os.path.splitext(filename.lower())
    is_csv = ext == ".csv"
    
    # Get the dataframe to query
    if isinstance(data, pd.DataFrame): # CSV
        df_to_query = data.copy()
    elif isinstance(data, dict) and sheet_name: # Excel with specified sheet
        df_to_query = data.get(sheet_name).copy() if sheet_name in data else None
    elif isinstance(data, dict) and not sheet_name and len(data) == 1: # Excel with single sheet
        df_to_query = next(iter(data.values())).copy()
    elif isinstance(data, dict) and not sheet_name and len(data) > 1: # Excel with multiple sheets
        raise ValueError(f"Excel file '{filename}' has multiple sheets. Query must specify a sheet.")
    else:
        raise ValueError(f"Could not process data from '{filename}'.")
    
    if df_to_query is None:
        raise ValueError(f"Sheet '{sheet_name}' not found in '{filename}' or data structure issue.")
    
    # Process single or multiple conditions
    if isinstance(query_params, list):
        # Apply multiple conditions sequentially
        for condition in query_params:
            col = condition.get("column")
            op = condition.get("operator")
            val = condition.get("value")
            
            if not all([col, op, val]):
                raise ValueError("Invalid query parameters. Need column, operator, and value.")
            if col not in df_to_query.columns:
                raise ValueError(f"Column '{col}' not found in data.")
            
            # Apply filter for this condition
            df_to_query = filter_dataframe(df_to_query, col, op, val, is_csv)
    else:
        # Apply single condition
        col = query_params.get("column")
        op = query_params.get("operator")
        val = query_params.get("value")
        
        if not all([col, op, val]):
            raise ValueError("Invalid query parameters. Need column, operator, and value.")
        if col not in df_to_query.columns:
            raise ValueError(f"Column '{col}' not found in data.")
        
        # Apply filter
        df_to_query = filter_dataframe(df_to_query, col, op, val, is_csv)
    
    # Handle duplicates if requested
    if drop_duplicates:
        df_to_query = df_to_query.drop_duplicates(subset=subset)
    
    return df_to_query

def filter_dataframe(df: pd.DataFrame, col: str, op: str, val: Any, is_csv: bool = False) -> pd.DataFrame:
    """Simple function to filter a dataframe based on a condition."""
    # Special handling for CSV files
    if is_csv:
        # For string comparisons
        if op in ["==", "!=", "contains"]:
            # Convert to strings and normalize
            df_col_str = df[col].astype(str).str.strip().str.lower()
            val_str = str(val).strip().lower()
            
            # Apply the appropriate comparison
            if op == "==":
                # Create a boolean mask
                mask = df_col_str == val_str
                # Use .loc to avoid ambiguous truth value errors
                return df.loc[mask]
            elif op == "!=":
                mask = df_col_str != val_str
                return df.loc[mask]
            elif op == "contains":
                # Handle NaN values
                mask = df_col_str.str.contains(val_str, na=False)
                return df.loc[mask]
        
        # For numeric comparisons
        else:
            # Convert to numeric, coercing errors to NaN
            df_col_num = pd.to_numeric(df[col], errors='coerce')
            
            try:
                val_num = float(val) if '.' in str(val) else int(val)
            except ValueError:
                raise ValueError(f"Cannot convert '{val}' to a number for comparison.")
            
            # Apply the appropriate comparison
            if op == ">":
                mask = df_col_num > val_num
                # Fill NaN values in mask with False
                mask = mask.fillna(False)
                return df.loc[mask]
            elif op == "<":
                mask = df_col_num < val_num
                mask = mask.fillna(False)
                return df.loc[mask]
            elif op == ">=":
                mask = df_col_num >= val_num
                mask = mask.fillna(False)
                return df.loc[mask]
            elif op == "<=":
                mask = df_col_num <= val_num
                mask = mask.fillna(False)
                return df.loc[mask]
            else:
                raise ValueError(f"Unsupported operator '{op}' for numeric comparison.")
    
    # Standard handling for Excel files
    else:
        try:
            # Convert value to appropriate type
            if pd.api.types.is_numeric_dtype(df[col]):
                val = float(val) if '.' in str(val) else int(val)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                val = pd.to_datetime(val)
        except ValueError:
            raise ValueError(f"Could not convert '{val}' to match column '{col}' type.")
        
        # Apply the filter
        if op == "==":
            return df.loc[df[col] == val]
        elif op == "!=":
            return df.loc[df[col] != val]
        elif op == ">":
            return df.loc[df[col] > val]
        elif op == "<":
            return df.loc[df[col] < val]
        elif op == ">=":
            return df.loc[df[col] >= val]
        elif op == "<=":
            return df.loc[df[col] <= val]
        elif op == "contains" and isinstance(val, str):
            if not pd.api.types.is_string_dtype(df[col]):
                raise ValueError(f"Column '{col}' must be string type for 'contains' operator.")
            return df.loc[df[col].str.contains(val, case=False, na=False)]
        else:
            raise ValueError(f"Unsupported operator: {op}")

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

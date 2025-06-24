import os
from io import BytesIO
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from docuquery_ai.core.config import settings

# Simple cache for loaded dataframes to avoid re-reading constantly
# Key: filename, Value: pd.DataFrame or Dict[str, pd.DataFrame] for Excel
# This should ideally be more robust (e.g., Redis, or manage lifetimes)
STRUCTURED_DATA_CACHE: Dict[str, Any] = {}


def load_structured_file(
    file_path: str, filename: str = None
) -> Union[pd.DataFrame, Dict[str, pd.DataFrame], None]:
    """
    Load a structured file from path or by filename.

    Args:
        file_path: Full path to the file, or just the filename (for backward compatibility)
        filename: Optional filename for cache keys (if None, uses file_path basename)

    Returns:
        DataFrame or Dict of DataFrames for Excel files with multiple sheets
    """
    # For backward compatibility
    if not filename:
        filename = os.path.basename(file_path)

    # Check cache first
    if filename in STRUCTURED_DATA_CACHE:
        return STRUCTURED_DATA_CACHE[filename]

    # If file_path is just a filename (legacy), construct the full path
    if not os.path.exists(file_path) and not os.path.isabs(file_path):
        file_path = os.path.join(settings.TEMP_UPLOAD_FOLDER, file_path)

    if not os.path.exists(file_path):
        # This indicates a potential issue: file summary in vector DB, but original gone.
        print(f"Warning: File {filename} not found at {file_path} for direct querying.")
        return None

    _, ext = os.path.splitext(filename.lower())
    data = None
    try:
        if ext == ".csv":
            data = pd.read_csv(file_path)
        elif ext in [".xls", ".xlsx"]:
            data = pd.read_excel(file_path, sheet_name=None)  # Load all sheets
    except Exception as e:
        print(f"Error loading file {filename}: {str(e)}")
        return None

    if data is not None:
        STRUCTURED_DATA_CACHE[filename] = data
    return data


def get_interactive_list(
    filename: str, column_name: str, sheet_name: str = None
) -> List[Any]:
    """Get a list of unique values in a column for interactive filtering."""
    # Get the file path in the user's directory
    file_path = os.path.join(settings.TEMP_UPLOAD_FOLDER, filename)  # Default location

    # Try to load from this path first
    data = load_structured_file(file_path, filename)
    if data is None:
        return ["Error: File not found or not loaded."]

    df_to_query = None
    if isinstance(data, pd.DataFrame):  # CSV
        df_to_query = data
    elif isinstance(data, dict) and sheet_name:  # Excel
        df_to_query = data.get(sheet_name)
    elif isinstance(data, dict) and not sheet_name:  # Excel, but no sheet specified
        if len(data) == 1:  # If only one sheet, use it
            df_to_query = next(iter(data.values()))
        else:
            return [
                f"Error: Excel file '{filename}' has multiple sheets. Please specify one from: {list(data.keys())}"
            ]

    if df_to_query is None:
        return [
            f"Error: Sheet '{sheet_name}' not found in '{filename}' or data not loaded."
        ]

    if column_name not in df_to_query.columns:
        return [
            f"Error: Column '{column_name}' not found. Available columns: {df_to_query.columns.tolist()}"
        ]

    return df_to_query[column_name].unique().tolist()


def count_matching_rows(
    filename: str, column: str, value: Any, sheet_name: str = None
) -> int:
    """
    Count rows in a DataFrame that match a specific value in a column.
    This is useful for queries like "how many males" or "number of department X".

    Args:
        filename: The name of the file to query
        column: The column to filter on
        value: The value to match
        sheet_name: Sheet name for Excel files (optional)

    Returns:
        int: Count of matching rows
    """
    data = load_structured_file(filename)
    if data is None:
        raise ValueError(f"File {filename} not found or could not be loaded")

    # Get the dataframe to query
    if isinstance(data, pd.DataFrame):  # CSV
        df = data.copy()
        is_csv = True
    elif isinstance(data, dict) and sheet_name:  # Excel with sheet
        df = data.get(sheet_name).copy() if sheet_name in data else None
        is_csv = False
    elif (
        isinstance(data, dict) and not sheet_name and len(data) == 1
    ):  # Excel with single sheet
        df = next(iter(data.values())).copy()
        is_csv = False
    else:
        raise ValueError("Could not determine the right dataframe to query")

    if df is None:
        raise ValueError(f"Sheet '{sheet_name}' not found in '{filename}'")

    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in the data")

    # For string comparisons, normalize and use case-insensitive comparison
    if pd.api.types.is_string_dtype(df[column]) or is_csv:
        # Convert column to string and normalize
        df_col = df[column].astype(str).str.strip().str.lower()
        value_str = str(value).strip().lower()
        # Get mask and count True values
        mask = df_col.eq(value_str)
        return int(mask.sum())
    else:
        # For numeric or other comparisons
        try:
            if pd.api.types.is_numeric_dtype(df[column]):
                value = float(value) if "." in str(value) else int(value)
            # Get mask and count True values
            mask = df[column] == value
            return int(mask.sum())
        except (ValueError, TypeError):
            raise ValueError(
                f"Cannot compare values of column '{column}' with '{value}'"
            )


def execute_filtered_query(
    filename: str,
    query_params: Dict,
    sheet_name: str = None,
    drop_duplicates: bool = False,
    subset: Optional[List[str]] = None,
    source_filename: str = None,
) -> pd.DataFrame:
    """
    Executes a filtered query based on parameters.

    Args:
        filename: Full path to the file or just the filename (legacy)
        query_params: Dict or List of Dicts with filtering conditions
        sheet_name: Optional sheet name for Excel files
        drop_duplicates: Whether to drop duplicate rows
        subset: Optional list of columns to consider when dropping duplicates
        source_filename: Optional original filename for cache keys

    query_params example: {"column": "Salary", "operator": ">", "value": 50000}
                         {"column": "Department", "operator": "==", "value": "HR"}
    Or for multiple conditions:
    query_params example: [
        {"column": "Gender", "operator": "==", "value": "Male"},
        {"column": "Age", "operator": ">", "value": "36"}
    ]

    Special cases:
    - If query_params is an empty list [], returns all records without filtering
    """
    print(
        f"execute_filtered_query called with: filename={filename}, query_params={query_params}, "
        f"sheet_name={sheet_name}, drop_duplicates={drop_duplicates}, subset={subset}"
    )

    # If source_filename is provided, use it for cache key, otherwise extract from path
    cache_key = source_filename if source_filename else os.path.basename(filename)

    data = load_structured_file(filename, cache_key)
    if data is None:
        print(f"Error: File {filename} not found or could not be loaded")
        raise ValueError("File not found or not loaded for querying.")

    # Determine if this is a CSV file
    _, ext = os.path.splitext(cache_key.lower())
    is_csv = ext == ".csv"

    # Get the dataframe to query
    if isinstance(data, pd.DataFrame):  # CSV
        df_to_query = data.copy()
    elif isinstance(data, dict) and sheet_name:  # Excel with specified sheet
        df_to_query = data.get(sheet_name).copy() if sheet_name in data else None
    elif (
        isinstance(data, dict) and not sheet_name and len(data) == 1
    ):  # Excel with single sheet
        df_to_query = next(iter(data.values())).copy()
    elif (
        isinstance(data, dict) and not sheet_name and len(data) > 1
    ):  # Excel with multiple sheets
        raise ValueError(
            f"Excel file '{cache_key}' has multiple sheets. Query must specify a sheet."
        )
    else:
        raise ValueError(f"Could not process data from '{cache_key}'.")

    if df_to_query is None:
        raise ValueError(
            f"Sheet '{sheet_name}' not found in '{cache_key}' or data structure issue."
        )

    # Handle specific cases - pre-process common columns for CSV files
    if is_csv:
        # Pre-process specific columns that might cause issues
        if "Gender" in df_to_query.columns:
            # Normalize gender values to avoid case/whitespace issues
            df_to_query["Gender"] = (
                df_to_query["Gender"].astype(str).str.strip().str.lower()
            )

    # Special case for "count" or "number of" queries with equality operator
    count_only = False
    if isinstance(query_params, dict) and query_params.get("count_only", False):
        count_only = True
        # If it's a simple count query with a single equality condition
        if query_params.get("operator") == "==":
            col = query_params.get("column")
            val = query_params.get("value")
            try:
                count = count_matching_rows(filename, col, val, sheet_name)
                # Create a simple DataFrame with the count to return
                return pd.DataFrame({"Count": [count]})
            except Exception as e:
                print(f"Error in count_matching_rows: {str(e)}")
                # Fall back to normal filtering below

    # Handle empty query_params list - return all records without filtering
    if isinstance(query_params, list) and len(query_params) == 0:
        print(f"No query parameters provided. Returning all records from {filename}")

        # Handle duplicates if requested
        if drop_duplicates:
            df_to_query = df_to_query.drop_duplicates(subset=subset)

        return df_to_query

    # Process single or multiple conditions
    try:
        if isinstance(query_params, list):
            # Apply multiple conditions sequentially
            for condition in query_params:
                col = condition.get("column")
                op = condition.get("operator")
                val = condition.get("value")

                if not all(
                    [col, op, val is not None]
                ):  # Changed to handle val=0 or val=False
                    raise ValueError(
                        "Invalid query parameters. Need column, operator, and value."
                    )
                if col not in df_to_query.columns:
                    raise ValueError(f"Column '{col}' not found in data.")

                # Special handling for gender column in CSV files to prevent ambiguity
                if is_csv and col.lower() == "gender" and op == "==":
                    val = str(val).strip().lower()  # Normalize value
                    # Create mask directly
                    mask = (df_to_query[col] == val).to_numpy()
                    df_to_query = df_to_query.loc[mask]
                else:
                    # Apply filter for this condition
                    try:
                        df_to_query = filter_dataframe(
                            df_to_query, col, op, val, is_csv
                        )
                    except Exception as e:
                        print(f"Error filtering on {col} {op} {val}: {str(e)}")
                        raise ValueError(
                            f"Error filtering on {col} {op} {val}: {str(e)}"
                        )
        else:
            # Apply single condition
            col = query_params.get("column")
            op = query_params.get("operator")
            val = query_params.get("value")

            if not all(
                [col, op, val is not None]
            ):  # Changed to handle val=0 or val=False
                raise ValueError(
                    "Invalid query parameters. Need column, operator, and value."
                )
            if col not in df_to_query.columns:
                raise ValueError(f"Column '{col}' not found in data.")

            # Special handling for gender column in CSV files to prevent ambiguity
            if is_csv and col.lower() == "gender" and op == "==":
                val = str(val).strip().lower()  # Normalize value
                # Create mask directly
                mask = (df_to_query[col] == val).to_numpy()
                df_to_query = df_to_query.loc[mask]
            else:
                # Apply filter
                try:
                    df_to_query = filter_dataframe(df_to_query, col, op, val, is_csv)
                except Exception as e:
                    print(f"Error filtering on {col} {op} {val}: {str(e)}")
                    raise ValueError(f"Error filtering on {col} {op} {val}: {str(e)}")

        # Special case for count-only queries with multiple conditions
        # Return just the count after all filters have been applied
        if count_only and isinstance(query_params, list):
            # Handle duplicates if requested before counting
            if drop_duplicates:
                df_to_query = df_to_query.drop_duplicates(subset=subset)
            return pd.DataFrame({"Count": [len(df_to_query)]})

    except Exception as e:
        print(f"Error during query execution: {str(e)}")
        raise

    # Handle duplicates if requested
    if drop_duplicates:
        df_to_query = df_to_query.drop_duplicates(subset=subset)

    return df_to_query


def filter_dataframe(
    df: pd.DataFrame, col: str, op: str, val: Any, is_csv: bool = False
) -> pd.DataFrame:
    """Simple function to filter a dataframe based on a condition."""
    # Special handling for CSV files
    if is_csv:
        # For string comparisons
        if op in ["==", "!=", "contains"]:
            # Convert to strings and normalize
            df_col_str = df[col].astype(str).str.strip().str.lower()
            val_str = str(val).strip().lower()

            if op == "==":
                mask = df_col_str.eq(val_str)
                return df.loc[mask]
            elif op == "!=":
                mask = df_col_str.ne(val_str)
                return df.loc[mask]
            elif op == "contains":
                mask = df_col_str.str.contains(val_str, na=False)
                return df.loc[mask]

        # For numeric comparisons
        else:
            # Convert to numeric, coercing errors to NaN
            df_col_num = pd.to_numeric(df[col], errors="coerce")

            try:
                val_num = float(val) if "." in str(val) else int(val)
            except ValueError:
                raise ValueError(f"Cannot convert '{val}' to a number for comparison.")

            # Apply comparisons and create masks
            if op == ">":
                mask = df_col_num > val_num
                return df.loc[mask.fillna(False)]
            elif op == "<":
                mask = df_col_num < val_num
                return df.loc[mask.fillna(False)]
            elif op == ">=":
                mask = df_col_num >= val_num
                return df.loc[mask.fillna(False)]
            elif op == "<=":
                mask = df_col_num <= val_num
                return df.loc[mask.fillna(False)]
            else:
                raise ValueError(f"Unsupported operator '{op}' for numeric comparison.")

    # Standard handling for Excel files
    else:
        try:
            # Convert value to appropriate type
            if pd.api.types.is_numeric_dtype(df[col]):
                val = float(val) if "." in str(val) else int(val)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                val = pd.to_datetime(val)
        except ValueError:
            raise ValueError(f"Could not convert '{val}' to match column '{col}' type.")

        # Apply filters using masks
        if op == "==":
            mask = (df[col] == val).to_numpy()
            return df.loc[mask]
        elif op == "!=":
            mask = (df[col] != val).to_numpy()
            return df.loc[mask]
        elif op == ">":
            mask = (df[col] > val).to_numpy()
            return df.loc[mask]
        elif op == "<":
            mask = (df[col] < val).to_numpy()
            return df.loc[mask]
        elif op == ">=":
            mask = (df[col] >= val).to_numpy()
            return df.loc[mask]
        elif op == "<=":
            mask = (df[col] <= val).to_numpy()
            return df.loc[mask]
        elif op == "contains" and isinstance(val, str):
            if not pd.api.types.is_string_dtype(df[col]):
                df[col] = df[col].astype(str)  # Convert column to string type
            mask = df[col].str.contains(val, case=False, na=False).to_numpy()
            return df.loc[mask]
        else:
            raise ValueError(f"Unsupported operator: {op}")


def dataframe_to_excel_bytes(df: pd.DataFrame) -> BytesIO:
    output = BytesIO()
    # Use xlsxwriter engine for better Excel compatibility
    try:
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")
            # Get the xlsxwriter workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets["Sheet1"]

            # Add some minimal formatting
            header_format = workbook.add_format({"bold": True, "bg_color": "#D3D3D3"})

            # Write the column headers with the defined format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # Adjust column widths to fit content
            for i, col in enumerate(df.columns):
                # Find the max length in the column
                max_len = (
                    max(
                        df[col].astype(str).map(len).max(),  # Max data length
                        len(str(col)),  # Length of column name
                    )
                    + 2
                )  # Add a little extra space

                # Set the column width
                worksheet.set_column(i, i, max_len)
    except ImportError:
        # Fall back to openpyxl if xlsxwriter is not available
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")

    output.seek(0)
    return output


def dataframe_to_csv_bytes(df: pd.DataFrame) -> BytesIO:
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return output

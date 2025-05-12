import logging
from mimetypes import guess_type
import re
from xml.dom.minidom import Document
import duckdb # Keep for type hinting if needed, but connection comes from rag_core
from typing import Dict, List, Any, Optional, Tuple

# Import the function to get the shared DB connection from rag_core
from rag_core import get_shared_db_connection, execute_sql_query_rag # Use RAG core's SQL executor

# Configure logging
logger = logging.getLogger(__name__)

class DirectResponseGenerator:
    """
    Class to generate direct responses for specific tabular queries,
    bypassing the LLM for simple operations like counting and listing.
    This version uses a shared DuckDB connection.
    """
    
    def __init__(self):
        # Patterns for identifying simple count and list queries
        self.count_patterns = [
            r"(?i)how\s+many\s+(.*?)(?:\s+are\s+there|\s+exist|\s+in\s+total|\s+total|\s+records|\s+rows|\s+items|\s+entries|\s+from|\s*\?|$)",
            r"(?i)count\s+(?:the\s+|all\s+|of\s+)?(.*?)(?:\s+in|\s+from|\s*\?|$)",
            r"(?i)total\s+(?:number\s+of\s+)?(.*?)(?:\s+in|\s+from|\s*\?|$)"
        ]
        
        self.list_patterns = [
            r"(?i)list\s+(?:all\s+|the\s+)?(.*?)(?:\s+in|\s+from|\s*\?|$)",
            r"(?i)show\s+(?:all\s+|the\s+|me\s+)?(.*?)(?:\s+in|\s+from|\s*\?|$)",
            r"(?i)what\s+(?:are|is)\s+(?:all\s+|the\s+)?(.*?)(?:\s+in|\s+from|\s*\?|$)",
            r"(?i)give\s+me\s+(?:all\s+|the\s+)?(.*?)(?:\s+in|\s+from|\s*\?|$)"
        ]
        
        # Get the shared DuckDB connection
        try:
            self.db_conn = get_shared_db_connection()
            if self.db_conn:
                logger.info("DirectResponseGenerator: Successfully obtained shared DuckDB connection.")
            else:
                logger.error("DirectResponseGenerator: Failed to obtain shared DuckDB connection.")
        except Exception as e:
            logger.error(f"DirectResponseGenerator: Error obtaining shared DuckDB connection: {e}")
            self.db_conn = None # Ensure it's None if connection fails
    
    def can_handle_directly(self, query: str, table_names: List[str]) -> bool:
        """Check if the query matches simple patterns for direct handling."""
        if not self.db_conn or not table_names:
            return False
        for pattern in self.count_patterns:
            if re.search(pattern, query): return True
        for pattern in self.list_patterns:
            if re.search(pattern, query): return True
        return False
    
    def _get_table_columns(self, table_name: str) -> List[str]:
        """Helper to get column names for a given table."""
        if not self.db_conn:
            return []
        try:
            # Ensure table_name is quoted for safety, especially if it contains special characters
            # However, PRAGMA table_info might expect unquoted name if it's simple.
            # DuckDB is generally good with quoted names in most contexts.
            cols_info = self.db_conn.execute(f"PRAGMA table_info(\"{table_name}\")").fetchall()
            return [col_info[1].lower() for col_info in cols_info]
        except Exception as e:
            logger.warning(f"Could not fetch column info for table '{table_name}': {e}")
            return []

    def extract_target_and_filters(self, query: str, table_name: str) -> Tuple[str, Dict[str, str], str]:
        """Extract target entity, filters, and query type from the query string."""
        target_entity = "*"
        filters: Dict[str, str] = {}
        query_type = "list" # Default query type
        
        table_columns = self._get_table_columns(table_name)

        # Check count patterns first
        for pattern in self.count_patterns:
            match = re.search(pattern, query)
            if match:
                query_type = "count"
                target_text = match.group(1).strip().lower()
                if target_text and target_text not in ["items", "records", "entries", "rows", "results", "all", "everything", "them"]:
                    if target_text in table_columns:
                        target_entity = f'"{target_text}"' # Quote column name for safety
                    else:
                        # If not a direct column match, assume counting all rows for now
                        logger.info(f"Target text '{target_text}' for count not a column of '{table_name}'. Defaulting to COUNT(*).")
                        target_entity = "*" 
                else: # e.g., "how many items"
                    target_entity = "*"
                break # Found a count pattern
        
        # If not a count query, check list patterns
        if query_type == "list":
            for pattern in self.list_patterns:
                match = re.search(pattern, query)
                if match:
                    query_type = "list" # Explicitly set, though default
                    target_text = match.group(1).strip().lower()
                    if target_text and target_text not in ["items", "records", "entries", "rows", "results", "all", "everything", "them"]:
                        if target_text in table_columns:
                            target_entity = f'"{target_text}"'
                        elif "all " + target_text in table_columns: # Handle "list all columns" -> "list columns"
                             target_entity = f'"{target_text}"'
                        else:
                            logger.info(f"Target text '{target_text}' for list not a column of '{table_name}'. Defaulting to SELECT *.")
                            target_entity = "*"
                    else: # e.g., "list all items"
                        target_entity = "*"
                    break # Found a list pattern

        # Simplified filter extraction (placeholder for more advanced NLP/parsing)
        # This part is highly complex and ideally should be handled by a Text-to-SQL LLM.
        # For this direct generator, we'll keep it very basic.
        filter_keywords = ["where", "with", "for", "that have", "who are", "which are", "whose"]
        remaining_query_part = query # Search for filters in the whole query
        
        # Example: "list users where age > 30" or "count products with category = 'electronics'"
        # This basic regex won't handle complex conditions, AND/OR, etc.
        # It looks for "column_name operator value"
        # Operators can be =, >, <, >=, <=, LIKE, IS, IS NOT
        # Values can be numbers, or quoted strings
        # This is a very simplified parser.
        for keyword in filter_keywords:
            # Regex to find "column operator value" after a keyword
            # It's hard to make this robust without a proper parser.
            # Example: "where name = 'John Doe'" or "for age > 25"
            # For simplicity, we'll look for patterns like: col = 'val', col = val, col > val
            # This regex is very basic and will miss many cases.
            filter_pattern_text = rf"(?i){keyword}\s+((?:\"[^\"]+\"|'[^']+'|\w+)\s*(?:=|is\s+not|is|like|>=|<=|>|<)\s*(?:\"[^\"]+\"|'[^']+'|\d+(?:\.\d+)?|true|false|null))"
            
            for f_match in re.finditer(filter_pattern_text, remaining_query_part):
                filter_condition_full = f_match.group(1).strip()
                
                # Split condition into column, operator, value
                # This is a common source of errors with regex based parsing.
                condition_match = re.match(r"(\w+|\"[^\"]+\"|'[^']+')\s*(={1,2}|is\s+not|is|like|>=|<=|>|<)\s*(.+)", filter_condition_full, re.IGNORECASE)
                if condition_match:
                    col_name_raw, operator, val_raw = condition_match.groups()
                    col_name = col_name_raw.strip().replace("\"", "").replace("'", "").lower()
                    val = val_raw.strip()
                    operator = operator.strip().upper()

                    if col_name in table_columns:
                        # Ensure column name is quoted in the filter dictionary key for SQL generation
                        quoted_col_name = f'"{col_name}"'
                        # Store as a tuple (operator, value) to allow more complex conditions later
                        # For now, we only use the first one found per column for simplicity
                        if quoted_col_name not in filters:
                             filters[quoted_col_name] = f"{operator} {val}"
                        logger.info(f"Extracted filter: {col_name} {operator} {val}")
                    else:
                        logger.warning(f"Filter column '{col_name}' not found in table '{table_name}' columns: {table_columns}")
        
        return target_entity, filters, query_type

    def generate_sql_for_direct_handler(self, query: str, table_name: str) -> str:
        """
        Generates SQL for simple count/list queries.
        This is a simplified version. For complex queries, a Text-to-SQL LLM is better.
        """
        target, filters, query_type = self.extract_target_and_filters(query, table_name)
        
        # Ensure table_name is quoted to handle spaces or special characters
        quoted_table_name = f'"{table_name}"'

        sql_parts = []
        if query_type == "count":
            if target == "*": # Default for "how many items"
                sql_parts.append(f"SELECT COUNT(*) FROM {quoted_table_name}")
            else: # "how many distinct values in column X"
                sql_parts.append(f"SELECT COUNT(DISTINCT {target}) FROM {quoted_table_name}")
        else:  # list query
            select_clause = f"SELECT DISTINCT {target}" if target != "*" else "SELECT *"
            sql_parts.append(f"{select_clause} FROM {quoted_table_name}")
        
        if filters:
            where_conditions = []
            for col_key_quoted, condition_val_str in filters.items():
                # col_key_quoted is already like "\"column_name\""
                # condition_val_str is like "OPERATOR value"
                where_conditions.append(f"{col_key_quoted} {condition_val_str}") 
            if where_conditions:
                sql_parts.append("WHERE " + " AND ".join(where_conditions))
        
        if query_type == "list":
            sql_parts.append("LIMIT 10") # Reduced limit for direct listing to keep it concise
            
        sql = " ".join(sql_parts)
        logger.info(f"DirectResponseGenerator generated SQL: {sql} for table '{table_name}'")
        return sql
    
    def generate_direct_response(self, query: str, table_names: List[str]) -> Dict[str, Any]:
        """
        Generates a direct response by executing a simplified SQL query.
        """
        if not self.db_conn:
            logger.error("DirectResponseGenerator: No database connection available.")
            return {"type": "error", "message": "Database connection not available for direct response."}
        if not table_names:
            logger.warning("DirectResponseGenerator: No table names provided for direct response.")
            return {"type": "error", "message": "No table context for direct response."}
        
        try:
            # For simplicity, use the first table name if multiple are relevant.
            # A more sophisticated approach might involve choosing based on query keywords or asking user.
            table_name_to_query = table_names[0] 
            
            # Use the simplified SQL generator for direct handling
            sql = self.generate_sql_for_direct_handler(query, table_name_to_query)
            
            # Execute the query using the RAG core's SQL executor which uses the shared connection
            sql_execution_result = execute_sql_query_rag(sql)

            if sql_execution_result.get("type") == "error":
                logger.error(f"Direct SQL execution failed: {sql_execution_result.get('message')}")
                return sql_execution_result # Propagate the error

            result_data = sql_execution_result.get("data", [])
            columns = sql_execution_result.get("columns", [])
            
            response_text = ""
            if "count" in sql.lower() and result_data:
                # Count queries from execute_sql_query_rag return list of dicts like [{'COUNT(*)': value}]
                # or [{'COUNT(DISTINCT "col")': value}]
                if result_data and isinstance(result_data[0], dict):
                    count_value = list(result_data[0].values())[0]
                else: # Should not happen with current execute_sql_query_rag
                    count_value = "an unknown number of"

                target_for_response = "items"
                match_target_distinct = re.search(r"SELECT COUNT\(DISTINCT (.*?)\)", sql, re.IGNORECASE)
                if match_target_distinct:
                    target_for_response = f"distinct {match_target_distinct.group(1).replace('\"','')} values"
                elif "COUNT(*)" in sql:
                    target_for_response = "rows"
                response_text = f"There are {count_value} {target_for_response} in table '{table_name_to_query}' matching your criteria."
            
            elif "SELECT" in sql.upper() and guess_type == "list": # Check if it was a list query
                if result_data:
                    response_text = f"Here are some results from table '{table_name_to_query}':\n"
                    # Format as a simple list or key-value pairs
                    for item_dict in result_data[:5]: # Show first 5 results
                        if isinstance(item_dict, dict):
                            response_text += "- " + ", ".join([f"{k}: {v}" for k,v in item_dict.items()]) + "\n"
                        else: # Should be dict from execute_sql_query_rag
                            response_text += f"- {item_dict}\n"
                    if len(result_data) > 5:
                        response_text += f"...and {len(result_data) - 5} more items."
                else:
                     response_text = f"No items found in table '{table_name_to_query}' matching your criteria."
            
            if not response_text and result_data: # Fallback if no specific text generated but data exists
                response_text = f"Query executed. Found {len(result_data)} results from '{table_name_to_query}'."


            logger.info(f"Direct query returned {len(result_data)} results. Response text: '{response_text}'")
            
            return {
                "type": "sql_result", # Consistent with RAG core's SQL execution
                "data": result_data, 
                "query": sql,
                "columns": columns,
                "direct_response_text": response_text # Key for LLM to use or display
            }
        
        except Exception as e:
            logger.error(f"Error generating direct response: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"type": "error", "message": f"Error generating direct response: {str(e)}"}

# This function is now effectively replaced by execute_sql_query_rag in rag_core.py
# if all SQL execution is to go through rag_core.
# If response_generator needs to independently execute SQL (e.g. for its internal logic
# not directly tied to user queries), it should use get_shared_db_connection().
# For user-facing SQL execution, main.py should call rag_core.retrieve() or rag_core.execute_sql_query_rag().

# def execute_sql_query(query: str) -> Dict[str, Any]:
#     """
#     DEPRECATED in favor of rag_core.execute_sql_query_rag or direct use of shared connection.
#     Execute a SQL query against the shared DuckDB in-memory database.
#     """
#     logger.warning("response_generator.execute_sql_query is deprecated. Use rag_core.execute_sql_query_rag.")
#     return execute_sql_query_rag(query)


def process_query_for_direct_response(query: str, context_docs: List[Dict[str, Any]], file_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Process a user query, determining whether to use direct response generation.
    This function is called if a query is likely SQL and documents are tabular-related.
    Returns a direct response payload if handled, otherwise None.
    """
    try:
        table_names_in_context = set()
        if context_docs:
            for doc_meta in context_docs: # Assuming context_docs are lists of metadata dicts or Document objects
                if isinstance(doc_meta, Document) and hasattr(doc_meta, 'metadata'):
                    meta = doc_meta.metadata
                elif isinstance(doc_meta, dict):
                    meta = doc_meta
                else:
                    continue # Skip if not a recognized format

                if meta.get("table_name"):
                    table_names_in_context.add(meta["table_name"])
        
        if table_names_in_context:
            logger.info(f"Direct Response Check: Tabular context for tables: {table_names_in_context}")
            generator = DirectResponseGenerator() # Re-instantiate to get fresh shared connection status
            
            if generator.can_handle_directly(query, list(table_names_in_context)):
                logger.info("Direct Response Check: Query pattern matches direct handling criteria.")
                direct_response_payload = generator.generate_direct_response(query, list(table_names_in_context))
                
                if direct_response_payload.get("type") == "sql_result" and direct_response_payload.get("direct_response_text"):
                    logger.info("Direct response generated successfully.")
                    return direct_response_payload
                else:
                    logger.warning(f"Direct handling attempted but failed or no response text: {direct_response_payload.get('message', 'No specific error')}")
            else:
                logger.info("Direct Response Check: Query pattern does not match direct handling.")
        else:
            logger.info("Direct Response Check: No specific table names found in document context for direct query processing.")
            
        return None # Not handled directly
    
    except Exception as e:
        logger.error(f"Error in process_query_for_direct_response (response_generator): {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None # Fallback if error

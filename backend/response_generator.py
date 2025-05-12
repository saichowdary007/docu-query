import logging
import re
import duckdb
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# IMPORTANT: This module uses its own DuckDB connection. For a shared in-memory DB,
# a single connection instance must be passed around or managed globally.
# Current behavior: operations here are on a separate in-memory DB.
# This is generally problematic if tables are registered elsewhere (e.g. in rag_core.py)
# For the purpose of this exercise, we assume that execute_sql_query and DirectResponseGenerator
# are intended to operate on tables registered via rag_core.register_duckdb_table which uses rag_core.db_conn.
# This implies that all DuckDB operations should ideally use that single rag_core.db_conn instance.

# Accessing rag_core.db_conn directly would create a circular dependency if rag_core imports this.
# A proper fix involves a shared DB connection manager or passing the connection.
# For now, we'll proceed assuming that duckdb.connect(':memory:') within the same process
# might refer to the same default in-memory database, or that tables are re-registered if necessary.
# The most robust solution is that functions needing DB access take a connection object as an argument.

# Let's assume rag_core.py will expose its db_conn for now, or we connect to the same :memory: db.
# If rag_core.py initializes `db_conn = duckdb.connect(database=":memory:", read_only=False)`,
# then `duckdb.connect(database=":memory:", read_only=False)` elsewhere in the same process
# should connect to the same default in-memory database.

class DirectResponseGenerator:
    """
    Class to generate direct responses for specific tabular queries,
    bypassing the LLM for simple operations like counting and listing.
    """
    
    def __init__(self):
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
        
        try:
            # Connect to the default in-memory DuckDB database.
            # This should be the same one used by rag_core.py if it also uses duckdb.connect(':memory:')
            self.db_conn = duckdb.connect(database=":memory:", read_only=False)
            logger.info("DirectResponseGenerator: DuckDB connection established to :memory:")
        except Exception as e:
            logger.error(f"DirectResponseGenerator: Error connecting to DuckDB: {e}")
            self.db_conn = None
    
    def can_handle_directly(self, query: str, table_names: List[str]) -> bool:
        if not self.db_conn or not table_names:
            return False
        for pattern in self.count_patterns:
            if re.search(pattern, query): return True
        for pattern in self.list_patterns:
            if re.search(pattern, query): return True
        return False
    
    def extract_target_and_filters(self, query: str, table_name: str) -> Tuple[str, Dict[str, str], str]:
        target_entity = "*"
        filters = {}
        query_type = "list"
        
        # Get column names for the given table to improve matching
        table_columns = []
        if self.db_conn:
            try:
                cols_info = self.db_conn.execute(f"PRAGMA table_info(\"{table_name}\")").fetchall()
                table_columns = [col_info[1].lower() for col_info in cols_info]
            except Exception as e:
                logger.warning(f"Could not fetch column info for table {table_name}: {e}")

        patterns_to_check = []
        for pattern_list, q_type in [(self.count_patterns, "count"), (self.list_patterns, "list")]:
            for pattern in pattern_list:
                match = re.search(pattern, query)
                if match:
                    target_text = match.group(1).strip().lower()
                    query_type = q_type
                    
                    if target_text and target_text not in ["items", "records", "entries", "rows", "results", "all", "everything", "them"]:
                        # Attempt to match target_text to an actual column name
                        if target_text in table_columns:
                            target_entity = f'"{target_text}"' # Quote column name
                        else:
                            # More fuzzy matching could be added here if needed
                            # For now, if not an exact match, assume it's not a column selector unless it's clearly one.
                            # This part is tricky; LLM might be better for complex target parsing.
                            # Defaulting to "*" if not a clear column match.
                            logger.info(f"Target text '{target_text}' not directly matched to columns of '{table_name}'. Defaulting target to *.")
                            target_entity = "*" 
                    else: # e.g. "how many items", "list all"
                        target_entity = "*"

                    # Simplified filter extraction (very basic)
                    # This part would benefit greatly from more advanced NLP/parsing
                    filter_keywords = ["where", "with", "for", "that have", "who are", "which are"]
                    for keyword in filter_keywords:
                        # Look for "column_name = value" or "column_name is value" patterns after keyword
                        filter_pattern_text = f"(?i){keyword}\\s+((?:\"[^\"]+\"|'[^']+'|\\w+)\\s*(?:=|is)\\s*(?:\"[^\"]+\"|'[^']+'|\\w+))"
                        filter_match = re.search(filter_pattern_text, query)
                        if filter_match:
                            filter_condition = filter_match.group(1).strip()
                            # Example: "name = 'John'" or "age = 30"
                            # This simplified parser won't handle complex conditions well
                            if "=" in filter_condition:
                                parts = filter_condition.split("=", 1)
                                col_name = parts[0].strip().replace("\"", "").replace("'", "")
                                val = parts[1].strip()
                                if col_name in table_columns: # Ensure column exists
                                     filters[f'"{col_name}"'] = val # Quote column name
                                else:
                                     logger.warning(f"Filter column '{col_name}' not found in table '{table_name}'")

                    return target_entity, filters, query_type # Found a match, return
        
        return target_entity, filters, query_type # Default if no pattern matched

    def generate_sql(self, query: str, table_name: str) -> str:
        target, filters, query_type = self.extract_target_and_filters(query, table_name)
        
        sql_parts = []
        if query_type == "count":
            if target == "*":
                sql_parts.append(f"SELECT COUNT(*) FROM \"{table_name}\"")
            else:
                # Count distinct values in the target column
                sql_parts.append(f"SELECT COUNT(DISTINCT {target}) FROM \"{table_name}\"")
        else:  # list query
            select_clause = f"SELECT DISTINCT {target}" if target != "*" else "SELECT *"
            sql_parts.append(f"{select_clause} FROM \"{table_name}\"")
        
        if filters:
            where_conditions = []
            for col, value in filters.items():
                # Value is already extracted, it might be 'value' or "value" or number
                # DuckDB is good at type inference for literals in SQL
                where_conditions.append(f"{col} = {value}") 
            if where_conditions:
                sql_parts.append("WHERE " + " AND ".join(where_conditions))
        
        if query_type == "list":
            sql_parts.append("LIMIT 20") # Reduced limit for direct listing
            
        sql = " ".join(sql_parts)
        logger.info(f"DirectResponseGenerator generated SQL: {sql}")
        return sql
    
    def generate_direct_response(self, query: str, table_names: List[str]) -> Dict[str, Any]:
        if not self.db_conn or not table_names:
            return {"type": "error", "message": "No database connection or tables available"}
        
        try:
            # For simplicity, use the first table name if multiple contextually relevant tables are found.
            # A more sophisticated approach might involve asking the user or using LLM to pick.
            table_name = table_names[0] 
            
            sql = self.generate_sql(query, table_name)
            
            query_result = self.db_conn.execute(sql)
            result_data = query_result.fetchall()
            columns = [desc[0] for desc in query_result.description]
            
            # Process results: convert from list of tuples to list of dicts or list of values
            output_data = []
            if len(columns) == 1: # Single column result
                output_data = [row[0] for row in result_data]
            else: # Multiple columns
                output_data = [dict(zip(columns, row)) for row in result_data]

            response_text = ""
            if "count" in sql.lower() and output_data:
                count_value = output_data[0] # Count query returns a single value in a list
                # Adjust based on target to be more descriptive
                target_for_response = "items" # default
                match_target = re.search(r"SELECT COUNT\(DISTINCT (.*?)\)", sql, re.IGNORECASE)
                if match_target:
                    target_for_response = f"distinct {match_target.group(1).replace('\"','')} values"
                elif "COUNT(*)" in sql:
                    target_for_response = "rows"

                response_text = f"There are {count_value} {target_for_response} in table '{table_name}' matching your criteria."
            elif "SELECT DISTINCT" in sql and output_data: # Assuming query_type was set during generate_sql
                response_text = f"Here are some results from table '{table_name}':\n"
                response_text += "\n".join([str(item) for item in output_data[:5]]) # Show first 5
                if len(output_data) > 5:
                    response_text += f"\n...and {len(output_data) - 5} more items."
                if not output_data:
                     response_text = f"No items found in table '{table_name}' matching your criteria."

            logger.info(f"Direct query returned {len(output_data)} results. Response text: '{response_text}'")
            
            return {
                "type": "sql_result",
                "data": output_data, # list of dicts or list of values
                "query": sql,
                "columns": columns,
                "direct_response": response_text # LLM can use this or generate its own
            }
        
        except Exception as e:
            logger.error(f"Error generating direct response: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"type": "error", "message": f"Error generating direct response: {str(e)}"}

def execute_sql_query(query: str) -> Dict[str, Any]:
    """Execute a SQL query against the shared DuckDB in-memory database."""
    try:
        # Connect to the default in-memory DuckDB.
        db_conn = duckdb.connect(database=":memory:", read_only=False)
        
        # For debugging: list available tables in this connection
        # tables_debug = db_conn.execute("SHOW TABLES").fetchall()
        # logger.debug(f"execute_sql_query: Tables in current DuckDB connection: {tables_debug}")
        
        query_result = db_conn.execute(query)
        result_data = query_result.fetchall()
        columns = [desc[0] for desc in query_result.description]
        
        # Convert to list of dicts for easier handling, unless it's a single column result (often aggregates)
        output_data = []
        if len(columns) == 1 and result_data and isinstance(result_data[0], tuple) and len(result_data[0]) == 1:
            # If it's like [(val1,), (val2,)]
            output_data = [row[0] for row in result_data]
        else:
             output_data = [dict(zip(columns, row)) for row in result_data]

        logger.info(f"SQL query '{query}' returned {len(output_data)} results.")
        return {
            "type": "sql_result",
            "data": output_data,
            "query": query,
            "columns": columns
        }
    except Exception as e:
        logger.error(f"SQL Error for query '{query}': {str(e)}")
        error_msg = str(e)
        suggestion = ""
        
        # More robust table name extraction from common DuckDB errors
        missing_table_match = re.search(r"Table with name (\w+|\".*?\") does not exist", error_msg, re.IGNORECASE)
        if not missing_table_match: # Try another pattern
            missing_table_match = re.search(r"Catalog Error: Table with name (.*?) does not exist!", error_msg, re.IGNORECASE)

        if missing_table_match:
            missing_table = missing_table_match.group(1).replace("\"", "")
            # Fetch current tables to suggest
            try:
                current_tables_conn = duckdb.connect(database=":memory:", read_only=True)
                tables_fetch = current_tables_conn.execute("SHOW TABLES").fetchall()
                available_tables = [t[0] for t in tables_fetch]
                if available_tables:
                    suggestion = f" Did you mean one of these? {', '.join(available_tables)}."
                else:
                    suggestion = " No tables are currently registered. Try uploading a CSV or Excel file."
                current_tables_conn.close()
            except Exception as list_table_err:
                logger.error(f"Could not list tables for error suggestion: {list_table_err}")

            error_msg = f"Table '{missing_table}' not found.{suggestion}"
        
        return {
            "type": "error",
            "message": f"SQL Error: {error_msg}",
            "query": query
        }

def process_query(query: str, context: Dict[str, Any], metadata_filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process a user query, determining whether to use direct response or pass to LLM.
    This function is called if a query is likely SQL and documents are tabular-related.
    """
    try:
        docs = context.get("data", []) # These are retrieved documents
        
        # Collect all table names mentioned in the metadata of retrieved documents
        table_names_in_context = set()
        for doc in docs:
            if doc.metadata.get("table_name"):
                table_names_in_context.add(doc.metadata["table_name"])
        
        if table_names_in_context:
            logger.info(f"Tabular context found for tables: {table_names_in_context}")
            generator = DirectResponseGenerator()
            
            # Check if the query can be handled by simple patterns (count, list)
            if generator.can_handle_directly(query, list(table_names_in_context)):
                logger.info("Query pattern matches direct handling criteria.")
                # Generate direct response (SQL query and execution)
                direct_response_payload = generator.generate_direct_response(query, list(table_names_in_context))
                # If successful direct response, return it. Otherwise, context will be passed to LLM.
                if direct_response_payload.get("type") == "sql_result":
                    return direct_response_payload
                else:
                    logger.warning(f"Direct handling failed: {direct_response_payload.get('message')}. Falling back to LLM with original context.")
            else:
                logger.info("Query pattern does not match direct handling. LLM will process.")
        else:
            logger.info("No specific table names found in document context for direct query processing.")
            
        # If not handled directly, return the original context for LLM processing
        return context
    
    except Exception as e:
        logger.error(f"Error in process_query (response_generator): {e}")
        import traceback
        logger.error(traceback.format_exc())
        return context # Fallback to returning original context
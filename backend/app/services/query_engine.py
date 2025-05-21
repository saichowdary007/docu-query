from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from app.services.nlp_service import get_llm
from app.services.vector_store import get_retriever
from app.services.data_handler import get_interactive_list, execute_filtered_query, load_structured_file, count_matching_rows
import json
import os
import pandas as pd
from copy import deepcopy
from typing import Optional

# This is a crucial part: Intent recognition and dispatching
# For a production system, this would be more sophisticated, possibly using
# LLM function calling or a dedicated NLU model.

# Tool/Intent definitions (conceptual)
# This helps the LLM understand what actions it can suggest or what information it needs.
TOOL_DESCRIPTIONS = """
Available tools:
1.  **retrieve_general_info**: Use this for general questions about the content of uploaded documents.
    Input: User's query.
    Output: Answer based on document context.

2.  **list_column_values**: Use this when the user asks to see all unique values in a specific column of a CSV or Excel file (e.g., "Show all departments", "List all project names from sheet X").
    Input: {"file_name": "example.xlsx", "sheet_name": "Sheet1" (optional), "column_name": "Department"}
    Output: A list of unique values.

3.  **filter_structured_data**: Use this when the user wants to extract specific data from a CSV or Excel file based on conditions (e.g., "Find employees aged 35", "Extract salaries > $50k").
    Input: {"file_name": "example.csv", "sheet_name": "Sheet1" (optional), "query_params": {"column": "Age", "operator": "==", "value": "35"}, "drop_duplicates": true/false (optional), "return_columns": ["Name","Salary"] (optional)}
    Output: A table of results or a message if no results.

4.  **extract_entities**: Use this when the user asks for specific entities like names, dates, or organizations from text.
    Input: User's query.
    Output: List of extracted entities.
"""

# More sophisticated prompt engineering for intent detection and parameter extraction.
# We can guide the LLM to output a JSON object specifying the intent and parameters.

INTENT_PROMPT_TEMPLATE = """
You are an AI assistant that helps users query information from uploaded documents.
Based on the user's query and the available tools, determine the user's intent and the necessary parameters.
If the query is about a CSV or Excel file, pay attention to file names, sheet names (if any), column names, and filter conditions.

Available tools:
{tool_descriptions}

User Query: "{user_query}"

Uploaded files context (summaries of structured files are included if relevant):
{context}

Selected file (if specified): {specified_file}

Based on the query and context, determine the primary intent.
If a specific file is specified, prioritize that file for your query.
If the intent is `list_column_values` or `filter_structured_data`, identify the target file, sheet (if applicable), column, any filter conditions, and (optionally) a list of columns to return (`return_columns`).
If a selected file is specified and is a structured file, assume the query is about that file.
If the intent is general retrieval or entity extraction from text, use `retrieve_general_info` or `extract_entities`.

For queries related to structured data, look for indications about duplicates in the query:
- If the user is asking about specific values or unique entries, include "drop_duplicates": true
- If the user mentions wanting to see all data including duplicates, include "drop_duplicates": false
- By default, assume duplicates should be shown (drop_duplicates: false)

For complex queries with multiple conditions (e.g., "show males with age over 30"), create a list of conditions and include `return_columns` if the user requests specific fields:
{{"intent": "filter_structured_data", "parameters": {{"file_name": "employees.xlsx", "sheet_name": "Q1_Data", "query_params": [
  {{"column": "Gender", "operator": "==", "value": "Male"}},
  {{"column": "Age", "operator": ">", "value": "30"}}
], "drop_duplicates": false, "return_columns": ["Name","Age"]}}}}

Output your decision as a JSON object with "intent" and "parameters" keys.
For example:
{{"intent": "filter_structured_data", "parameters": {{"file_name": "employees.xlsx", "sheet_name": "Q1_Data", "query_params": {{"column": "Salary", "operator": ">", "value": "50000"}}, "drop_duplicates": false}}}}
OR
{{"intent": "filter_structured_data", "parameters": {{"file_name": "employees.xlsx", "sheet_name": "Q1_Data", "query_params": [
  {{"column": "Department", "operator": "==", "value": "Sales"}},
  {{"column": "Salary", "operator": ">", "value": "50000"}}
], "drop_duplicates": false}}}}
OR
{{"intent": "list_column_values", "parameters": {{"file_name": "projects.csv", "column_name": "Project Lead"}}}}
OR
{{"intent": "retrieve_general_info", "parameters": {{"query": "What are the main risks mentioned in project_report.pdf?"}}}}

If you are unsure, or the query is ambiguous, you can ask for clarification or default to `retrieve_general_info`.
If the user asks to list something from a structured file (CSV/Excel), ensure `file_name` and `column_name` are identified for `list_column_values`.
If the user asks to filter/extract from a structured file, ensure `file_name`, `query_params` (with `column`, `operator`, `value`) are identified for `filter_structured_data`.

JSON Response:
"""

def get_qa_chain(user_id: Optional[str] = None):
    llm = get_llm()
    # Pass user_id to get_retriever to filter by user
    retriever = get_retriever(user_id=user_id)
    if not retriever:
        return None # Handle case where vector store is not ready

    # Generic RAG prompt
    prompt_template = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
Keep the answer concise.

Context: {context}

Question: {question}

Helpful Answer:"""
    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff", # or "map_reduce", "refine"
        retriever=retriever,
        chain_type_kwargs={"prompt": PROMPT},
        return_source_documents=True
    )
    return qa_chain

async def process_query(user_query: str, file_context: str = None, user_id: Optional[str] = None):
    llm = get_llm()
    # Pass user_id to filter documents by user
    retriever = get_retriever(user_id=user_id)

    if not retriever:
        return {"answer": "Vector store not initialized. Please upload files first.", "type": "text"}
    
    # 1. Retrieve relevant context for intent detection (optional but can help)
    #    This context can include summaries of structured files.
    #    We want to ensure the LLM knows about available structured files.
    #    The vector store should have summaries of CSV/Excel files (column names, etc.)
    docs_for_intent = retriever.get_relevant_documents(user_query)
    context_for_intent = "\n".join([doc.page_content for doc in docs_for_intent])
    
    # Add info about known structured files if not already in context
    # This part needs access to the list of uploaded structured files.
    # For now, we assume summaries are in the vector store.

    # Check if file_context exists and is valid
    if file_context:
        # Try to load the file to confirm it exists
        try:
            # For structured files, this will load into cache if not present
            structured_file = load_structured_file(file_context, user_id=user_id)
            if structured_file is not None:
                # File exists, add context about this being the selected file
                file_is_structured = True
            else:
                # Not a structured file, but might be a text/PDF file
                # We'll rely on the vector store to find it
                file_is_structured = False
        except Exception:
            # If error loading, it might be a non-structured file or doesn't exist
            file_is_structured = False
    else:
        file_is_structured = False

    # 2. Intent Recognition and Parameter Extraction using LLM
    #    (Simplified version; true function calling with Gemini would be more robust)
    intent_prompt = PromptTemplate(
        template=INTENT_PROMPT_TEMPLATE,
        input_variables=["tool_descriptions", "user_query", "context", "specified_file"]
    )
    
    formatted_intent_prompt = intent_prompt.format(
        tool_descriptions=TOOL_DESCRIPTIONS,
        user_query=user_query,
        context=context_for_intent,
        specified_file=file_context if file_context else "None"
    )
    
    # print(f"DEBUG: Intent Prompt: {formatted_intent_prompt}") # For debugging
    
    try:
        # The LLM should respond with a JSON string
        intent_response_str = await llm.ainvoke(formatted_intent_prompt)
        # Ensure intent_response_str is the actual string content
        if hasattr(intent_response_str, 'content'):
             intent_response_str = intent_response_str.content
        
        # print(f"DEBUG: LLM Raw Intent Response: {intent_response_str}")

        # Clean up the response if it's wrapped in ```json ... ```
        if "```json" in intent_response_str:
            intent_response_str = intent_response_str.split("```json")[1].split("```")[0].strip()
        elif "```" in intent_response_str: # if just ``` at start/end
             intent_response_str = intent_response_str.strip("`").strip()


        intent_data = json.loads(intent_response_str)
        intent = intent_data.get("intent")
        parameters = intent_data.get("parameters", {})
    except Exception as e:
        print(f"Error parsing LLM intent response: {e}. Defaulting to general retrieval.")
        print(f"Problematic LLM response string: {intent_response_str if 'intent_response_str' in locals() else 'N/A'}")
        intent = "retrieve_general_info"
        parameters = {"query": user_query}

    # Check if the query is specifically about duplicates or unique records
    lower_query = user_query.lower()
    has_unique_keywords = any(kw in lower_query for kw in ['unique', 'distinct', 'without duplicates', 'no duplicates'])
    has_duplicate_keywords = any(kw in lower_query for kw in ['including duplicates', 'with duplicates', 'all records', 'all data'])
    
    # Override parameters if query explicitly mentions duplicates/uniqueness
    if intent == "filter_structured_data":
        if has_unique_keywords and 'drop_duplicates' not in parameters:
            parameters['drop_duplicates'] = True
        elif has_duplicate_keywords and 'drop_duplicates' not in parameters:
            parameters['drop_duplicates'] = False
            
    # If a specific file is provided in file_context, override the file_name parameter
    if file_context and (intent == "filter_structured_data" or intent == "list_column_values"):
        parameters["file_name"] = file_context

    # 3. Dispatch to appropriate handler
    if intent == "list_column_values":
        try:
            file_name = parameters.get("file_name")
            column_name = parameters.get("column_name")
            sheet_name = parameters.get("sheet_name") # Might be None
            if not file_name or not column_name:
                raise ValueError("Missing file_name or column_name for list_column_values")
            
            # Verify file exists (load_structured_file will try to load it)
            loaded_file = load_structured_file(file_name, user_id=user_id)  # Loads into cache if not present
            if loaded_file is None:
                 return {"answer": f"File '{file_name}' not found or is not a recognized structured file.", "type": "text"}

            result_list = get_interactive_list(file_name, column_name, sheet_name, user_id=user_id)
            if isinstance(result_list, list) and result_list and "Error:" in result_list[0]:
                return {"answer": result_list[0], "type": "text"} # Propagate error message
            
            return {
                "answer": f"Unique values for '{column_name}' in '{file_name}'" + (f" (sheet: {sheet_name})" if sheet_name else "") + ":",
                "type": "list",
                "data": result_list,
                "file_context": file_name # For potential follow-up or download original
            }
        except Exception as e:
            return {"answer": f"Error processing list request: {str(e)}", "type": "text"}

    elif intent == "filter_structured_data":
        try:
            file_name = parameters.get("file_name")
            query_params = parameters.get("query_params")
            sheet_name = parameters.get("sheet_name") # Might be None
            drop_duplicates = parameters.get("drop_duplicates", False)
            subset = parameters.get("subset", None)  # Optional list of columns for deduplication
            
            # ── 1.  Resolve file_name automatically ────────────────────
            if not file_name:
                # (a) Use the selected file_context if present
                if file_context:
                    file_name = file_context
                else:
                    # (b) Fallback: if exactly one structured file is cached, use it
                    from app.services.data_handler import STRUCTURED_DATA_CACHE
                    if len(STRUCTURED_DATA_CACHE) == 1:
                        file_name = next(iter(STRUCTURED_DATA_CACHE.keys()))
            if not file_name:
                raise ValueError("No structured file found. Please upload a CSV/XLS file first.")
            
            # ── 2.  Treat missing query_params as "no filter" ───────────
            if not query_params:
                query_params = []  # execute_filtered_query will return full DataFrame
                
            # file_name is now guaranteed; query_params can be empty list
            
            # Check if we just want to return specific columns without filtering
            return_columns = parameters.get("return_columns") or parameters.get("columns_to_return")
            
            # Load file to verify it exists
            loaded_file = load_structured_file(file_name, user_id=user_id)
            if loaded_file is None:
                return {"answer": f"File '{file_name}' not found or is not a recognized structured file.", "type": "text"}

            # Execute query with duplicate handling
            print(f"DEBUG: Executing filter query on file {file_name}")
            try:
                result_df = execute_filtered_query(
                    filename=file_name, 
                    query_params=query_params, 
                    sheet_name=sheet_name, 
                    drop_duplicates=drop_duplicates,
                    subset=subset,
                    user_id=user_id
                )
                
                print(f"DEBUG: Query successful, got DataFrame with {len(result_df)} rows")
                
                # ─── OPTIONAL: limit to specific columns ─────────────────
                if return_columns:
                    if isinstance(return_columns, str):
                        return_columns = [return_columns]
                    missing = [c for c in return_columns if c not in result_df.columns]
                    if missing:
                        print(f"WARNING: Requested columns not found in data: {missing}")
                        # Filter out missing columns 
                        return_columns = [c for c in return_columns if c in result_df.columns]
                        if not return_columns:  # If no valid columns remain
                            print("No valid columns to return, using all columns")
                        else:
                            result_df = result_df[return_columns]
                    else:
                        result_df = result_df[return_columns]
                # ─────────────────────────────────────────────────────────
                
                # Verify result_df is not empty
                if result_df.empty:
                    return {
                        "answer": f"No matching data found in '{file_name}' for your query.",
                        "type": "text",
                        "file_context": file_name  # Preserve file context even for empty results
                    }
                
                # Determine download format based on original file extension
                _, original_ext = os.path.splitext(file_name.lower())
                download_filename = f"filtered_{os.path.splitext(file_name)[0]}{original_ext}"
                
                # Adjust the answer based on duplicate handling
                duplicate_info = " (showing unique records)" if drop_duplicates else ""
                
                result_response = {
                    "answer": f"Filtered data from '{file_name}'" + (f" (sheet: {sheet_name})" if sheet_name else "") + 
                             f"{duplicate_info}. Results below:",
                    "type": "table", # Frontend will render this as a table
                    "data": result_df.to_dict(orient="records"), # Send data for frontend table
                    "columns": [str(col) for col in result_df.columns.tolist()],
                    "download_available": True,
                    "download_filename": download_filename, # For /download endpoint
                    "file_context": file_name, # Keep context of original file
                    "query_params_for_download": query_params,
                    "sheet_name_for_download": sheet_name,
                    "drop_duplicates_for_download": drop_duplicates,
                    "subset_for_download": subset,
                    "return_columns_for_download": return_columns if return_columns else None
                }
                
                # Log the response shape for debugging
                print(f"DEBUG: Query response fields: {list(result_response.keys())}")
                print(f"DEBUG: return_columns_for_download value: {result_response['return_columns_for_download']}")
                
                return result_response
            except Exception as e:
                print(f"DEBUG: Execute_filtered_query failed with error: {str(e)}")
                raise
            
        except Exception as e:
            print(f"Error in filter_structured_data: {str(e)}")  # Add debug print
            return {
                "answer": f"Error processing filter request: {str(e)}", 
                "type": "text",
                "file_context": parameters.get("file_name")  # Preserve file context even when error occurs
            }

    # Default to general RAG or if entity extraction is its own path
    # elif intent == "extract_entities":
        # Use a specific LLM prompt for entity extraction using the retrieved context
        # For now, let's fold this into general retrieval or handle as a separate specialized LLM call
        # pass

    # Default: retrieve_general_info (or if intent detection failed)
    qa_chain = get_qa_chain(user_id=user_id)
    if not qa_chain:
        return {"answer": "QA system not ready. Please try again after uploading files.", "type": "text"}
    
    # If parameters contain a specific query from intent detection, use it. Otherwise, use original.
    final_query = parameters.get("query", user_query)
    
    # Check for "number of X" or "count of X" type queries
    lower_query = user_query.lower()
    count_match = False
    
    # First check for total count queries (highest priority)
    simple_count_keywords = ["number of people", "how many people", "count of people", 
                           "number of rows", "how many rows", "count of rows",
                           "number of records", "how many records", "count of records",
                           "number of entries", "how many entries", "count of entries",
                           "total people", "total rows", "total records", "total entries"]
                           
    if any(keyword in lower_query for keyword in simple_count_keywords) or lower_query.strip() in simple_count_keywords:
        if file_context:
            try:
                # Use the already imported load_structured_file function
                data = load_structured_file(file_context, user_id=user_id)
                
                row_count = 0
                if isinstance(data, pd.DataFrame):  # CSV
                    row_count = len(data)
                elif isinstance(data, dict):
                    # Attempt to use a sheet name if the LLM detected one
                    sheet_name_param = parameters.get("sheet_name") if isinstance(parameters, dict) else None
                    if sheet_name_param and sheet_name_param in data:
                        row_count = len(data[sheet_name_param])
                    elif len(data) == 1:
                        # Only one sheet present – count its rows
                        row_count = len(next(iter(data.values())))
                    else:
                        # Multiple sheets and none specified – sum all rows
                        row_count = sum(len(df) for df in data.values())
                
                print(f"DEBUG: Total count query detected, returning {row_count}")
                return {
                    "answer": str(row_count),
                    "type": "text",
                    "file_context": file_context
                }
            except Exception as e:
                print(f"DEBUG: Error counting rows: {str(e)}")
            
    # Now check for specific count queries (gender, etc)
    if "number of " in lower_query or "count of " in lower_query or "how many " in lower_query:
        count_match = True
        
        # For complex queries, we should use the intent recognition to parse multiple conditions
        # rather than trying to directly extract the count target
        
        # Check if the intent system detected multiple conditions (filter_structured_data intent)
        if intent == "filter_structured_data" and file_context:
            print(f"DEBUG: Detected complex count query with multiple conditions: {query_params}")
            
            # Make sure query_params is marked for count_only operation
            # If it's a dict with a single condition
            if isinstance(query_params, dict):
                query_params["count_only"] = True
            # If it's a list of conditions
            elif isinstance(query_params, list) and len(query_params) > 0:
                # Add a new query parameter to the first condition in the list to indicate count only
                # We need to use deepcopy to avoid modifying the original parameters
                modified_params = deepcopy(query_params)
                if isinstance(modified_params[0], dict):
                    modified_params[0]["count_only"] = True
                    
                # Execute filtered query with all conditions
                try:
                    result_df = execute_filtered_query(
                        file_context,
                        modified_params,
                        parameters.get("sheet_name"),
                        drop_duplicates=True  # For counting, we typically want unique records
                    )
                    
                    # Get the count - simply return the number of rows
                    count_value = len(result_df)
                    return {
                        "answer": str(count_value),
                        "type": "text",
                        "file_context": file_context
                    }
                except Exception as e:
                    print(f"DEBUG: Error executing complex count query: {str(e)}")
            
        # Simple extraction for straightforward queries (fallback to previous implementation)
        # Extract what we're counting after the keywords
        count_target = None
        if "number of " in lower_query:
            count_target = lower_query.split("number of ")[1].strip()
        elif "count of " in lower_query:
            count_target = lower_query.split("count of ")[1].strip()
        elif "how many " in lower_query:
            count_target = lower_query.split("how many ")[1].strip()
        
        if count_target and file_context:
            # First check if we need to handle a multi-part count target
            # For example "male employees in France" or "female employees with age > 30"
            parts = count_target.split()
            
            # If it's a simple count like "males" or "females"
            if len(parts) == 1 or (parts[0].lower() in ["male", "female", "males", "females"]):
                # Handle gender specially
                gender_value = None
                if parts[0].lower() in ["male", "males", "men", "man"]:
                    gender_value = "male"
                    column_name = "Gender"
                elif parts[0].lower() in ["female", "females", "women", "woman"]:
                    gender_value = "female"
                    column_name = "Gender"
                    
                # If we have a gender value, try to count it
                if gender_value:
                    try:
                        count_value = count_matching_rows(file_context, column_name, gender_value)
                        return {
                            "answer": str(count_value),
                            "type": "text",
                            "file_context": file_context
                        }
                    except Exception as e:
                        print(f"DEBUG: Error in simple gender count: {str(e)}")
            
            # For more complex queries, tell the user we need to improve the parsing
            return {
                "answer": "I understand you're asking for a count with multiple conditions. Please try separate simple queries for now, or phrase your question like 'show me all male employees from France' to see the full filtered data.",
                "type": "text",
                "file_context": file_context
            }
        
    # If we reach here, no special count handling was done, continue with normal process
    
    try:
        # If a specific file is selected but not handled by structured data operations,
        # we need to filter for documents only from that file
        if file_context:
            # For general RAG queries with a specific file, we need to filter the documents
            # This requires a custom retriever that can filter by source
            # For now, we'll use a simple approach of retrieving more documents than needed
            # and then filtering them manually
            
            raw_docs = retriever.get_relevant_documents(final_query)
            
            # Filter documents to only include those from the specified file
            filtered_docs = [doc for doc in raw_docs if file_context.lower() in doc.metadata.get('source', '').lower()]
            
            if not filtered_docs:
                return {
                    "answer": f"I couldn't find any relevant information in '{file_context}' for your query. "
                              f"Please try a different question or select another file.",
                    "type": "text"
                }
                
            # Create context from filtered docs
            context = "\n".join([doc.page_content for doc in filtered_docs])
            
            # Use the LLM directly with the filtered context
            prompt = f"""Use the following context from the file '{file_context}' to answer the question. 
If you don't know the answer based on this context, say so.

Context: {context}

Question: {final_query}

Answer:"""
            
            answer_result = await llm.ainvoke(prompt)
            if hasattr(answer_result, 'content'):
                answer_result = answer_result.content
                
            return {
                "answer": answer_result,
                "type": "text",
                "file_context": file_context
            }
        else:
            # Standard RAG approach for no specific file
            result = await qa_chain.ainvoke({"query": final_query})
            answer = result.get("result", "No answer found.")
            # source_documents = result.get("source_documents", [])
            # sources_text = "\n".join([f"- {doc.metadata.get('source', 'Unknown')}" for doc in source_documents])
            # full_answer = f"{answer}\n\nSources:\n{sources_text}"
            return {"answer": answer, "type": "text"} #, "sources": sources_text}
    except Exception as e:
        print(f"Error during RAG chain execution: {e}")
        return {"answer": f"An error occurred while processing your request: {str(e)}", "type": "text"}

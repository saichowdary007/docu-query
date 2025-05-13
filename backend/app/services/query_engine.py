from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from app.services.nlp_service import get_llm
from app.services.vector_store import get_retriever
from app.services.data_handler import get_interactive_list, execute_filtered_query, load_structured_file
import json
import os

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
    Input: {"file_name": "example.csv", "sheet_name": "Sheet1" (optional), "query_params": {"column": "Age", "operator": "==", "value": "35"}}
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

Based on the query and context, determine the primary intent.
If the intent is `list_column_values` or `filter_structured_data`, identify the target file, sheet (if applicable), column, and any filter conditions.
If the intent is general retrieval or entity extraction from text, use `retrieve_general_info` or `extract_entities`.

Output your decision as a JSON object with "intent" and "parameters" keys.
For example:
{{"intent": "filter_structured_data", "parameters": {{"file_name": "employees.xlsx", "sheet_name": "Q1_Data", "query_params": {{"column": "Salary", "operator": ">", "value": "50000"}}}}}}
OR
{{"intent": "list_column_values", "parameters": {{"file_name": "projects.csv", "column_name": "Project Lead"}}}}
OR
{{"intent": "retrieve_general_info", "parameters": {{"query": "What are the main risks mentioned in project_report.pdf?"}}}}

If you are unsure, or the query is ambiguous, you can ask for clarification or default to `retrieve_general_info`.
If the user asks to list something from a structured file (CSV/Excel), ensure `file_name` and `column_name` are identified for `list_column_values`.
If the user asks to filter/extract from a structured file, ensure `file_name`, `query_params` (with `column`, `operator`, `value`) are identified for `filter_structured_data`.

JSON Response:
"""

def get_qa_chain():
    llm = get_llm()
    retriever = get_retriever()
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

async def process_query(user_query: str):
    llm = get_llm()
    retriever = get_retriever()

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

    # 2. Intent Recognition and Parameter Extraction using LLM
    #    (Simplified version; true function calling with Gemini would be more robust)
    intent_prompt = PromptTemplate(
        template=INTENT_PROMPT_TEMPLATE,
        input_variables=["tool_descriptions", "user_query", "context"]
    )
    
    formatted_intent_prompt = intent_prompt.format(
        tool_descriptions=TOOL_DESCRIPTIONS,
        user_query=user_query,
        context=context_for_intent
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


    # 3. Dispatch to appropriate handler
    if intent == "list_column_values":
        try:
            file_name = parameters.get("file_name")
            column_name = parameters.get("column_name")
            sheet_name = parameters.get("sheet_name") # Might be None
            if not file_name or not column_name:
                raise ValueError("Missing file_name or column_name for list_column_values")
            
            # Verify file exists (load_structured_file will try to load it)
            # This is a simplified check; ideally, maintain a list of uploaded structured files.
            if not load_structured_file(file_name): # This loads into cache if not present
                 return {"answer": f"File '{file_name}' not found or is not a recognized structured file.", "type": "text"}

            result_list = get_interactive_list(file_name, column_name, sheet_name)
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

            if not file_name or not query_params:
                raise ValueError("Missing file_name or query_params for filter_structured_data")
            
            if not load_structured_file(file_name):
                 return {"answer": f"File '{file_name}' not found or is not a recognized structured file.", "type": "text"}

            result_df = execute_filtered_query(file_name, query_params, sheet_name)
            
            # Determine download format based on original file extension
            _, original_ext = os.path.splitext(file_name.lower())
            download_filename = f"filtered_{os.path.splitext(file_name)[0]}{original_ext}"
            
            return {
                "answer": f"Filtered data from '{file_name}'" + (f" (sheet: {sheet_name})" if sheet_name else "") + ". Results below:",
                "type": "table", # Frontend will render this as a table
                "data": result_df.to_dict(orient="records"), # Send data for frontend table
                "columns": [str(col) for col in result_df.columns.tolist()],
                "download_available": True,
                "download_filename": download_filename, # For /download endpoint
                "file_context": file_name, # Keep context of original file
                "query_params_for_download": query_params,
                "sheet_name_for_download": sheet_name
            }
        except Exception as e:
            return {"answer": f"Error processing filter request: {str(e)}", "type": "text"}

    # Default to general RAG or if entity extraction is its own path
    # elif intent == "extract_entities":
        # Use a specific LLM prompt for entity extraction using the retrieved context
        # For now, let's fold this into general retrieval or handle as a separate specialized LLM call
        # pass

    # Default: retrieve_general_info (or if intent detection failed)
    qa_chain = get_qa_chain()
    if not qa_chain:
        return {"answer": "QA system not ready. Please try again after uploading files.", "type": "text"}
    
    # If parameters contain a specific query from intent detection, use it. Otherwise, use original.
    final_query = parameters.get("query", user_query)
    
    try:
        result = await qa_chain.ainvoke({"query": final_query}) # Langchain runs this async
        answer = result.get("result", "No answer found.")
        # source_documents = result.get("source_documents", [])
        # sources_text = "\n".join([f"- {doc.metadata.get('source', 'Unknown')}" for doc in source_documents])
        # full_answer = f"{answer}\n\nSources:\n{sources_text}"
        return {"answer": answer, "type": "text"} #, "sources": sources_text}
    except Exception as e:
        print(f"Error during RAG chain execution: {e}")
        return {"answer": f"An error occurred while processing your request: {str(e)}", "type": "text"}

import json
import os
from copy import deepcopy

import pandas as pd
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from sqlalchemy.orm import Session

from docuquery_ai.models.db_models import File
from docuquery_ai.models.pydantic_models import QueryRequest, QueryResponse
from docuquery_ai.services.data_handler import (
    count_matching_rows,
    execute_filtered_query,
    get_interactive_list,
    load_structured_file,
)
from docuquery_ai.services.nlp_service import get_llm
from docuquery_ai.services.vector_store import get_retriever

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


def get_qa_chain():
    llm = get_llm()
    retriever = get_retriever()
    if not retriever:
        return None  # Handle case where vector store is not ready

    # Generic RAG prompt
    prompt_template = """Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
Keep the answer concise.

Context: {context}

Question: {question}

Helpful Answer:"""
    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",  # or "map_reduce", "refine"
        retriever=retriever,
        chain_type_kwargs={"prompt": PROMPT},
        return_source_documents=True,
    )
    return qa_chain


async def process_query(
    query_request: QueryRequest, user_id: str, db: Session
) -> QueryResponse:
    llm = get_llm()
    retriever = get_retriever()
    user_query = query_request.question
    file_ids = query_request.file_ids

    if not retriever:
        return QueryResponse(
            answer="Vector store not initialized. Please upload files first.",
            type="text",
        )

    # 1. Build context for the LLM, including file list
    user_files = db.query(File).filter(File.user_id == user_id).all()
    file_context_str = "\n".join(
        [
            f"- {f.filename} (type: {'structured' if f.is_structured else 'unstructured'})"
            for f in user_files
        ]
    )

    # Check if a specific file is being targeted
    specified_file_info = "None"
    if file_ids:
        # For simplicity, we handle the first specified file ID. Multi-file context can be complex.
        target_file = (
            db.query(File)
            .filter(File.id == file_ids[0], File.user_id == user_id)
            .first()
        )
        if target_file:
            specified_file_info = f"{target_file.filename} (type: {'structured' if target_file.is_structured else 'unstructured'})"

    # 2. Intent Recognition
    intent_prompt = PromptTemplate(
        template=INTENT_PROMPT_TEMPLATE,
        input_variables=[
            "tool_descriptions",
            "user_query",
            "context",
            "specified_file",
        ],
    )

    formatted_intent_prompt = intent_prompt.format(
        tool_descriptions=TOOL_DESCRIPTIONS,
        user_query=user_query,
        context=file_context_str,
        specified_file=specified_file_info,
    )

    try:
        intent_response = await llm.ainvoke(formatted_intent_prompt)
        intent_response_str = intent_response.content

        if "```json" in intent_response_str:
            intent_response_str = (
                intent_response_str.split("```json")[1].split("```")[0].strip()
            )
        elif "```" in intent_response_str:
            intent_response_str = intent_response_str.strip("`").strip()

        intent_data = json.loads(intent_response_str)
        intent = intent_data.get("intent")
        parameters = intent_data.get("parameters", {})
    except Exception as e:
        print(
            f"Error parsing LLM intent response: {e}. Defaulting to general retrieval."
        )
        intent = "retrieve_general_info"
        parameters = {"query": user_query}

    # If a specific file is targeted, ensure it's used as the file_name
    if specified_file_info != "None" and "file_name" not in parameters:
        if intent in ["filter_structured_data", "list_column_values"]:
            parameters["file_name"] = specified_file_info.split(" (")[0]

    # 3. Dispatch to appropriate handler
    if intent == "list_column_values":
        try:
            file_name = parameters.get("file_name")
            if not file_name:
                return QueryResponse(
                    answer="Could not determine the target file for the query. Please specify the file.",
                    type="text",
                )

            # Verify this file belongs to the user
            file_record = (
                db.query(File)
                .filter(File.filename == file_name, File.user_id == user_id)
                .first()
            )
            if not file_record:
                return QueryResponse(
                    answer=f"File '{file_name}' not found for the current user.",
                    type="text",
                )

            column_name = parameters.get("column_name")
            sheet_name = parameters.get("sheet_name")
            if not column_name:
                raise ValueError("Missing column_name for list_column_values")

            result_list = get_interactive_list(
                file_record.file_path, column_name, sheet_name
            )

            return QueryResponse(
                answer=f"Unique values for '{column_name}' in '{file_name}':",
                type="list",
                data=result_list,
                file_context=file_name,
            )
        except Exception as e:
            return QueryResponse(
                answer=f"Error processing list request: {str(e)}", type="text"
            )

    elif intent == "filter_structured_data":
        try:
            file_name = parameters.get("file_name")
            if not file_name:
                return QueryResponse(
                    answer="Could not determine the target file for the query. Please specify the file.",
                    type="text",
                )

            # Verify this file belongs to the user
            file_record = (
                db.query(File)
                .filter(File.filename == file_name, File.user_id == user_id)
                .first()
            )
            if not file_record:
                return QueryResponse(
                    answer=f"File '{file_name}' not found for the current user.",
                    type="text",
                )

            df = execute_filtered_query(
                file_path=file_record.file_path,
                query_params=parameters.get("query_params"),
                sheet_name=parameters.get("sheet_name"),
                drop_duplicates=parameters.get("drop_duplicates", False),
                subset=parameters.get("subset"),
                return_columns=parameters.get("return_columns"),
            )

            # Check if DataFrame is empty
            if df.empty:
                return QueryResponse(
                    answer="No matching data found for your query.", type="text"
                )

            return QueryResponse(
                answer=f"Filtered data from '{file_name}':",
                type="table",
                data=df.to_dict(orient="records"),
                columns=df.columns.tolist(),
                download_available=True,
                download_filename=f"filtered_{file_name.replace('.csv', '').replace('.xlsx', '')}.csv",
                file_context=file_name,
                query_params_for_download=parameters.get("query_params"),
            )
        except Exception as e:
            return QueryResponse(
                answer=f"Error processing data filtering request: {str(e)}", type="text"
            )

    else:  # Default to RAG
        qa_chain = get_qa_chain()
        if not qa_chain:
            return QueryResponse(
                answer="Vector store not initialized. Please upload files first.",
                type="text",
            )

        result = qa_chain({"question": user_query})

        sources = "\n".join(
            [
                os.path.basename(doc.metadata.get("source", "Unknown"))
                for doc in result.get("source_documents", [])
            ]
        )

        return QueryResponse(
            answer=result.get("result", "No answer found."),
            sources=sources,
            type="text",
        )

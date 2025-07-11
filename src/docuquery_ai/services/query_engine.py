import os
from copy import deepcopy
from typing import Any, Dict, List, Optional, Union

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
from docuquery_ai.services.nlp_service import get_llm, get_embeddings_model
from docuquery_ai.services.vector_store import get_retriever
from docuquery_ai.services.graph_service import get_knowledge_graph

# New imports for structured output
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

# Define Pydantic models for structured output
class RetrieveGeneralInfo(BaseModel):
    """Use this for general questions about the content of uploaded documents."""
    query: str = Field(description="User's query.")

class ListColumnValues(BaseModel):
    """Use this when the user asks to see all unique values in a specific column of a CSV or Excel file."""
    file_name: str = Field(description="Name of the CSV or Excel file.")
    column_name: str = Field(description="Name of the column to list values from.")
    sheet_name: Optional[str] = Field(None, description="Name of the sheet for Excel files.")

class QueryParamItem(BaseModel):
    column: str = Field(description="Column name for filtering.")
    operator: str = Field(description="Comparison operator (e.g., '==', '>', '<', 'contains').")
    value: Any = Field(description="Value to compare against.")

class FilterStructuredData(BaseModel):
    """Use this when the user wants to extract specific data from a CSV or Excel file based on conditions."""
    file_name: str = Field(description="Name of the CSV or Excel file.")
    query_params: Union[QueryParamItem, List[QueryParamItem]] = Field(description="Filtering conditions. Can be a single condition or a list of conditions.")
    sheet_name: Optional[str] = Field(None, description="Name of the sheet for Excel files.")
    drop_duplicates: Optional[bool] = Field(False, description="Whether to drop duplicate rows. Default to false if not specified.")
    subset: Optional[List[str]] = Field(None, description="List of columns to consider when dropping duplicates.")
    return_columns: Optional[List[str]] = Field(None, description="List of columns to return from the filtered data.")

class ExtractEntities(BaseModel):
    """Use this when the user asks for specific entities like names, dates, or organizations from text."""
    query: str = Field(description="User's query.")

class GraphQuery(BaseModel):
    """Use this when the user asks questions that require understanding relationships between entities across documents, such as 'Who worked on Project X?' or 'What documents mention both A and B?'."
    query: str = Field(description="The natural language query that can be translated into a graph traversal.")
    entities: Optional[List[str]] = Field(None, description="List of key entities mentioned in the query that might be nodes in the graph.")
    relationships: Optional[List[str]] = Field(None, description="List of potential relationship types to look for in the graph.")

# Union of all possible structured outputs
IntentOutput = Union[RetrieveGeneralInfo, ListColumnValues, FilterStructuredData, ExtractEntities, GraphQuery]

def get_qa_chain(vector_store, bm25_retriever, knowledge_graph):
    llm = get_llm()
    embeddings = get_embeddings_model()
    retriever = get_retriever(vector_store, bm25_retriever, llm, embeddings, knowledge_graph)
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
    query_request: QueryRequest, user_id: str, db: Session, file_ids: Optional[list[str]] = None, vector_store=None, bm25_retriever=None
) -> QueryResponse:
    llm = get_llm()
    knowledge_graph = get_knowledge_graph()
    retriever = get_retriever(vector_store, bm25_retriever, llm, get_embeddings_model(), knowledge_graph)
    user_query = query_request.query
    

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

    # 2. Intent Recognition using structured output
    # Define the LLM with structured output
    structured_llm = llm.with_structured_output(IntentOutput)

    # Create the prompt for the structured LLM
    messages = [
        SystemMessage(
            content=(
                "You are an AI assistant that helps users query information from uploaded documents. "
                "Based on the user's query and the available tools, determine the user's intent and the necessary parameters. "
                "If the query is about a CSV or Excel file, pay attention to file names, sheet names (if any), column names, and filter conditions. "
                "If the query involves relationships between entities (e.g., 'Who worked on Project X?', 'Documents by Author Y'), consider the `GraphQuery` tool. "
                "If you are unsure, or the query is ambiguous, default to `RetrieveGeneralInfo`."
            )
        ),
        HumanMessage(
            content=(
                f"Uploaded files context:\n{file_context_str}\n\n"
                f"Selected file (if specified): {specified_file_info}\n\n"
                f"User Query: {user_query}"
            )
        ),
    ]

    try:
        # Invoke the structured LLM
        intent_output_model = await structured_llm.ainvoke(messages)

        # Extract intent and parameters from the Pydantic model
        intent = type(intent_output_model).__name__
        parameters = intent_output_model.dict()

    except Exception as e:
        print(
            f"Error with LLM structured output: {e}. Defaulting to general retrieval."
        )
        intent = "RetrieveGeneralInfo"
        parameters = {"query": user_query}

    # Map Pydantic model names to the existing intent strings
    intent_mapping = {
        "RetrieveGeneralInfo": "retrieve_general_info",
        "ListColumnValues": "list_column_values",
        "FilterStructuredData": "filter_structured_data",
        "ExtractEntities": "extract_entities",
        "GraphQuery": "graph_query",
    }
    intent = intent_mapping.get(intent, "retrieve_general_info")

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

            # Convert QueryParamItem objects to dictionaries for execute_filtered_query
            query_params_from_llm = parameters.get("query_params")
            if isinstance(query_params_from_llm, QueryParamItem):
                parameters["query_params"] = query_params_from_llm.dict()
            elif isinstance(query_params_from_llm, list):
                parameters["query_params"] = [qp.dict() for qp in query_params_from_llm]

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

    elif intent == "graph_query":
        try:
            knowledge_graph = get_knowledge_graph()
            graph_query_text = parameters.get("query", "")
            graph_entities = parameters.get("entities", [])
            graph_relationships = parameters.get("relationships", [])

            # Simple graph traversal logic for demonstration
            # In a real scenario, this would involve more complex graph query translation
            # and traversal based on the user's query and extracted entities/relationships.
            results = []
            if graph_entities:
                for entity_name in graph_entities:
                    # Search for nodes matching the entity name
                    found_nodes = knowledge_graph.search_nodes(entity_name)
                    for node in found_nodes:
                        results.append(f"Found entity: {node['properties'].get('name')} (Type: {node['properties'].get('type')})")
                        # For each found node, list its immediate connections
                        for u, v, data in knowledge_graph.get_edges(node['id']):
                            target_node = knowledge_graph.get_node(v)
                            if target_node:
                                results.append(f"  - {node['properties'].get('name')} -[{data.get('type')}]-> {target_node.get('name')}")
            elif graph_relationships:
                results.append("Graph relationship queries are not fully supported yet. Please try a more specific entity-based query.")
            else:
                results.append("Please specify entities or relationships for a graph query.")

            if not results:
                results.append("No relevant information found in the knowledge graph.")

            return QueryResponse(
                answer="\n".join(results),
                type="text",
                file_context="Knowledge Graph",
            )
        except Exception as e:
            return QueryResponse(
                answer=f"Error processing graph query: {str(e)}", type="text"
            )

    else:  # Default to RAG
        qa_chain = get_qa_chain(vector_store, bm25_retriever)
        if not qa_chain:
            return QueryResponse(
                answer="Vector store not initialized. Please upload files first.",
                type="text",
            )

        result = qa_chain.invoke({"query": user_query})

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

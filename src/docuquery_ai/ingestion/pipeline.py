import logging
import os
from typing import List

from docuquery_ai.exceptions import IngestionError, UnsupportedFileType

from ..db.models import Document
from .embedding import EmbeddingGenerator
from .ner import NER
from .parser import parse_csv, parse_docx, parse_excel, parse_md, parse_pdf, parse_pptx

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Orchestrates the document ingestion process, including parsing, embedding generation,
    and named entity recognition.
    """

    def __init__(self):
        """
        Initializes the IngestionPipeline with an EmbeddingGenerator and NER component.
        """
        self.embedding_generator = EmbeddingGenerator()
        self.ner = NER()

    async def ingest_file(self, file_path: str, filename: str) -> Document:
        """
        Processes a single file through the ingestion pipeline.

        Args:
            file_path: The absolute path to the file to ingest.
            filename: The name of the file.

        Returns:
            A Document object containing the processed content, embeddings, and entities.

        Raises:
            UnsupportedFileType: If the file type is not supported.
            IngestionError: If an error occurs during ingestion.
        """
        _, ext = os.path.splitext(filename.lower())
        content = ""
        metadata = {"source": filename, "file_type": ext}

        try:
            if ext == ".docx":
                content = parse_docx(file_path)
            elif ext == ".pptx":
                content = parse_pptx(file_path)
            elif ext == ".pdf":
                content = parse_pdf(file_path)
            elif ext == ".md":
                content = parse_md(file_path)
            elif ext == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif ext == ".csv":
                df = parse_csv(file_path)
                content = df.to_string()  # Convert DataFrame to string for embedding
                metadata["is_structured"] = True
                metadata["structure_type"] = "csv"
            elif ext in [".xls", ".xlsx"]:
                excel_data = parse_excel(file_path)
                content_parts = []
                for sheet_name, df in excel_data.items():
                    content_parts.append(f"Sheet {sheet_name}:\n{df.to_string()}")
                content = "\n".join(content_parts)
                metadata["is_structured"] = True
                metadata["structure_type"] = "excel"
            else:
                logger.warning(f"Unsupported file type encountered: {ext}")
                raise UnsupportedFileType(f"File type {ext} is not supported.")

            embeddings = await self.embedding_generator.generate_embeddings(content)
            entities = await self.ner.extract_entities(content)

            logger.info(f"Successfully processed file: {filename}")
            return Document(
                id=filename,
                title=filename,
                content=content,
                metadata=metadata,
                embeddings=embeddings,
                entities=entities,
                relationships=[],
                knowledge_triples=[],
            )
        except UnsupportedFileType:
            raise  # Re-raise the specific exception
        except (ValueError, IOError) as exc:
            logger.error("Error processing file %s: %s", filename, exc, exc_info=True)
            raise IngestionError(f"Failed to process file {filename}: {exc}") from exc

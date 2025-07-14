import csv
import os
from typing import Any, Dict, List

import markdown
import pandas as pd
from docx import Document as DocxDocument
from pptx import Presentation
from pypdf import PdfReader

from docuquery_ai.core.config import settings

# Ensure temp_uploads directory exists
os.makedirs(settings.TEMP_UPLOAD_FOLDER, exist_ok=True)


def parse_docx(file_path: str) -> str:
    """
    Parses a DOCX file and extracts its text content.

    Args:
        file_path: The absolute path to the DOCX file.

    Returns:
        The extracted text content as a string.
    """
    doc = DocxDocument(file_path)
    return "\n".join([para.text for para in doc.paragraphs])


def parse_pptx(file_path: str) -> str:
    """
    Parses a PPTX file and extracts its text content from all slides.

    Args:
        file_path: The absolute path to the PPTX file.

    Returns:
        The extracted text content as a string.
    """
    prs = Presentation(file_path)
    text_runs = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    text_runs.append(run.text)
    return "\n".join(text_runs)


def parse_pdf(file_path: str) -> str:
    """
    Parse PDF and extract text with robust error handling and fallback methods.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text content from the PDF
    """
    try:
        # First try the standard method
        reader = PdfReader(file_path)

        # Check if the PDF is encrypted
        if reader.is_encrypted:
            try:
                # Try with empty password (some PDFs can be accessed this way)
                reader.decrypt("")
                logger.warning(
                    "Successfully decrypted PDF with empty password: %s",
                    file_path,
                )
            except (ValueError, IOError) as exc:
                logger.warning("Cannot decrypt PDF %s: %s", file_path, str(exc))
                return f"[This PDF is encrypted and could not be processed: {os.path.basename(file_path)}]"

        # Extract text from each page with better error handling
        text = ""
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                text += page_text
                # If page is empty, add a note
                if not page_text.strip():
                    logger.warning(
                        "Empty or non-text content on page %s in %s",
                        i + 1,
                        file_path,
                    )
            except (ValueError, IOError) as page_e:
                logger.warning(
                    "Error extracting text from page %s in %s: %s",
                    i + 1,
                    file_path,
                    str(page_e),
                )
                text += f"\n[Error extracting text from page {i+1}]\n"

        # If we got no text at all, try a fallback method
        if not text.strip():
            logger.warning(
                "No text extracted from %s. Attempting fallback method.", file_path
            )
            # We could implement alternative extraction here if needed
            # e.g., using a different library or OCR for scanned PDFs
            text = f"[This document appears to contain no extractable text or may be a scanned PDF: {os.path.basename(file_path)}]"

        return text

    except (ValueError, IOError) as e:
        logger.error("Error parsing PDF %s: %s", file_path, str(e))
        # Return a placeholder so the document's not completely lost
        return f"[Error processing PDF document: {os.path.basename(file_path)}. Error: {str(e)}]"


def parse_csv(file_path: str) -> pd.DataFrame:
    """
    Parses a CSV file into a pandas DataFrame.

    Args:
        file_path: The absolute path to the CSV file.

    Returns:
        A pandas DataFrame containing the CSV data.
    """
    # For RAG, we might convert CSV rows to text or handle structured queries separately
    return pd.read_csv(file_path)


def parse_excel(file_path: str) -> Dict[str, pd.DataFrame]:
    """
    Parses an Excel file into a dictionary of pandas DataFrames, where keys are sheet names.

    Args:
        file_path: The absolute path to the Excel file.

    Returns:
        A dictionary where keys are sheet names and values are pandas DataFrames.
    """
    # Returns a dictionary of sheet_name: dataframe
    return pd.read_excel(file_path, sheet_name=None)


def parse_md(file_path: str) -> str:
    """
    Parses a Markdown file and converts its content to HTML.

    Args:
        file_path: The absolute path to the Markdown file.

    Returns:
        The HTML content as a string.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return markdown.markdown(f.read())

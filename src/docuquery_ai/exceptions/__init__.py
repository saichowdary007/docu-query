class DocumentQueryError(Exception):
    """Base exception for DocuQuery AI errors."""

    pass


class DocumentNotFound(DocumentQueryError):
    """Exception raised when a document is not found."""

    pass


class UnsupportedFileType(DocumentQueryError):
    """Exception raised for unsupported file types during ingestion."""

    pass


class DatabaseConnectionError(DocumentQueryError):
    """Exception raised for database connection issues."""

    pass


class IngestionError(DocumentQueryError):
    """Exception raised during the document ingestion process."""

    pass


class QueryError(DocumentQueryError):
    """Exception raised during query execution."""

    pass

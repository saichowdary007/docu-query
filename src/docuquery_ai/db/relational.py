import logging
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional SQLAlchemy dependency
    from sqlalchemy import Boolean, Column, DateTime, String, Text, create_engine
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import declarative_base, sessionmaker
    SQLALCHEMY_AVAILABLE = True
except Exception:  # pragma: no cover - fall back to in-memory store
    SQLALCHEMY_AVAILABLE = False

from datetime import datetime, timezone
from docuquery_ai.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()

    class DocumentRecord(Base):
        __tablename__ = "documents"
        id = Column(String, primary_key=True, index=True)
        title = Column(String, index=True)
        content = Column(Text)
        file_path = Column(String)
        file_type = Column(String)
        user_id = Column(String, index=True)
        is_structured = Column(Boolean, default=False)
        structure_type = Column(String, nullable=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
else:
    # Minimal stand-in when SQLAlchemy is unavailable
    class DocumentRecord(dict):
        pass
    Base = object

class RelationalDBManager:
    def __init__(self, db_url: str = "sqlite:///:memory:"):
        """Initialise relational storage.

        If SQLAlchemy is available, use it with an in-memory SQLite database by
        default. Otherwise fall back to a simple in-memory dictionary. This keeps
        unit tests running even when optional dependencies are missing.
        """
        self.db_url = db_url
        if SQLALCHEMY_AVAILABLE:
            try:
                self.engine = create_engine(db_url)
                self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                Base.metadata.create_all(bind=self.engine)
                logger.info("RelationalDBManager initialised using SQLAlchemy")
            except SQLAlchemyError as e:
                logger.error(f"Error connecting to relational database: {e}", exc_info=True)
                raise DatabaseConnectionError(f"Failed to connect to relational database: {e}") from e
        else:  # pragma: no cover - simplified in-memory implementation
            self._records: Dict[str, Dict[str, Any]] = {}
            logger.info("RelationalDBManager initialised using in-memory store")

    async def recreate_tables(self):
        """Reset the storage backend."""
        if SQLALCHEMY_AVAILABLE:
            try:
                Base.metadata.drop_all(bind=self.engine)
                Base.metadata.create_all(bind=self.engine)
                logger.info("Relational database tables recreated.")
            except SQLAlchemyError as e:
                logger.error(f"Error recreating relational database tables: {e}", exc_info=True)
                raise DatabaseConnectionError(f"Failed to recreate tables: {e}") from e
        else:  # pragma: no cover - simple reset
            self._records.clear()

    def get_db(self):
        if not SQLALCHEMY_AVAILABLE:
            raise RuntimeError("Database sessions require SQLAlchemy")
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def create_document_record(
        self,
        doc_id: str,
        title: str,
        content: str,
        file_path: str,
        file_type: str,
        user_id: str,
        is_structured: bool = False,
        structure_type: Optional[str] = None,
    ) -> DocumentRecord:
        if SQLALCHEMY_AVAILABLE:
            try:
                db = next(self.get_db())
                db_record = DocumentRecord(
                    id=doc_id,
                    title=title,
                    content=content,
                    file_path=file_path,
                    file_type=file_type,
                    user_id=user_id,
                    is_structured=is_structured,
                    structure_type=structure_type,
                )
                db.add(db_record)
                db.commit()
                db.refresh(db_record)
                logger.info(f"Created document record: {doc_id}")
                return db_record
            except SQLAlchemyError as e:
                logger.error(
                    f"Error creating document record {doc_id}: {e}", exc_info=True
                )
                raise DatabaseConnectionError(
                    f"Failed to create document record: {e}"
                ) from e
        else:  # pragma: no cover - store in dictionary
            record = {
                "id": doc_id,
                "title": title,
                "content": content,
                "file_path": file_path,
                "file_type": file_type,
                "user_id": user_id,
                "is_structured": is_structured,
                "structure_type": structure_type,
            }
            self._records[doc_id] = record
            logger.info(f"Created document record: {doc_id}")
            return DocumentRecord(**record)

    async def get_document_record(self, doc_id: str) -> Optional[DocumentRecord]:
        if SQLALCHEMY_AVAILABLE:
            try:
                db = next(self.get_db())
                record = (
                    db.query(DocumentRecord)
                    .filter(DocumentRecord.id == doc_id)
                    .first()
                )
                if not record:
                    logger.warning(f"Document record {doc_id} not found.")
                return record
            except SQLAlchemyError as e:
                logger.error(
                    f"Error getting document record {doc_id}: {e}", exc_info=True
                )
                raise DatabaseConnectionError(
                    f"Failed to get document record: {e}"
                ) from e
        else:  # pragma: no cover
            return self._records.get(doc_id)

    async def delete_document_record(self, doc_id: str) -> bool:
        if SQLALCHEMY_AVAILABLE:
            try:
                db = next(self.get_db())
                db_record = (
                    db.query(DocumentRecord)
                    .filter(DocumentRecord.id == doc_id)
                    .first()
                )
                if db_record:
                    db.delete(db_record)
                    db.commit()
                    logger.info(f"Deleted document record: {doc_id}")
                    return True
                logger.warning(
                    f"Attempted to delete non-existent document record: {doc_id}"
                )
                return False
            except SQLAlchemyError as e:
                logger.error(
                    f"Error deleting document record {doc_id}: {e}", exc_info=True
                )
                raise DatabaseConnectionError(
                    f"Failed to delete document record: {e}"
                ) from e
        else:  # pragma: no cover
            existed = doc_id in self._records
            self._records.pop(doc_id, None)
            if existed:
                logger.info(f"Deleted document record: {doc_id}")
            else:
                logger.warning(
                    f"Attempted to delete non-existent document record: {doc_id}"
                )
            return existed

    async def search_documents(self, query: str) -> List[Dict[str, Any]]:
        if SQLALCHEMY_AVAILABLE:
            try:
                db = next(self.get_db())
                # Simple keyword search for demonstration
                results = (
                    db.query(DocumentRecord)
                    .filter(DocumentRecord.content.contains(query))
                    .all()
                )
                logger.info(
                    f"Found {len(results)} relational documents for query: {query}"
                )
                return [
                    {
                        "id": doc.id,
                        "title": doc.title,
                        "content": doc.content,
                        "file_type": doc.file_type,
                        "user_id": doc.user_id,
                    }
                    for doc in results
                ]
            except SQLAlchemyError as e:
                logger.error(
                    f"Error searching relational documents for {query}: {e}",
                    exc_info=True,
                )
                raise DatabaseConnectionError(
                    f"Failed to search relational documents: {e}"
                ) from e
        else:  # pragma: no cover
            results = [
                record
                for record in self._records.values()
                if query in record.get("content", "")
            ]
            logger.info(
                f"Found {len(results)} relational documents for query: {query}"
            )
            return results

    def dispose(self):
        if SQLALCHEMY_AVAILABLE:
            self.engine.dispose()
        else:  # pragma: no cover
            self._records.clear()
        logger.info("RelationalDBManager engine disposed.")

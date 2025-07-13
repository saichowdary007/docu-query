import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from docuquery_ai.exceptions import DatabaseConnectionError, DocumentNotFound

logger = logging.getLogger(__name__)

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

class RelationalDBManager:
    def __init__(self, db_url: str = "sqlite:///:memory:"):
        try:
            self.engine = create_engine(db_url)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            Base.metadata.create_all(bind=self.engine)
            logger.info(f"RelationalDBManager initialized with DB: {db_url}")
        except SQLAlchemyError as e:
            logger.error(f"Error connecting to relational database: {e}", exc_info=True)
            raise DatabaseConnectionError(f"Failed to connect to relational database: {e}") from e

    async def recreate_tables(self):
        try:
            Base.metadata.drop_all(bind=self.engine)
            Base.metadata.create_all(bind=self.engine)
            logger.info("Relational database tables recreated.")
        except SQLAlchemyError as e:
            logger.error(f"Error recreating relational database tables: {e}", exc_info=True)
            raise DatabaseConnectionError(f"Failed to recreate tables: {e}") from e

    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def create_document_record(self, doc_id: str, title: str, content: str, file_path: str, file_type: str, user_id: str, is_structured: bool = False, structure_type: Optional[str] = None) -> DocumentRecord:
        try:
            db = next(self.get_db())
            db_record = DocumentRecord(id=doc_id, title=title, content=content, file_path=file_path, file_type=file_type, user_id=user_id, is_structured=is_structured, structure_type=structure_type)
            db.add(db_record)
            db.commit()
            db.refresh(db_record)
            logger.info(f"Created document record: {doc_id}")
            return db_record
        except SQLAlchemyError as e:
            logger.error(f"Error creating document record {doc_id}: {e}", exc_info=True)
            raise DatabaseConnectionError(f"Failed to create document record: {e}") from e

    async def get_document_record(self, doc_id: str) -> Optional[DocumentRecord]:
        try:
            db = next(self.get_db())
            record = db.query(DocumentRecord).filter(DocumentRecord.id == doc_id).first()
            if not record:
                logger.warning(f"Document record {doc_id} not found.")
            return record
        except SQLAlchemyError as e:
            logger.error(f"Error getting document record {doc_id}: {e}", exc_info=True)
            raise DatabaseConnectionError(f"Failed to get document record: {e}") from e

    async def delete_document_record(self, doc_id: str) -> bool:
        try:
            db = next(self.get_db())
            db_record = db.query(DocumentRecord).filter(DocumentRecord.id == doc_id).first()
            if db_record:
                db.delete(db_record)
                db.commit()
                logger.info(f"Deleted document record: {doc_id}")
                return True
            logger.warning(f"Attempted to delete non-existent document record: {doc_id}")
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting document record {doc_id}: {e}", exc_info=True)
            raise DatabaseConnectionError(f"Failed to delete document record: {e}") from e

    async def search_documents(self, query: str) -> List[Dict[str, Any]]:
        try:
            db = next(self.get_db())
            # Simple keyword search for demonstration
            results = db.query(DocumentRecord).filter(DocumentRecord.content.contains(query)).all()
            logger.info(f"Found {len(results)} relational documents for query: {query}")
            return [{
                "id": doc.id,
                "title": doc.title,
                "content": doc.content,
                "file_type": doc.file_type,
                "user_id": doc.user_id
            } for doc in results]
        except SQLAlchemyError as e:
            logger.error(f"Error searching relational documents for {query}: {e}", exc_info=True)
            raise DatabaseConnectionError(f"Failed to search relational documents: {e}") from e

    def dispose(self):
        self.engine.dispose()
        logger.info("RelationalDBManager engine disposed.")
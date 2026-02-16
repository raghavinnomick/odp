"""
Chunk Storage Service
Handles database operations for document chunks
"""

# Python Packages
from typing import List, Dict

# Database
from sqlalchemy.orm import Session

# Models
from ...models.odp_deal_document_chunks import DealDocumentChunk





class ChunkStorageService:
    """ Service for storing and retrieving document chunks with embeddings... """

    def __init__(self, db_session: Session):
        """
        Initialize with database session
        
        Args:
            db_session: SQLAlchemy database session
        """

        self.db = db_session



    def store_document_chunks(
        self,
        deal_id: int,
        doc_id: int,
        chunks: List[Dict]
    ) -> List[int]:
        """
        Store chunks with embeddings in database
        
        Args:
            deal_id: Deal ID
            doc_id: Document ID
            chunks: List of chunk dictionaries with 'text', 'embedding', 'index', 'metadata'
        
        Returns:
            List of created chunk_ids
        """

        chunk_ids = []
        
        try:
            for chunk in chunks:
                db_chunk = DealDocumentChunk(
                    deal_id = deal_id,
                    doc_id = doc_id,
                    chunk_text = chunk['text'],
                    chunk_index = chunk['index'],
                    page_number = chunk.get('metadata', {}).get('page_number'),
                    embedding = chunk['embedding'],
                    chunk_metadata = chunk.get('metadata')
                )

                self.db.add(db_chunk)
                self.db.flush()  # Get the ID without committing yet
                chunk_ids.append(db_chunk.chunk_id)

            self.db.commit()
            print(f"   ✅ Stored {len(chunks)} chunks in database")
            return chunk_ids

        except Exception as e:
            self.db.rollback()
            print(f"   ❌ Error storing chunks: {e}")
            raise



    def delete_document_chunks(self, doc_id: int) -> int:
        """
        Delete all chunks for a document (useful for re-processing)
        
        Args:
            doc_id: Document ID
        
        Returns:
            Number of chunks deleted
        """

        try:
            deleted = self.db.query(DealDocumentChunk).filter(
                DealDocumentChunk.doc_id == doc_id
            ).delete()
            self.db.commit()
            
            if deleted > 0:
                print(f"   🗑️  Deleted {deleted} old chunks")
            
            return deleted

        except Exception as e:
            self.db.rollback()
            print(f"   ❌ Error deleting chunks: {e}")
            raise



    def get_document_chunks(self, doc_id: int) -> List[DealDocumentChunk]:
        """
        Retrieve all chunks for a document
        
        Args:
            doc_id: Document ID
        
        Returns:
            List of DealDocumentChunk objects ordered by chunk_index
        """

        return self.db.query(DealDocumentChunk).filter(
            DealDocumentChunk.doc_id == doc_id
        ).order_by(DealDocumentChunk.chunk_index).all()



    def get_deal_chunks(self, deal_id: int) -> List[DealDocumentChunk]:
        """
        Retrieve all chunks for a deal (across all documents)
        
        Args:
            deal_id: Deal ID
        
        Returns:
            List of DealDocumentChunk objects
        """

        return self.db.query(DealDocumentChunk).filter(
            DealDocumentChunk.deal_id == deal_id
        ).all()



    def get_chunk_count(self, doc_id: int) -> int:
        """
        Get the number of chunks for a document
        
        Args:
            doc_id: Document ID
        
        Returns:
            Number of chunks
        """

        return self.db.query(DealDocumentChunk).filter(
            DealDocumentChunk.doc_id == doc_id
        ).count()

"""
Document Process Service
Handles chunking and embedding after text extraction
"""

# Python Packages
from typing import List

# Database
from odp.config.database import db

# Models
from ...models.odp_deal_document import DealDocument

# Services
from ...document_processing.services.document_processor import DocumentProcessor
from ...document_processing.services.chunk_storage import ChunkStorageService

# Messages & Exceptions
from ...util.exceptions import ServiceException
from ...util import messages





class DocumentProcessService:
    """
    Service to process extracted text:
    - Chunk text
    - Generate embeddings
    - Store in database
    """

    def __init__(self):
        self.processor = DocumentProcessor()
        self.storage = ChunkStorageService(db.session)



    def process_and_store(
        self,
        deal_id: int,
        doc_id: int,
        extracted_text: str,
        doc_name: str
    ) -> dict:
        """
        Process extracted text and store chunks with embeddings
        
        Args:
            deal_id: Deal ID
            doc_id: Document ID
            extracted_text: Text extracted from document
            doc_name: Document name
            
        Returns:
            dict: Processing result with chunk statistics
        """

        try:
            print(f"\n{'='*60}")
            print(f"📄 Processing: {doc_name}")
            print(f"{'='*60}")
            
            # Delete existing chunks (if re-processing)
            print(f"🗑️  Cleaning up old chunks...")
            deleted_count = self.storage.delete_document_chunks(doc_id)
            
            # Chunk the text
            print(f"🔪 Chunking text (length: {len(extracted_text)} chars)...")
            chunks = self.processor.chunk_text(
                text = extracted_text,
                doc_name = doc_name,
                chunk_size = 1000,
                overlap = 200
            )
            print(f"✅ Created {len(chunks)} chunks")

            # Generate embeddings
            print(f"🧮 Generating embeddings...")
            texts = [chunk['text'] for chunk in chunks]
            embeddings = self.processor.generate_embeddings_batch(texts)
            print(f"✅ Generated {len(embeddings)} embeddings (dim: {len(embeddings[0])})")

            # Combine chunks with embeddings
            for chunk, embedding in zip(chunks, embeddings):
                chunk['embedding'] = embedding

            # Store in database
            print(f"💾 Storing chunks in database...")
            chunk_ids = self.storage.store_document_chunks(
                deal_id = deal_id,
                doc_id = doc_id,
                chunks = chunks
            )

            print(f"\n{'='*60}")
            print(f"✅ COMPLETE: {doc_name}")
            print(f"   - Chunks created: {len(chunk_ids)}")
            print(f"   - Old chunks deleted: {deleted_count}")
            print(f"{'='*60}\n")

            return {
                "chunks_created": len(chunk_ids),
                "chunk_ids": chunk_ids,
                "embeddings_generated": len(embeddings),
                "old_chunks_deleted": deleted_count,
                "status": "success"
            }

        except Exception as errors:
            print(f"❌ Error processing document: {str(errors)}")
            raise ServiceException(
                error_code = "DOCUMENT_PROCESSING_FAILED",
                message = messages.ERROR.get(
                    "DOCUMENT_PROCESSING_FAILED",
                    "Failed to process document"
                ),
                details = str(errors)
            )

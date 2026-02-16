"""
Debug Service
Helper service to debug and inspect the vector database
"""

# Python Packages
from typing import List, Dict

# Database
from sqlalchemy import text, func
from odp.config.database import db

# Models
from ...models.odp_deal_document_chunks import DealDocumentChunk
from ...models.odp_deal_document import DealDocument


class DebugService:
    """Service for debugging vector search and database content"""
    
    def get_deal_stats(self, deal_id: int) -> Dict:
        """
        Get statistics about documents and chunks for a deal
        
        Args:
            deal_id: Deal ID
            
        Returns:
            Dictionary with stats
        """
        
        # Count documents
        doc_count = db.session.query(DealDocument).filter(
            DealDocument.deal_id == deal_id
        ).count()
        
        # Count chunks
        chunk_count = db.session.query(DealDocumentChunk).filter(
            DealDocumentChunk.deal_id == deal_id
        ).count()
        
        # Count chunks with embeddings using raw SQL
        chunks_with_embeddings_query = text("""
            SELECT COUNT(*) 
            FROM odp_deal_document_chunks 
            WHERE deal_id = :deal_id 
            AND embedding IS NOT NULL
        """)
        
        chunks_with_embeddings = db.session.execute(
            chunks_with_embeddings_query,
            {"deal_id": deal_id}
        ).scalar()
        
        # Get document details
        documents = db.session.query(
            DealDocument.doc_id,
            DealDocument.doc_name,
            func.count(DealDocumentChunk.chunk_id).label('chunk_count')
        ).outerjoin(
            DealDocumentChunk,
            DealDocument.doc_id == DealDocumentChunk.doc_id
        ).filter(
            DealDocument.deal_id == deal_id
        ).group_by(
            DealDocument.doc_id,
            DealDocument.doc_name
        ).all()
        
        return {
            "deal_id": deal_id,
            "total_documents": doc_count,
            "total_chunks": chunk_count,
            "chunks_with_embeddings": chunks_with_embeddings,
            "documents": [
                {
                    "doc_id": doc.doc_id,
                    "doc_name": doc.doc_name,
                    "chunk_count": doc.chunk_count
                }
                for doc in documents
            ]
        }
    
    def get_sample_chunks(self, deal_id: int, limit: int = 3) -> List[Dict]:
        """
        Get sample chunks for inspection
        
        Args:
            deal_id: Deal ID
            limit: Number of samples
            
        Returns:
            List of chunk samples
        """
        
        chunks = db.session.query(DealDocumentChunk).filter(
            DealDocumentChunk.deal_id == deal_id
        ).limit(limit).all()
        
        return [
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "chunk_text_preview": chunk.chunk_text[:200] + "...",
                "has_embedding": chunk.embedding is not None,
                "embedding_dimension": len(chunk.embedding) if chunk.embedding is not None else 0
            }
            for chunk in chunks
        ]
    
    def test_search(self, deal_id: int, question: str) -> Dict:
        """
        Test search without similarity threshold
        
        Args:
            deal_id: Deal ID
            question: Test question
            
        Returns:
            Search results with similarity scores
        """
        
        from .search_service import SearchService
        
        search_service = SearchService()
        
        # Generate embedding
        question_embedding = search_service.embedding_service.generate_embedding(question)
        embedding_str = "[" + ",".join(map(str, question_embedding)) + "]"
        
        # Search WITHOUT threshold to see what exists
        query = text("""
            SELECT 
                dc.chunk_id,
                dc.chunk_text,
                dd.doc_name,
                1 - (dc.embedding <=> CAST(:query_embedding AS vector)) AS similarity
            FROM odp_deal_document_chunks dc
            JOIN odp_deal_documents dd ON dc.doc_id = dd.doc_id
            WHERE dc.deal_id = :deal_id
                AND dc.embedding IS NOT NULL
            ORDER BY dc.embedding <=> CAST(:query_embedding AS vector)
            LIMIT 10
        """)
        
        result = db.session.execute(
            query,
            {
                "query_embedding": embedding_str,
                "deal_id": deal_id
            }
        )
        
        results = result.fetchall()
        
        return {
            "question": question,
            "total_results": len(results),
            "top_results": [
                {
                    "chunk_id": r[0],
                    "text_preview": r[1][:150] + "...",
                    "doc_name": r[2],
                    "similarity_score": f"{r[3]:.4f}"
                }
                for r in results[:5]
            ]
        }
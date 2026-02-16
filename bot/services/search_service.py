"""
Search Service
Handles vector similarity search for relevant chunks
Now supports searching across all deals
"""

# Python Packages
from typing import List, Tuple, Optional

# Database
from sqlalchemy import text
from odp.config.database import db

# Vendors
from ...vendors.openai import EmbeddingService





class SearchService:
    """
    Service for searching similar document chunks using embeddings
    """
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    
    def search_similar_chunks(
        self,
        question: str,
        deal_id: Optional[int] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.5
    ) -> List[Tuple]:
        """
        Search for chunks similar to the question
        
        Args:
            question: User's question
            deal_id: Optional deal ID (if None, searches ALL deals)
            top_k: Number of chunks to retrieve
            similarity_threshold: Minimum similarity (0-1)
        
        Returns:
            List of tuples: (chunk_text, doc_name, similarity, chunk_id, chunk_index, page_number, deal_id)
        """
        
        # Generate embedding for question
        print(f"🧮 Generating question embedding...")
        question_embedding = self.embedding_service.generate_embedding(question)
        
        # Search database
        if deal_id:
            print(f"🔍 Searching in deal {deal_id}...")
            chunks = self._vector_search_single_deal(
                deal_id=deal_id,
                query_embedding=question_embedding,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
        else:
            print(f"🔍 Searching across ALL deals...")
            chunks = self._vector_search_all_deals(
                query_embedding=question_embedding,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
        
        print(f"✅ Found {len(chunks)} relevant chunks")
        return chunks
    
    
    def _vector_search_single_deal(
        self,
        deal_id: int,
        query_embedding: List[float],
        top_k: int,
        similarity_threshold: float
    ) -> List[Tuple]:
        """
        Perform vector similarity search within a single deal
        
        Returns:
            List of tuples with chunk data
        """
        
        # Convert embedding to PostgreSQL vector format
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        # SQL query using cosine similarity
        query = text("""
            SELECT 
                dc.chunk_text,
                dd.doc_name,
                1 - (dc.embedding <=> CAST(:query_embedding AS vector)) AS similarity,
                dc.chunk_id,
                dc.chunk_index,
                dc.page_number,
                dc.deal_id
            FROM odp_deal_document_chunks dc
            JOIN odp_deal_documents dd ON dc.doc_id = dd.doc_id
            WHERE dc.deal_id = :deal_id
                AND dc.embedding IS NOT NULL
                AND (1 - (dc.embedding <=> CAST(:query_embedding AS vector))) >= :threshold
            ORDER BY dc.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
        """)
        
        result = db.session.execute(
            query,
            {
                "query_embedding": embedding_str,
                "deal_id": deal_id,
                "threshold": similarity_threshold,
                "top_k": top_k
            }
        )
        
        return result.fetchall()
    
    
    def _vector_search_all_deals(
        self,
        query_embedding: List[float],
        top_k: int,
        similarity_threshold: float
    ) -> List[Tuple]:
        """
        Perform vector similarity search across ALL deals
        
        Returns:
            List of tuples with chunk data (including deal_id)
        """
        
        # Convert embedding to PostgreSQL vector format
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        # SQL query WITHOUT deal_id filter
        query = text("""
            SELECT 
                dc.chunk_text,
                dd.doc_name,
                1 - (dc.embedding <=> CAST(:query_embedding AS vector)) AS similarity,
                dc.chunk_id,
                dc.chunk_index,
                dc.page_number,
                dc.deal_id
            FROM odp_deal_document_chunks dc
            JOIN odp_deal_documents dd ON dc.doc_id = dd.doc_id
            WHERE dc.embedding IS NOT NULL
                AND (1 - (dc.embedding <=> CAST(:query_embedding AS vector))) >= :threshold
            ORDER BY dc.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
        """)
        
        result = db.session.execute(
            query,
            {
                "query_embedding": embedding_str,
                "threshold": similarity_threshold,
                "top_k": top_k
            }
        )
        
        return result.fetchall()
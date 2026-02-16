"""
Context Builder Service
Builds formatted context from retrieved chunks for LLM
"""

# Python Packages
from typing import List, Tuple, Dict





class ContextBuilder:
    """
    Service for building context from document chunks
    """
    
    def build_context(self, chunks: List[Tuple]) -> str:
        """
        Build formatted context string from retrieved chunks
        
        Args:
            chunks: List of tuples - can be 6 or 7 values:
                   (chunk_text, doc_name, similarity, chunk_id, chunk_index, page_number)
                   OR
                   (chunk_text, doc_name, similarity, chunk_id, chunk_index, page_number, deal_id)
        
        Returns:
            Formatted context string ready for LLM
        """
        
        if not chunks:
            return ""
        
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            # Handle both 6 and 7 value tuples
            chunk_text = chunk[0]
            doc_name = chunk[1]
            similarity = chunk[2]
            page_number = chunk[5] if len(chunk) > 5 else None
            
            # Format chunk with source information
            source_info = f"[Source: {doc_name}"
            if page_number:
                source_info += f", Page {page_number}"
            source_info += f", Relevance: {similarity:.2%}]"
            
            context_parts.append(
                f"Document {i}:\n{source_info}\n{chunk_text}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    
    def extract_sources(self, chunks: List[Tuple]) -> List[Dict]:
        """
        Extract source information from chunks for response
        
        Args:
            chunks: List of chunks with metadata
        
        Returns:
            List of source dictionaries with document info
        """
        
        sources = []
        seen_docs = set()
        
        for chunk in chunks:
            chunk_text = chunk[0]
            doc_name = chunk[1]
            similarity = chunk[2]
            page_number = chunk[5] if len(chunk) > 5 else None
            
            # Avoid duplicate documents in sources
            if doc_name not in seen_docs:
                source = {
                    "document_name": doc_name,
                    "relevance": f"{similarity:.2%}",
                    "preview": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
                }
                
                if page_number:
                    source["page_number"] = page_number
                
                sources.append(source)
                seen_docs.add(doc_name)
        
        return sources
    
    
    def calculate_confidence(self, chunks: List[Tuple]) -> str:
        """
        Calculate confidence level based on similarity scores
        
        Args:
            chunks: List of chunks with similarity scores
        
        Returns:
            Confidence level: "high", "medium", or "low"
        """
        
        if not chunks:
            return "low"
        
        # Get average similarity of top chunks
        # Similarity score is at index 2
        avg_similarity = sum(chunk[2] for chunk in chunks) / len(chunks)
        
        if avg_similarity >= 0.85:
            return "high"
        elif avg_similarity >= 0.70:
            return "medium"
        else:
            return "low"
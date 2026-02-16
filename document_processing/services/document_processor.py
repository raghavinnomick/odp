"""
Document Processing Service: Handles chunking
Uses EmbeddingService from vendors/openai for embeddings
"""

# Python Packages
import re
import tiktoken
from typing import List, Dict, Optional

# Vendors
from ...vendors.openai import EmbeddingService





class DocumentProcessor:
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize document processor
        
        Args:
            openai_api_key: Optional OpenAI API key (uses env var if not provided)
        """
        self.embedding_service = EmbeddingService(openai_api_key)
        self.encoding = tiktoken.get_encoding("cl100k_base")


    def chunk_text(
        self, 
        text: str, 
        chunk_size: int = 1000, 
        overlap: int = 200,
        doc_name: str = "",
        page_number: Optional[int] = None
    ) -> List[Dict]:
        """
        Split text into overlapping chunks with metadata
        
        Args:
            text: Full document text
            chunk_size: Maximum characters per chunk
            overlap: Character overlap between chunks
            doc_name: Document name for metadata
            page_number: Optional page number
        
        Returns:
            List of chunk dictionaries with text and metadata
        """
        text = self._clean_text(text)
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            if end < len(text):
                sentence_breaks = [
                    chunk.rfind('. '),
                    chunk.rfind('.\n'),
                    chunk.rfind('? '),
                    chunk.rfind('! '),
                    chunk.rfind('\n\n')
                ]
                break_point = max(sentence_breaks)
                
                if break_point > chunk_size * 0.5:
                    end = start + break_point + 1
                    chunk = text[start:end]
            
            if len(chunk.strip()) < 50:
                break
                
            chunks.append({
                'text': chunk.strip(),
                'index': chunk_index,
                'metadata': {
                    'doc_name': doc_name,
                    'page_number': page_number,
                    'char_start': start,
                    'char_end': end,
                    'token_count': len(self.encoding.encode(chunk))
                }
            })
            
            chunk_index += 1
            start = end - overlap
        
        return chunks



    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text
        
        Args:
            text: Raw text to clean
        
        Returns:
            Cleaned text
        """
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = text.replace('\x00', '')
        return text.strip()



    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using the vendor service
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List of embeddings
        """
        return self.embedding_service.generate_embeddings_batch(texts)

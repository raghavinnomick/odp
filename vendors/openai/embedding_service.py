""" OpenAI Embedding Service... """

# Python Packages
from typing import List
from .openai_client import OpenAIClient

# Constants
from ...base  import constants





class EmbeddingService:
    """ Service for generating embeddings using OpenAI... """

    def __init__(self, api_key: str = None):
        """ Initialize embedding service... """

        self.client = OpenAIClient(api_key).get_client()
        self.default_model = constants.OPENAI_EMBEDDING_MODEL



    def generate_embedding(self, text: str, model: str = None) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            model: OpenAI embedding model (default: constants.OPENAI_EMBEDDING_MODEL)
            
        Returns:
            List of floats representing the embedding
        """

        try:
            response = self.client.embeddings.create(
                model = model or self.default_model,
                input=text
            )
            return response.data[0].embedding

        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            raise



    def generate_embeddings_batch(
        self, 
        texts: List[str], 
        model: str = None,
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches
        
        Args:
            texts: List of texts to embed
            model: OpenAI embedding model (default: constants.OPENAI_EMBEDDING_MODEL)
            batch_size: Number of texts to process at once (max 2048 for OpenAI)
            
        Returns:
            List of embeddings
        """

        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        for i in range(0, len(texts), batch_size):
            batch_num = (i // batch_size) + 1
            batch = texts[i:i + batch_size]

            try:
                print(f"   Processing batch {batch_num}/{total_batches} ({len(batch)} texts)...")
                response = self.client.embeddings.create(
                    model = model or self.default_model,
                    input = batch
                )
                embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(embeddings)

            except Exception as e:
                print(f"❌ Error in batch {batch_num}: {e}")
                raise
        
        return all_embeddings



    def get_embedding_dimension(self, model: str = None) -> int:
        """
        Get the dimension of embeddings for a given model
        
        Args:
            model: OpenAI embedding model
            
        Returns:
            Embedding dimension
        """

        model = model or self.default_model

        # Model dimension mapping
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }

        return dimensions.get(model, 1536)

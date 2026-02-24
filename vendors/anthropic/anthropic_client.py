"""
vendors/anthropic/anthropic_client.py
======================================
Singleton Anthropic client.
Reads ANTHROPIC_API_KEY from environment via base/constants.py.
"""

# Python Packages
from anthropic import Anthropic
from typing import Optional

# Constants
from ...base import constants





class AnthropicClient:
    """
    Singleton Anthropic client for the application.
    One shared instance reused across all requests.
    """

    _instance = None
    _client   = None

    def __new__(cls, api_key: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(AnthropicClient, cls).__new__(cls)
            cls._client   = Anthropic(api_key=constants.ANTHROPIC_API_KEY)
        return cls._instance


    def get_client(self) -> Anthropic:
        if self._client is None:
            raise Exception(
                "Anthropic client not initialized. "
                "Set ANTHROPIC_API_KEY in your .env file."
            )
        return self._client

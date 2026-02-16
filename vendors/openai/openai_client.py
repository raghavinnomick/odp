""" OpenAI Client Configuration... """

# Python Packages
import os
from openai import OpenAI
from typing import Optional

# Constants
from ...base import constants





class OpenAIClient:
    """ Singleton OpenAI client for the application... """

    _instance = None
    _client = None

    def __new__(cls, api_key: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(OpenAIClient, cls).__new__(cls)
            cls._client = OpenAI(
                api_key = constants.OPENAI_API_KEY
            )
        return cls._instance



    @property
    def client(self):
        """ Get the OpenAI client instance... """

        if self._client is None:
            raise Exception("OpenAI client not initialized. Set OPENAI_API_KEY environment variable.")

        return self._client


    def get_client(self):
        """Get the OpenAI client instance (alternative method)"""

        return self.client

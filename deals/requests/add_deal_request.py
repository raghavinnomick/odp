"""
Add Deal Request Definition
Handles:
    - deal_name (form-data)
    - file (Document upload)
"""

# Python Packages
from flask import request as flask_request





class AddDealRequest:

    @staticmethod
    def apply(namespace):
        """
        Apply swagger decorators to endpoint
        """

        def decorator(func):
            func = namespace.doc(consumes = ['multipart/form-data'])(func)
            func = namespace.param(
                'deal_name',
                'Deal Name',
                _in = 'formData',
                required = True
            )(func)

            func = namespace.param(
                'file',
                'Document',
                type = 'file',
                _in = 'formData',
                required = True
            )(func)

            return func

        return decorator


    @staticmethod
    def get_data():
        """
        Extract request data
        """

        return {
            "deal_name": flask_request.form.get("deal_name"),
            "file": flask_request.files.get("file")
        }

"""
Edit Deal Request

Handles:
    - Swagger body model for Edit Deal API
    - Extract JSON payload
"""

from flask_restx import fields
from flask import request





class EditDealRequest:

    @staticmethod
    def apply(namespace):
        """
        Swagger Model for Edit Deal
        """

        model = namespace.model("EditDealRequest", {
            "deal_id": fields.Integer(
                required = True,
                description = "Deal ID to update"
            ),
            "deal_name": fields.String(
                required = True,
                description = "New Deal Name"
            )
        })

        return namespace.expect(model)


    @staticmethod
    def get_data():
        """
        Extract JSON body
        """
        return request.json

"""
File: Deal Routes

Handles:
    - Add Deal
    - Upload Deal Document
    - Extract Document Text
"""

# Flask Packages
from flask import abort
from flask_restx import Namespace, Resource, fields

# Request
from ..deals.requests.add_deal_request import AddDealRequest

# Validations
from ..deals.validations.add_deal_validation import AddDealValidation
from ..deals.validations.process_document_validation import ProcessDocumentValidation

# Controller
from ..deals.controller import DealController

# Errors & Exceptions
from ..util import messages
from ..util.exceptions import AppException, InternalServerException

# Namespaces
deal_namespace = Namespace('deals', description = 'Deal Management APIs')





@deal_namespace.route('/add')
class AddDeal(Resource):

    @AddDealRequest.apply(deal_namespace)
    def post(self):
        """
        Create new Deal with Document
        """

        try:
            # Args
            args = AddDealRequest.get_data()

            # Validations
            AddDealValidation().validate(args)

            # Controller
            result = DealController().create_deal(args)

            return {
                "status": "success",
                "data": result
            }, 201

        except AppException as error:
            return error.to_dict(), error.status_code

        except Exception as error:
            error = InternalServerException(details = str(error))
            return error.to_dict(), error.status_code



@deal_namespace.route('/process-document/<int:doc_id>')
class ProcessDealDocument(Resource):

    def post(self, doc_id):
        """
        Extract text from uploaded Deal Document (PDF/DOCX)

        - Fetch document by doc_id
        - Extract text from S3
        - Return preview + length
        """

        try:
            # Validations
            ProcessDocumentValidation().validate(doc_id)

            # Controller
            result = DealController().process_deal_document(doc_id)

            return {
                "status": "success",
                "data": result
            }, 200

        except AppException as error:
            return error.to_dict(), error.status_code

        except Exception as error:
            error = InternalServerException(details = str(error))
            return error.to_dict(), error.status_code

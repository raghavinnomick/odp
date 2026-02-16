""" All Error and Success Message declare here... """


# SUCCESS MESSAGES
SUCCESS = {
    "DEAL_UPDATE_SUCCESS"       :   "Deal updated successfully.",
    "DEAL_DELETE_SUCCESS"       :   "Deal deleted successfully."
}


# ERROR MESSAGES
ERROR = {
    # Deal Errors
    "INVALID_DEAL_ID"           :   "Deal ID is required.",
    "INVALID_DEAL_NAME"         :   "Deal name is required.",
    "DEAL_NOT_FOUND"            :   "Deal with given ID does not exist.",
    "DEAL_NAME_ALREADY_EXISTS"  :   "Another deal already exists with this name.",

    # Add Deal Errors
    "ADD_DEAL_NAME_REQUIRED"    :   "Deal name is required.",
    "ADD_DEAL_NAME_MIN"         :   "Deal name must be at least {} characters.",
    "ADD_DEAL_FILE_REQUIRED"    :   "File is required.",
    "ADD_DEAL_INVALID_FILE"     :   "Invalid file name.",

    # Edit/Delete Deal Errors
    "DEAL_UPDATE_FAILED"        :   "Unable to update deal.",
    "DEAL_DELETE_FAILED"        :   "Unable to delete deal.",

    # Process Document Erros
    "DOCUMENT_ID_REQUIRED"      :   "Document ID is required.",
    "INVALID_DOCUMENT_ID"       :   "Invalid Document ID.",
    "DOCUMENT_NOT_FOUND"        :   "Document not found.",
    "DOCUMENT_STORAGE_MISSING"  :   "Storage path missing for document.",
    "DOCUMENT_EXTRACTION_FAILED":   "Document extraction failed.",
    "PDFPLUMBER_EXTRACTION_FAILED": "PDFPlumber extraction failed.",
    "GOOGLE_DOC_AI_FAILED"      :   "Google Document AI extraction failed.",
    "GOOGLE_INIT_FAILED"        :   "Failed to initialize Google Document AI client.",
    "GOOGLE_EMPTY_RESPONSE"     :   "Google Document AI returned empty text.",
    "DOCUMENT_PROCESSING_FAILED": "Failed to process document chunks and embeddings",

    # Bot/Query Errors
    "QUERY_FAILED": "Failed to process question",
    "MISSING_QUESTION": "Question is required",
    "INVALID_QUESTION": "Question must be a non-empty string",
    "INVALID_TOP_K": "top_k must be an integer between 1 and 20",
    "INVALID_REQUEST": "Request body is required",

    # General Errors
    "UNSUPPORTED_FILE_FORMAT"   :   "Unsupported file format: {file_extension}. Supported formats: PDF",
}


# ERROR CODES
ERROR_CODES = {
    "HTTP_400_BAD_REQUEST"                  :   400,
    "HTTP_401_BAD_AUTHORIZATION"            :   401,
    "HTTP_403_NOT_AUTHORIZED"               :   403,
    "HTTP_429_TOO_MANY_REQUEST"             :   429,
    "HTTP_500_INTERNAL_ERROR"               :   500
}

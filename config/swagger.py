""" Swagger configuration defined here... """

# Python Packages
from flask_restx import Api

# Constants
from ..base import constants





# Swagger authorization for the API
authorizations = {
    'Bearer Auth' : {
        'type' : 'apiKey',
        'in' : 'header',
        'name' : 'Authorization'
    }
}

if constants.APP_ENV != "production":
    doc = '/swagger/'
else:
    doc = False

# Swagger Configuration
api = Api(
    authorizations = authorizations,
    title = constants.SWAGGER_APP_PROPS['name'],
    version = constants.SWAGGER_APP_PROPS['version'],
    description = constants.SWAGGER_APP_PROPS['description'],
    doc = doc
)

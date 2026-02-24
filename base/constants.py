""" All Application Constants declare here... """

# Python Packages
from decouple import config


# App Constants
APP_ENV                         =   config('APP_ENV')
APP_SECRET_KEY                  =   config('APP_SECRET_KEY')


# Swagger Constants
SWAGGER_APP_PROPS       =   {
                                "name": "ODP",
                                "version": "1.0",
                                "description": "Gmail-native RAG assistant: extracts investor \
                                questions, retrieves deal terms/FAQs, and drafts \
                                safe replies with audit logs."
                            }


# Database Constants
DB_HOST                         =   config('DB_HOST')
DB_PORT                         =   config('DB_PORT')
DB_NAME                         =   config('DB_NAME')
DB_USER                         =   config('DB_USER')
DB_PASSWORD                     =   config('DB_PASSWORD')


# AWS Constants
AWS_ACCESS_KEY_ID		        =	config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY	        =	config('AWS_SECRET_ACCESS_KEY')
AWS_REGION				        =	config('AWS_REGION')
AWS_S3_BUCKET_NAME	            =	config('AWS_S3_BUCKET_NAME')


# OpenAI Constants
OPENAI_API_KEY		            =	config('OPENAI_API_KEY')
OPENAI_DEFAULT_MODEL            =   "gpt-4o-mini"
OPENAI_MAX_TOKENS		        =	3000
OPENAI_ANSWER_TEMPERATURE	    =	0.7 # Very Fliexible for creative answers
OPENAI_EMBEDDING_MODEL          =	"text-embedding-3-small"

OPENAI_RAG_MODEL	            =	config('OPENAI_RAG_MODEL')
OPENAI_LIGHT_MODEL	            =	config('OPENAI_LIGHT_MODEL')


# Google Variables
GOOGLE_PROJECT_ID		        =	config('GOOGLE_PROJECT_ID')
GOOGLE_PROJECT_LOCATION	        =	config('GOOGLE_PROJECT_LOCATION')
GOOGLE_PROJECT_PROCESSOR_ID     =	config('GOOGLE_PROJECT_PROCESSOR_ID')
GOOGLE_APPLICATION_CREDENTIALS	=	config('GOOGLE_APPLICATION_CREDENTIALS')

"""
Application factory
"""

# Python Packages
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

# Local Imports
from .config.swagger import api
from .config.urls import URLs
from .config.database import init_db, db





def create_app():
    """
    Application Factory
    """

    # App Object
    app = Flask(__name__)
    app.config["DEBUG"] = True

    # Initialize Database
    init_db(app)

    # Register models
    from . import models

    # Initialize Migration
    Migrate(app, db)

    # Enable CORS
    CORS(app)

    # Initialize Swagger
    api.init_app(app)

    # Register Namespaces
    URLs.add_namespaces()

    return app



# Create app instance for Flask CLI
app = create_app()


if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 5000)

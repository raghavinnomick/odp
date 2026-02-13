""" Database configuration and initialization... """

# Python Packages
from flask_sqlalchemy import SQLAlchemy

# Constants
from ..base import constants





class Database:
    """
    Handles database configuration
    """

    def __init__(self):
        self.host = constants.DB_HOST
        self.port = constants.DB_PORT
        self.user = constants.DB_USER
        self.password = constants.DB_PASSWORD
        self.database = constants.DB_NAME

    def get_database_uri(self):
        """
        Build PostgreSQL URI dynamically
        """
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


# Global SQLAlchemy object
db = SQLAlchemy()


def init_db(app):
    """
    Initialize database with Flask app
    """
    database = Database()

    app.config["SQLALCHEMY_DATABASE_URI"] = database.get_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

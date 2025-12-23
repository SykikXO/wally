import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess-this-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app/static/uploads')
    QUARANTINE_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app/static/quarantine')
    # MAX_CONTENT_LENGTH = 300 * 1024 * 1024  # Disabled to allow admin bypass in route



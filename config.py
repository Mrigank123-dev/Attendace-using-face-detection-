import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent

class Config:
    # --- Application Settings ---
    SECRET_KEY = os.getenv('SECRET_KEY', 'a-very-secret-dev-key-that-you-should-change')

    # --- Database Settings ---
    # Defines the path for the SQLite database file
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR / "data" / "attendance.db"}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- File Upload Settings ---
    # Folder where student face images will be stored
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', str(BASE_DIR / 'static' / 'uploads'))
    
    # Allowed file extensions for face images
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Create a single config instance to be imported by the app
config = Config()
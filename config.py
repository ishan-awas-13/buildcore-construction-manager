import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
    # Use environment variables if set, otherwise default to a typical local setup
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-for-dev'
    
    # SQLAlchemy Configuration
    # postgresql://username:password@localhost:5432/dbname
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'password')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'buildcore')

    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

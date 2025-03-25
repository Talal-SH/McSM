import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Configuration settings for the application."""
    
    # Application version
    VERSION = '0.0.1'
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')
    
    # Server settings
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Application paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SERVERS_DIR = os.environ.get('SERVERS_DIR', os.path.join(BASE_DIR, 'servers'))
    
    # Server management settings
    DEFAULT_MEMORY = os.environ.get('DEFAULT_MEMORY', '2G')
    MAX_MEMORY = os.environ.get('MAX_MEMORY', '8G')
    JAVA_PATH = os.environ.get('JAVA_PATH', 'java')
    
    # API settings
    API_KEY = os.environ.get('API_KEY', '')  # Empty string means no API key required
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'False').lower() in ('true', '1', 't')
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', 60))
    RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', 60))
    
    # Discord integration settings
    DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', '')
    DISCORD_NOTIFICATIONS_ENABLED = os.environ.get('DISCORD_NOTIFICATIONS_ENABLED', 'False').lower() in ('true', '1', 't')
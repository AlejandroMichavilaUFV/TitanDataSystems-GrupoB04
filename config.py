import os
from dotenv import load_dotenv

# Cargar variables desde el archivo .env
load_dotenv()

class Config:
    # Clave secreta para la sesión de Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'una-clave-secreta-muy-segura')

    # Configuración de Google OAuth
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = "http://localhost:8501/auth/callback"
    
    GOOGLE_SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/userinfo.email',
        'openid'
    ]

    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

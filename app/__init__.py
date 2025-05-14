from flask import Flask
from google_auth_oauthlib.flow import Flow
import os

app = Flask(__name__)
app.secret_key = 'r3g27fge27fy23'

# Configuración de OAuth2
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email'
]

# Importar las rutas después de crear la aplicación
from app import routes
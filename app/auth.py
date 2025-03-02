from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from flask import redirect, url_for, session
from config import Config

def get_authorization_url():
    """Genera la URL de autorización de Google."""
    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=Config.GOOGLE_SCOPES,
        redirect_uri=Config.GOOGLE_REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url

def exchange_code_for_token(code):
    """Intercambia el código de autorización por credenciales."""
    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=Config.GOOGLE_SCOPES,
        redirect_uri=Config.GOOGLE_REDIRECT_URI
    )
    flow.fetch_token(code=code)
    return flow.credentials

def get_user_profile(creds):
    """Obtiene la información del perfil del usuario."""
    service = build('oauth2', 'v2', credentials=creds)
    return service.userinfo().get().execute()

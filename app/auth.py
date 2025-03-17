from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from flask import redirect, url_for, session
from config import Config
import os
import base64
import re
from functools import wraps

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

def get_user_profile(credentials):
    service = build('oauth2', 'v2', credentials=credentials)
    profile = service.userinfo().get().execute()
    return profile

def clean_email_content(content):
    """Limpia el contenido del correo eliminando texto no deseado."""
    pattern = r"(?s)^.*?Extracto de actividad de la cuenta.*?Adjuntamos tu extracto de actividad de la cuenta, que incluye:.*?glosario|Trading 212 es un nombre comercial.*?Todos los Derechos Reservados"
    cleaned_content = re.sub(pattern, '', content)
    return cleaned_content.strip()

def get_last_emails(creds):
    """Obtiene los últimos 3 correos del usuario autenticado."""
    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(userId='me', maxResults=3).execute()
    messages = results.get('messages', [])
    emails = []
    
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
        
        email_data = {
            'id': message['id'],
            'snippet': msg.get('snippet', ''),
            'subject': '',
            'full_content': '',
            'attachments': []
        }
        
        if 'payload' in msg and 'headers' in msg['payload']:
            for header in msg['payload']['headers']:
                if header['name'] == 'Subject':
                    email_data['subject'] = header['value']
        
        def get_body(payload):
            if 'data' in payload['body']:
                return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            elif 'parts' in payload:
                return ''.join([get_body(part) for part in payload['parts']])
            return ''
        
        raw_content = get_body(msg['payload'])
        email_data['full_content'] = clean_email_content(raw_content)
        
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['filename']:
                    attachment = {
                        'filename': part['filename'],
                        'mimeType': part['mimeType'],
                        'attachmentId': part['body']['attachmentId'],
                        'size': part['body']['size']
                    }
                    email_data['attachments'].append(attachment)
        
        emails.append(email_data)
    
    return emails

def login_required(f):
    """Decorador para proteger rutas que requieren autenticación."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

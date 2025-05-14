from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import Config
import os
import base64
import re
from functools import wraps
from flask import redirect, url_for, session

# Configuración del flujo de OAuth
def get_authorization_url():
    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=Config.GOOGLE_SCOPES,
        redirect_uri=Config.GOOGLE_REDIRECT_URI
    )
    authorization_url, _ = flow.authorization_url(prompt='consent')
    return authorization_url

# Intercambiar el código de autorización por credenciales
def exchange_code_for_token(code):
    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=Config.GOOGLE_SCOPES,
        redirect_uri=Config.GOOGLE_REDIRECT_URI
    )
    flow.fetch_token(code=code)
    return flow.credentials

# Obtener el perfil del usuario
def get_user_profile(creds):
    service = build('people', 'v1', credentials=creds)
    profile = service.people().get(
        resourceName='people/me',
        personFields='names,emailAddresses,photos'
    ).execute()
    return profile

def clean_email_content(content):
    # Ajusta el patrón para eliminar encabezados y pie de página no deseados
    # Puedes modificar el patrón según el formato específico de tus correos
    pattern = r"(?s)^.*?Extracto de actividad de la cuenta.*?Adjuntamos tu extracto de actividad de la cuenta, que incluye:.*?glosario|Trading 212 es un nombre comercial.*?Todos los Derechos Reservados"
    cleaned_content = re.sub(pattern, '', content)
    return cleaned_content.strip()

# Obtener los últimos 3 correos
def get_last_emails(creds):
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
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
import email
import arrow

def format_date(date_str):
    """Convierte diferentes formatos de fecha a formato local y añade tiempo relativo"""
    try:
        # Lista de formatos posibles de fecha
        formats = [
            'ddd, DD MMM YYYY HH:mm:ss ZZ',
            'ddd, DD MMM YYYY HH:mm:ss [GMT]',
            'ddd, DD MMM YYYY HH:mm:ss ZZ (UTC)',
            'ddd, D MMM YYYY HH:mm:ss ZZ',  
            'ddd, DD MMM YYYY HH:mm:ss Z',
            'ddd, DD MMM YYYY HH:mm:ss ZZ',
            'ddd, DD MMM YYYY HH:mm:ss ZZ (UTC)',
            'ddd, DD MMM YYYY HH:mm:ss Z (UTC)',
            'ddd, D MMM YYYY HH:mm:ss Z',
            'ddd, D MMM YYYY HH:mm:ss ZZ',
            'ddd, D MMM YYYY HH:mm:ss [GMT]',
            'ddd, D MMM YYYY HH:mm:ss Z (UTC)',
        ]
        
        # Intentar parsear la fecha con cada formato hasta que uno funcione
        for fmt in formats:
            try:
                date = arrow.get(date_str, fmt)
                break
            except arrow.parser.ParserError:
                continue
        else:
            # Si ningún formato funciona, intentar con el parser automático
            try:
                date = arrow.get(date_str)
            except:
                raise ValueError(f"No se pudo parsear la fecha: {date_str}")
        
        # Convertir a hora local del sistema
        date = date.to('local')
        
        return {
            'formatted': date.format('DD/MM/YYYY HH:mm'),
            'when': date.humanize(locale='es')  # "hace 2 días", "hace 5 minutos", etc.
        }
    
    except Exception as e:
        print(f"Error formateando fecha: {e}")
        return {
            'formatted': date_str,
            'when': ''
        }

def process_email(message, service):
    """Procesa un mensaje individual y extrae toda la información necesaria"""
    try:
        headers = message['payload']['headers']
        email_data = {
            'id': message['id'],
            'thread_id': message['threadId'],
            'subject': next((h['value'] for h in headers if h['name'].lower() == 'subject'), '(Sin asunto)'),
            'sender': next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Desconocido'),
            'receiver': next((h['value'] for h in headers if h['name'].lower() == 'to'), 'Desconocido'),
            'body': '',
            'attachments': [],
            'is_read': 'UNREAD' not in message.get('labelIds', []),
            'is_thread': False,  # Se actualizará después
            'labels': message.get('labelIds', [])
        }

        # Procesar fecha
        date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        date_info = format_date(date_str)
        email_data.update({
            'date': date_info['formatted'],
            'when': date_info['when']
        })

        # Extraer el cuerpo del mensaje
        def get_body_from_part(part):
            if part.get('mimeType') == 'text/plain':
                if 'data' in part.get('body', {}):
                    return base64.urlsafe_b64decode(part['body']['data']).decode()
            return None

        # Procesar el cuerpo y los adjuntos
        if 'parts' in message['payload']:
            # Mensaje con partes múltiples
            attachments = []
            for part in message['payload']['parts']:
                if 'filename' in part and part['filename']:
                    # Es un adjunto
                    attachment = {
                        'id': f"{message['id']}:{part['body'].get('attachmentId', '')}:{part['filename']}",
                        'filename': part['filename'],
                        'mimeType': part['mimeType'],
                        'size': int(part['body'].get('size', 0))
                    }
                    attachments.append(attachment)
                else:
                    # Podría ser el cuerpo del mensaje
                    body = get_body_from_part(part)
                    if body:
                        email_data['body'] = body
            email_data['attachments'] = attachments
        else:
            # Mensaje simple
            body = get_body_from_part(message['payload'])
            if body:
                email_data['body'] = body

        # Verificar si es parte de un hilo con múltiples mensajes
        thread = service.users().threads().get(userId='me', id=message['threadId']).execute()
        email_data['is_thread'] = len(thread['messages']) > 1

        return email_data

    except Exception as e:
        print(f"Error procesando email {message.get('id', 'unknown')}: {e}")
        return None

def get_last_emails(credentials, limit=10):
    """Obtiene los últimos correos con toda su información"""
    try:
        service = build('gmail', 'v1', credentials=credentials)
        
        results = service.users().messages().list(
            userId='me',
            maxResults=limit,
            labelIds=['INBOX']
        ).execute()
        
        messages = results.get('messages', [])
        emails_data = []
        
        for message_info in messages:
            message = service.users().messages().get(
                userId='me',
                id=message_info['id'],
                format='full'
            ).execute()
            
            email_data = process_email(message, service)
            if email_data:
                emails_data.append(email_data)
        
        return emails_data
        
    except Exception as e:
        print(f"Error obteniendo correos: {e}")
        return [] 
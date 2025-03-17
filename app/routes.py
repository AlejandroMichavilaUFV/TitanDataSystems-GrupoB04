from flask import redirect, url_for, session, request, render_template, send_file, jsonify
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app import app, CLIENT_SECRETS_FILE, SCOPES
from app.auth import get_authorization_url, exchange_code_for_token, get_user_profile, get_last_emails, login_required
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from groq import Groq
import base64
import io
import os
import json
from app.gmail_utils import get_last_emails
from app.rag_utils import EmailRAG
from app.models.usuarios import registrar_usuario_google

# Variables globales para el modelo y el índice
model_emb = None
index = None
embeddings = None
emails_data = []

# Instancia global del sistema RAG
email_rag = EmailRAG()

def initialize_ai(credentials):
    global model_emb, index, embeddings, emails_data
    
    if model_emb is None:
        model_emb = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Crear servicio de Gmail
    service = build('gmail', 'v1', credentials=credentials)
    
    # Obtener todos los correos
    results = service.users().messages().list(userId='me').execute()
    messages = results.get('messages', [])
    
    # Agregar registro de depuración
    print(f"Correos obtenidos: {len(messages)}")
    
    emails_data = []  # Reiniciar la lista de correos
    
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        
        # Extraer información relevante
        headers = msg['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Obtener el cuerpo del mensaje
        body = ''
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode()
                        break
        
        email_data = {
            'subject': subject,
            'body': body,
            'sender': sender,
            'date': date,
            'id': message['id']
        }
        emails_data.append(email_data)
    
    # Generar textos para embeddings
    textos = [f"Asunto: {email['subject']}\nCuerpo: {email['body']}\nRemitente: {email['sender']}\nFecha: {email['date']}" 
              for email in emails_data]
    
    # Generar embeddings
    embeddings = model_emb.encode(textos)
    
    # Crear índice FAISS
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    # Agregar registro de depuración
    print(f"Inicialización completada. Correos procesados: {len(emails_data)}")

def buscar_correos(pregunta, k=5):
    pregunta_embedding = model_emb.encode([pregunta])
    distancias, indices = index.search(pregunta_embedding, k)
    return [emails_data[i] for i in indices[0]]

def generar_respuesta(pregunta, correos_relevantes):
    contexto = "\n".join([
        f"Asunto: {correo['subject']}\nCuerpo: {correo['body']}\nRemitente: {correo['sender']}\nFecha: {correo['date']}" 
        for correo in correos_relevantes
    ])
    
    input_text = (
        f"Contexto: {contexto}\n"
        f"Pregunta: {pregunta}\n"
        "Por favor, responde a todas las partes de la pregunta de manera precisa y completa basándote en el contexto proporcionado."
    )

    cliente = Groq(api_key="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")
    
    chat_completion = cliente.chat.completions.create(
        messages=[{"role": "user", "content": input_text}],
        model="llama-3.3-70b-versatile",
    )
    
    return chat_completion.choices[0].message.content

@app.route('/')
def index():
    """Página de inicio."""
    return render_template('index.html')

@app.route('/login')
def login():
    """Redirige al usuario a Google para autenticarse."""
    return redirect(get_authorization_url())

@app.route('/auth/callback')
def callback():
    """Recibe el código de autorización y obtiene las credenciales."""
    code = request.args.get('code')
    creds = exchange_code_for_token(code)
    session['credentials'] = creds_to_dict(creds)
    return redirect(url_for('profile'))

@app.route('/profile')
def profile():
    """Muestra el perfil del usuario autenticado y lo registra/actualiza."""
    if 'credentials' not in session:
        return redirect(url_for('index'))

    creds = Credentials(**session['credentials'])
    profile = get_user_profile(creds)
    
    # Verificar que el perfil contenga las claves necesarias
    if 'email' not in profile or 'picture' not in profile:
        return jsonify({'error': 'No se pudo obtener el correo electrónico o la foto del perfil'}), 400
    
    # Registrar o actualizar el usuario en usuarios.json
    registrar_usuario_google(profile)
    
    # Inicializar el modelo AI con las credenciales
    initialize_ai(creds)
    
    # Agregar registro de depuración
    print(f"Perfil del usuario: {profile}")
    
    return render_template('profile.html', profile=profile, emails=emails_data)

@app.route('/logout')
def logout():
    """Cierra la sesión del usuario."""
    session.pop('credentials', None)
    return redirect(url_for('index'))

def creds_to_dict(creds):
    """Convierte credenciales a diccionario para almacenarlas en sesión."""
    return {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }

@app.route('/download_attachment/<message_id>/<attachment_id>')
def download_attachment(message_id, attachment_id):
    if 'credentials' not in session:
        return redirect(url_for('index'))
    
    try:
        creds = Credentials(
            token=session['credentials']['token'],
            refresh_token=session['credentials']['refresh_token'],
            token_uri=session['credentials']['token_uri'],
            client_id=session['credentials']['client_id'],
            client_secret=session['credentials']['client_secret'],
            scopes=session['credentials']['scopes']
        )
        
        service = build('gmail', 'v1', credentials=creds)
        
        # Obtener el adjunto
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment_id
        ).execute()
        
        file_data = base64.urlsafe_b64decode(attachment['data'])
        file_bytes = io.BytesIO(file_data)
        
        # Configurar el tipo MIME para PDFs
        response = send_file(
            file_bytes,
            mimetype='application/pdf',
            as_attachment=False  # No forzar la descarga
        )
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
        
    except Exception as e:
        print(f"Error downloading attachment: {e}")
        return redirect(url_for('profile'))

@app.route('/chat')
@login_required
def chat():
    try:
        # Verificar si hay credenciales en la sesión
        if 'credentials' not in session:
            return redirect(url_for('index'))
            
        credentials = Credentials(**session['credentials'])
        
        # Obtener perfil del usuario
        service = build('oauth2', 'v2', credentials=credentials)
        profile = service.userinfo().get().execute()
        
        # Obtener los últimos 10 correos
        emails = get_last_emails(credentials, limit=10)
        
        # Adaptar el perfil para la plantilla
        user_profile = {
            'display_name': profile.get('name', 'Usuario'),
            'email': profile.get('email', '')
        }
        
        return render_template('chat.html', profile=user_profile, debug_emails=emails)
    except Exception as e:
        print(f"Error en chat: {e}")
        session.clear()  # Limpiar la sesión si hay un error
        return redirect(url_for('index'))

@app.route('/api/chat', methods=['POST'])
@login_required
def process_chat():
    if 'credentials' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        credentials = Credentials(**session['credentials'])
        
        # Obtener correos si el RAG no está inicializado
        if not email_rag.emails_data:
            emails = get_last_emails(credentials)
            email_rag.initialize(emails)
        
        # Procesar la pregunta
        data = request.json
        pregunta = data.get('message')
        
        if not pregunta:
            return jsonify({'error': 'No message provided'}), 400
        
        correos_relevantes = email_rag.buscar_correos(pregunta)
        respuesta = email_rag.generar_respuesta(pregunta, correos_relevantes)
        
        return jsonify({'response': respuesta})
        
    except Exception as e:
        print(f"Error en el chat: {e}")
        return jsonify({'error': 'Error procesando la solicitud'}), 500

@app.route('/api/email/<email_id>')
@login_required
def get_email(email_id):
    try:
        credentials = Credentials(**session['credentials'])
        service = build('gmail', 'v1', credentials=credentials)
        
        # Obtener el mensaje completo
        message = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        # Procesar el mensaje y sus adjuntos
        email_data = process_email(message, service)
        
        return jsonify(email_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_email(message, service):
    email_data = {
        'id': message['id'],
        'threadId': message['threadId'],
        'labelIds': message['labelIds'],
        'snippet': message['snippet'],
        'historyId': message['historyId'],
        'internalDate': message['internalDate'],
        'payload': message['payload'],
        'sizeEstimate': message['sizeEstimate'],
        'raw': message['raw'] if 'raw' in message else None,
        'attachments': []
    }

    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            if part['filename']:
                attachment_id = part['body']['attachmentId']
                attachment = service.users().messages().attachments().get(
                    userId='me',
                    messageId=message['id'],
                    id=attachment_id
                ).execute()
                email_data['attachments'].append({
                    'filename': part['filename'],
                    'mimeType': part['mimeType'],
                    'data': attachment['data']
                })

    return email_data

@app.route('/api/attachment/<attachment_id>')
@login_required
def get_attachment(attachment_id):
    try:
        credentials = Credentials(**session['credentials'])
        service = build('gmail', 'v1', credentials=credentials)
        
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=attachment_id.split(':')[0],
            id=attachment_id.split(':')[1]
        ).execute()
        
        file_data = base64.urlsafe_b64decode(attachment['data'])
        
        return send_file(
            io.BytesIO(file_data),
            as_attachment=True,
            download_name=attachment_id.split(':')[2]
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
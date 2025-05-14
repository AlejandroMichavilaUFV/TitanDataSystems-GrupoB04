from flask import redirect, url_for, session, request, render_template, send_file, jsonify
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app import app, CLIENT_SECRETS_FILE, SCOPES
from app.auth import get_authorization_url, exchange_code_for_token, get_user_profile, get_last_emails, login_required
from groq import Groq
import base64
import io
import os
import json
from app.gmail_utils import get_last_emails
from app.rag_utils import EmailRAG

# Instancia global del sistema RAG
email_rag = EmailRAG()

@app.route('/')
def index():
    if 'credentials' in session:
        return redirect(url_for('profile'))
    return render_template('index.html')

@app.route('/login')
def login():
    authorization_url = get_authorization_url()
    return redirect(authorization_url)

@app.route('/auth/callback')
def callback():
    code = request.args.get('code')
    creds = exchange_code_for_token(code)
    session['credentials'] = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }
    return redirect(url_for('profile'))

@app.route('/profile')
def profile():
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
        
        profile = get_user_profile(creds)
        emails = get_last_emails(creds)
        
        return render_template('profile.html', profile=profile, emails=emails)
    except Exception as e:
        print(f"Error: {e}")
        session.pop('credentials', None)
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('credentials', None)
    return redirect(url_for('index'))

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

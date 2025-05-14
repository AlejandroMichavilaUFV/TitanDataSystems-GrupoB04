from flask import Flask, request, jsonify, render_template
from flask_login import login_required
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from groq import Groq
import base64
import os

app = Flask(__name__)

# Variables globales
vectorizer = None
tfidf_matrix = None
emails_data = []

def initialize_ai(gmail_service):
    global vectorizer, tfidf_matrix, emails_data

    # Obtener todos los correos al inicializar
    results = gmail_service.users().messages().list(userId='me').execute()
    messages = results.get('messages', [])

    for message in messages:
        msg = gmail_service.users().messages().get(userId='me', id=message['id']).execute()

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

    # Generar textos para TF-IDF
    textos = [f"Asunto: {email['subject']}\nCuerpo: {email['body']}\nRemitente: {email['sender']}\nFecha: {email['date']}"
              for email in emails_data]

    # Crear vectorizador TF-IDF y matriz
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(textos)

def buscar_correos(pregunta, k=5):
    pregunta_tfidf = vectorizer.transform([pregunta])
    similitudes = cosine_similarity(pregunta_tfidf, tfidf_matrix).flatten()
    indices = similitudes.argsort()[-k:][::-1]
    return [emails_data[i] for i in indices]

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

    cliente = Groq(api_key="tu_api_key_aquí")

    chat_completion = cliente.chat.completions.create(
        messages=[{"role": "user", "content": input_text}],
        model="llama-3.3-70b-versatile",
    )

    return chat_completion.choices[0].message.content

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
@login_required
def process_chat():
    data = request.json
    pregunta = data.get('message')

    if not pregunta:
        return jsonify({'error': 'No se proporcionó una pregunta'}), 400

    correos_relevantes = buscar_correos(pregunta)
    respuesta = generar_respuesta(pregunta, correos_relevantes)

    return jsonify({'response': respuesta})

# Inicializar el modelo AI cuando se inicia la aplicación
# Asegúrate de pasar el servicio de Gmail autenticado a initialize_ai
# initialize_ai(gmail_service)

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from groq import Groq
from flask import jsonify

# Variables globales para el modelo y el índice
model_emb = None
index = None
embeddings = None
emails_data = []

def initialize_ai():
    global model_emb, index, embeddings, emails_data
    model_emb = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Obtener todos los correos al inicializar
    results = gmail.users().messages().list(userId='me').execute()
    messages = results.get('messages', [])
    
    for message in messages:
        msg = gmail.users().messages().get(userId='me', id=message['id']).execute()
        
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
    
    # Generar textos para embeddings
    textos = [f"Asunto: {email['subject']}\nCuerpo: {email['body']}\nRemitente: {email['sender']}\nFecha: {email['date']}" 
              for email in emails_data]
    
    # Generar embeddings
    embeddings = model_emb.encode(textos)
    
    # Crear índice FAISS
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

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

    # API key directamente en el código
    cliente = Groq(api_key="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")
    
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
        return jsonify({'error': 'No message provided'}), 400
    
    correos_relevantes = buscar_correos(pregunta)
    respuesta = generar_respuesta(pregunta, correos_relevantes)
    
    return jsonify({'response': respuesta})

# Inicializar el modelo AI cuando se inicia la aplicación
initialize_ai() 
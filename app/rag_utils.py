from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from groq import Groq

class EmailRAG:
    def __init__(self):
        self.model_emb = None
        self.index = None
        self.embeddings = None
        self.emails_data = []
        self.groq_client = Groq(api_key="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")

    def initialize(self, emails_data):
        """Inicializa el sistema RAG con los correos proporcionados"""
        self.emails_data = emails_data
        
        if self.model_emb is None:
            self.model_emb = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Generar textos para embeddings usando la estructura exacta del JSON
        textos = []
        for email in emails_data:
            texto = (
                f"Asunto: {email['subject']}\n"
                f"Cuerpo: {email['body']}\n"
                f"Remitente: {email['sender']}\n"
                f"Destinatario: {email['receiver']}\n"
                f"Fecha: {email['date']}\n"
                f"ID: {email['id']}\n"
                f"Thread ID: {email['thread_id']}"
            )
            textos.append(texto)
        
        # Generar embeddings
        self.embeddings = self.model_emb.encode(textos)
        
        # Crear índice FAISS
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(self.embeddings)

    def buscar_correos(self, pregunta, k=3):
        """Busca los correos más relevantes para la pregunta"""
        pregunta_embedding = self.model_emb.encode([pregunta])
        distancias, indices = self.index.search(pregunta_embedding, k)
        return [self.emails_data[i] for i in indices[0]]

    def generar_respuesta(self, pregunta, correos_relevantes):
        """Genera una respuesta basada en los correos relevantes"""
        # Crear el contexto con la estructura exacta del JSON pero limitando el cuerpo
        contexto = "\n\n".join([
            f"Asunto: {correo['subject']}\n"
            f"Remitente: {correo['sender']}\n"
            f"Destinatario: {correo['receiver']}\n"
            f"Fecha: {correo['date']}\n"
            f"Cuerpo: {correo['body'][:500]}..."  # Limitamos el cuerpo a 500 caracteres
            for correo in correos_relevantes
        ])
        
        input_text = (
            f"Contexto: {contexto}\n\n"
            f"Pregunta: {pregunta}\n\n"
            "Responde de manera directa y precisa usando la información proporcionada. "
            "Incluye detalles específicos relevantes."
        )

        chat_completion = self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": input_text}],
            model="llama-3.3-70b-versatile",
        )
        
        return chat_completion.choices[0].message.content 
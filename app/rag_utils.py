import numpy as np
from groq import Groq
from sklearn.metrics.pairwise import cosine_similarity

class EmailRAG:
    def __init__(self, api_key='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'):
        self.groq_client = Groq(api_key=api_key)
        self.embeddings = None
        self.emails_data = []

    def initialize(self, emails_data):
        """Inicializa el sistema RAG con los correos proporcionados"""
        self.emails_data = emails_data

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

        # Generar embeddings utilizando la API de Groq
        self.embeddings = []
        for texto in textos:
            response = self.groq_client.embeddings.create(
                model="llama-3-8b-8192",
                input=texto
            )
            embedding = response.data[0].embedding
            self.embeddings.append(embedding)
        self.embeddings = np.array(self.embeddings)

    def buscar_correos(self, pregunta, k=3):
        """Busca los correos más relevantes para la pregunta"""
        # Generar embedding de la pregunta
        response = self.groq_client.embeddings.create(
            model="llama-3-8b-8192",
            input=pregunta
        )
        pregunta_embedding = np.array([response.data[0].embedding])

        # Calcular similitud de coseno entre la pregunta y los correos
        similitudes = cosine_similarity(pregunta_embedding, self.embeddings)[0]
        indices = np.argsort(similitudes)[::-1][:k]
        return [self.emails_data[i] for i in indices]

    def generar_respuesta(self, pregunta, correos_relevantes):
        """Genera una respuesta basada en los correos relevantes"""
        # Crear el contexto con la estructura exacta del JSON pero limitando el cuerpo
        contexto = "\n\n".join([
            f"Asunto: {correo['subject']}\n"
            f"Remitente: {correo['sender']}\n"
            f"Destinatario: {correo['receiver']}\n"
            f"Fecha: {correo['date']}\n"
            f"Cuerpo: {correo['body'][:500]}..."
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

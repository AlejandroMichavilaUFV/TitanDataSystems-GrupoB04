import os
import base64
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import Config # Se usa Config para obtener SCOPES

def autenticar_gmail():
    """Autentica con la API de Gmail y devuelve el servicio de Gmail."""
    creds = None
    token_path = "token.json"
    credentials_path = "credentials.json"

    try:
        # Cargar credenciales previas si existen
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, Config.GOOGLE_SCOPES)

        # Si las credenciales no son válidas, refrescarlas o solicitar nuevas
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, Config.GOOGLE_SCOPES)
                creds = flow.run_local_server(port=0)

            # Guardamos las credenciales en un archivo
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)
    
    except Exception as e:
        print(f"Error al autenticar en Gmail: {e}")
        return None

def mandarCorreo(asunto, cuerpo, destinatario, copia=None):
    """
    Envía un correo usando la API de Gmail.

    :param asunto: Asunto del correo.
    :param cuerpo: Cuerpo del correo (texto plano o HTML).
    :param destinatario: Dirección del destinatario (str o lista).
    :param copia: Dirección en copia (str o lista, opcional).
    :return: True si el correo se envió correctamente, False si hubo un error.
    """
    service = autenticar_gmail()
    if not service:
        print("No se pudo autenticar en Gmail. Verifica las credenciales.")
        return False

    try:
        # Asegurar que destinatario y copia sean listas
        if isinstance(destinatario, str):
            destinatario = [destinatario]
        if isinstance(copia, str):
            copia = [copia]

        # Crear el mensaje MIME
        mensaje = MIMEMultipart()
        mensaje["Subject"] = asunto
        mensaje["From"] = Config.GOOGLE_CLIENT_ID or "tuemail@gmail.com"  # Opcional: obtener remitente de config
        mensaje["To"] = ", ".join(destinatario)
        if copia:
            mensaje["Cc"] = ", ".join(copia)
        
        mensaje.attach(MIMEText(cuerpo, "plain"))

        # Codificar el mensaje en Base64 para la API de Gmail
        raw_message = base64.urlsafe_b64encode(mensaje.as_bytes()).decode("utf-8")
        message_body = {"raw": raw_message}

        # Enviar el correo
        service.users().messages().send(userId="me", body=message_body).execute()

        print("Correo enviado con éxito")
        return True

    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return False

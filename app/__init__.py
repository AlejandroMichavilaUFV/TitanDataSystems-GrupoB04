from flask import Flask, session
from config import Config
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=Config.GOOGLE_CLIENT_ID,
    client_secret=Config.GOOGLE_CLIENT_SECRET,
    server_metadata_url=Config.GOOGLE_DISCOVERY_URL,
    client_kwargs={
        'scope': 'openid email profile',
    }
)

# Importar rutas después de inicializar `app`
from app import routes

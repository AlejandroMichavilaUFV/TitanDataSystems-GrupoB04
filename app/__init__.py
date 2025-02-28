from flask import Flask, session
from config import Config

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Importar rutas después de inicializar `app`
from app import routes

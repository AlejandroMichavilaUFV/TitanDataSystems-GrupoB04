from flask import render_template, redirect, url_for, session, request
from google.oauth2.credentials import Credentials
from app import app
from app.auth import get_authorization_url, exchange_code_for_token, get_user_profile

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
    """Muestra el perfil del usuario autenticado."""
    if 'credentials' not in session:
        return redirect(url_for('index'))

    creds = Credentials(**session['credentials'])
    profile = get_user_profile(creds)
    return render_template('profile.html', profile=profile)

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

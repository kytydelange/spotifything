from app import db
from flask import session, abort, request, current_app
import datetime
from app.models import Session
import base64
import os
from urllib.parse import urlencode, urlparse, urljoin
import random
import hashlib
from cryptography.fernet import Fernet
import requests
from flask_login import current_user


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def invalid_request(resp):
    return resp.get('error', None)


def create_verifier_challenge():
    length = random.randint(60, 80)
    verifier_bytes = os.urandom(length)
    verifier = base64.urlsafe_b64encode(verifier_bytes).rstrip(b'=')
    challenge_bytes = hashlib.sha256(verifier).digest()
    challenge = base64.urlsafe_b64encode(challenge_bytes).rstrip(b'=')
    return verifier, challenge


def create_state():
    return base64.urlsafe_b64encode(os.urandom(6)).rstrip(b'=').decode()


def construct_authorization_uri(state, challenge):
    base_uri = 'https://accounts.spotify.com/authorize'
    query_parameters = {
        'client_id': current_app.config['CLIENT_ID'],
        'response_type': 'code',
        'redirect_uri': current_app.config['REDIRECT_URI'],
        'code_challenge_method': 'S256',
        'code_challenge': challenge,
        'state': state,
        'scope': f'playlist-modify-public, user-top-read'
    }
    query = urlencode(query_parameters)
    return f'{base_uri}?{query}'


def token_expired(user):
    now = datetime.datetime.now()
    return now > user.expiry or user.token is None


def get_access_token():
    user = current_user
    if user.token and not token_expired(user):
        f = Fernet(session['key'])
        return f.decrypt(user.token).decode('utf-8')

    if user.token and token_expired(user):
        get_refresh_token()
        return get_access_token()


def get_initial_token(code):
    user = Session.query.filter_by(session_id=session['session_id']).first()
    endpoint = 'https://accounts.spotify.com/api/token'
    params = {
        'client_id': current_app.config['CLIENT_ID'],
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': current_app.config['REDIRECT_URI'],
        'code_verifier': user.verifier
    }
    response = requests.post(endpoint, data=params).json()
    if invalid_request(response):
        session.clear()
        abort(500)
    else:
        f = Fernet(session['key'])
        token = f.encrypt(response['access_token'].encode())
        user.token = token
        user.refresh_token = f.encrypt(response['refresh_token'].encode())
        expires_in = response['expires_in']
        now = datetime.datetime.now()
        user.expiry = now + datetime.timedelta(seconds=expires_in)
        db.session.commit()
        return token


def get_refresh_token():
    user = current_user
    f = Fernet(session['key'])
    endpoint = 'https://accounts.spotify.com/api/token'
    refresh_params = {
        'grant_type': 'refresh_token',
        'refresh_token': f.decrypt(user.refresh_token).decode('utf-8'),
        'client_id': current_app.config['CLIENT_ID']
    }
    response = requests.post(endpoint, data=refresh_params).json()
    if invalid_request(response):
        session.clear()
        db.session.commit()
        abort(500)
    else:
        f = Fernet(session['key'])
        user.token = f.encrypt(response['access_token'].encode())
        user.refresh_token = f.encrypt(response['refresh_token'].encode())
        expires_in = response['expires_in']
        now = datetime.datetime.now()
        user.expiry = now + datetime.timedelta(seconds=expires_in)
        db.session.commit()
        pass


def register_user(token):
    f = Fernet(session['key'])
    endpoint = 'https://api.spotify.com/v1/me'
    headers = {'Authorization': f'Bearer {f.decrypt(token).decode("utf-8")}'}
    profile = requests.get(endpoint, headers=headers).json()
    return profile['id']


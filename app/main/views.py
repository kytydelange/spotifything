from flask import Blueprint, render_template, redirect, url_for
from app.main.utils import *
from app.models import Session
from app.extensions import db, login_manager
from flask_login import current_user, login_user, logout_user


main = Blueprint('main', __name__)


@main.route('/')
def home():
    return render_template('home.html')


@main.route('/about')
def about():
    return render_template('about.html')


@login_manager.user_loader
def load_user(session_id):
    return Session.query.filter_by(session_id=session_id).first()


@main.route('/connect')
def connect():
    session['next'] = request.args.get('next')
    if not current_user.is_authenticated:
        state = create_state()
        verifier, challenge = create_verifier_challenge()
        auth_uri = construct_authorization_uri(state, challenge)
        session_id = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b'=').decode()
        session['session_id'] = session_id
        key = Fernet.generate_key()
        session['key'] = key
        session.permanent = True
        user = Session(session_id=session_id, state=state, verifier=verifier)
        db.session.add(user)
        db.session.commit()
        return redirect(auth_uri)
    else:
        return redirect('/')


@main.route('/callback')
def callback():
    user = Session.query.filter_by(session_id=session['session_id']).first()
    if request.args.get('error'):
        return redirect(url_for('main.home'))
    if not user.token:
        code = request.args.get('code')
        state = request.args.get('state')
        if state == user.state:
            token = get_initial_token(code)
            user.user = str(register_user(token))
            db.session.commit()
            login_user(user)
            if session.get('next'):
                if is_safe_url(session["next"]):
                    return redirect(f'{request.url_root}{session["next"]}')
                else:
                    abort(400)
            return redirect(url_for('main.home'))
        else:
            raise Exception('Invalid state')
    else:
        return redirect('/')


@main.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('main.home'))


def add_custom_cover(pl_id, pl_type, token):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'image/jpeg'
    }
    with open(f'app/features/cover_{pl_type}.jpg', 'rb') as image_file:
        image_data = base64.b64encode(image_file.read())
    url = f'https://api.spotify.com/v1/playlists/{pl_id}/images'
    res = requests.put(url, headers=headers, data=image_data)
    return res.status_code


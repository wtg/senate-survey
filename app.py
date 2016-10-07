from functools import wraps
from flask import Flask, session, redirect, url_for, request, jsonify
from flask_cas import CAS, login_required, login, logout

import hashlib
import os


def get_pepper():
    try:
        return os.environ['CC_SURVEY_PEPPER']
    except:
        return None

app = Flask(__name__)
cas = CAS(app)
app.config['CAS_SERVER'] = 'https://cas-auth.rpi.edu/cas/'
app.config['CAS_AFTER_LOGIN'] = 'hashing'


def hash_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'hashed' in session:
            return f(*args, **kwargs)
        return login()
    return decorated_function


def check_pepper(f):
    @wraps(f)
    def func(*args, **kwargs):
        if get_pepper() is None:
            return not_configured()
        return f(*args, **kwargs)
    return func


@app.route('/hashing')
@login_required
def hashing():
    """Generate a hash of the user's RCS ID.

    Appends a pepper from the environment. This makes it harder to brute-force
    RCS IDs to reverse these hashes, assuming that the pepper is kept secret.
    """
    pepper = get_pepper()
    if pepper is None:
        return not_configured()
    to_hash = cas.username + pepper
    session['hashed'] = hashlib.md5(to_hash.encode()).hexdigest()
    return redirect(url_for('form'))


@app.route("/data")
@hash_login_required
def data():
    return jsonify({'q2b': 'test'}), 200


@app.route('/form', methods=['GET', 'POST'])
@check_pepper
@hash_login_required
def form():
    if request.method == 'POST':
        print(session['hashed'])
        print(request.form)
        return 'OK'
    else:
        return app.send_static_file('form.html')


def not_configured():
    return 'Counseling Center Survey not configured.'

# set the secret key.  keep this really secret:
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

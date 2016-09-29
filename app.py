from functools import wraps
from flask import Flask, session, redirect, url_for, request, jsonify
from flask_cas import CAS, login_required, login, logout

import hashlib

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

@app.route('/hashing')
@login_required
def hashing():
    session['hashed'] = hashlib.md5(cas.username.encode()).hexdigest()
    return redirect(url_for('form'))

@app.route("/data")
@hash_login_required
def data():
    return jsonify({'q2b': 'test'}), 200

@app.route('/form', methods=['GET', 'POST'])
@hash_login_required
def form():
    if request.method == 'POST':
        print(session['hashed'])
        print(request.form)
        return 'OK'
    else:
        return app.send_static_file('form.html')

# set the secret key.  keep this really secret:
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

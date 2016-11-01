from functools import wraps
from flask import Flask, session, redirect, url_for, request, jsonify, render_template
from flask_cas import CAS, login_required, login, logout

import hashlib
import json
import os

import models


def get_pepper():
    try:
        return os.environ['CC_SURVEY_PEPPER']
    except:
        return None

app = Flask(__name__)
cas = CAS(app)
app.config['CAS_SERVER'] = 'https://cas-auth.rpi.edu/cas/'
app.config['CAS_AFTER_LOGIN'] = 'form'
SURVEY_VERSION = 2


def hash_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session['hash'] = hash()
        return f(*args, **kwargs)
    return decorated_function


def check_pepper(f):
    @wraps(f)
    def func(*args, **kwargs):
        if get_pepper() is None:
            return not_configured()
        return f(*args, **kwargs)
    return func


def hash():
    """Generate a hash of the user's RCS ID.

    Appends a pepper from the environment. This makes it harder to brute-force
    RCS IDs to reverse these hashes, assuming that the pepper is kept secret.
    The survey version is also included in the hash so that a new version of
    the survey can be taken by someone who has taken a previous version.
    """
    pepper = get_pepper()
    if pepper is None:
        return not_configured()
    to_hash = cas.username + pepper + str(SURVEY_VERSION)
    return hashlib.md5(to_hash.encode()).hexdigest()


@app.route("/data")
@login_required
def data():
    return jsonify({'q2b': 'test'}), 200


@app.route('/form', methods=['GET', 'POST'])
@check_pepper
@login_required
@hash_request
def form():
    with models.db.atomic():
        # Check if a submission from this user has already been received.
        # This and inserting new submissions should be done atomically to avoid
        # race conditions with multiple submissions from the same user at the
        # same time.
        if len((models.UserHash
                .select()
                .where(models.UserHash.hash == session['hash']))) != 0:
            return render_template('message.html',
                                   message="You've already responded to this survey.",
                                   title='Already responded')

        # Insert into database if UserHash is new
        if request.method == 'POST':

            # No previous submission; record this one.
            models.UserHash().create(hash=session['hash'])

            # Dump form to JSON
            form_json = json.dumps(request.form)
            models.Submission().create(form=form_json, version=SURVEY_VERSION)

            return render_template('message.html', message="""Your submission has
                been recorded. Thank you for your participation in the survey
                and your contribution to improving the student experience at
                Rensselaer.""", title='Submission recorded')

        else:
            return render_template('form.html',
                                   title='Take survey')


@app.route('/form/<auth_key>', methods=['GET', 'POST'])
@check_pepper
def form_auth_key(auth_key):
    with models.db.atomic():
        # Check if this is a valid survey authorization key.
        # This and inserting new submissions should be done atomically to avoid
        # race conditions with multiple submissions with the same key at the
        # same time.
        key_models = (models.AuthorizationKey
                      .select()
                      .where(models.AuthorizationKey.key == auth_key))
        if len(key_models) != 1:
            return render_template('message.html',
                                   message="Invalid authorization key.",
                                   title='Not authorized')

        # Insert into database if UserHash is new
        if request.method == 'POST':

            # Delete this authorization key. We can assume len == 0 because of
            # the check a few lines above.
            key_models[0].delete_instance()

            # Dump form to JSON
            form_json = json.dumps(request.form)
            models.Submission().create(form=form_json, version=SURVEY_VERSION)

            return render_template('message.html', message="""Your submission has
                been recorded. Thank you for your participation in the survey
                and your contribution to improving the student experience at
                Rensselaer.""", title='Submission recorded')

        else:
            return render_template('form.html',
                                   title='Take survey')


@app.route('/')
def index():
    return render_template('index.html')


def not_configured():
    return render_template('message.html',
                           title='Not configured',
                           message='Counseling Center Survey not configured.')

# set the secret key.  keep this really secret:
app.secret_key = os.environ['SECRET_KEY']

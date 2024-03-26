from functools import wraps
from flask import Flask, render_template

from flask_cas import CAS

import functools
import json
import os

@functools.lru_cache(maxsize=1)
def get_survey():
    with open('survey.json', 'r') as f:
        return json.load(f)


def login_required_stub(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print("Skipping login requirements in debug mode…")
        return f(*args, **kwargs)
    return decorated_function

DEBUG_USERNAME = os.getenv('DEBUG_USERNAME')
if DEBUG_USERNAME:
    if input("Change username for testing?: ").strip().lower() == "y":
        DEBUG_USERNAME = input("New username: ")
    print(f"Debug mode is active with username “{DEBUG_USERNAME}”")
    login_required = login_required_stub
else:
    from flask_cas import login_required

app = Flask(__name__)
cas = CAS(app)
app.config['CAS_SERVER'] = 'https://cas.auth.rpi.edu'
app.config['CAS_AFTER_LOGIN'] = '/'
app.config['CAS_LOGIN_ROUTE'] = "/cas/login"
SURVEY_VERSION = 1

CC_SURVEY_ADMINS = set(os.getenv('SURVEY_ADMINS', '').split(','))
SAMPLE_POPULATION = set(os.getenv('SAMPLE_POPULATION', '').split(','))
CLOSED = os.getenv('SURVEY_CLOSED') == 'True'
CMS_API_KEY = os.getenv('CMS_API_KEY', '')

# Index page
@app.route('/')
def index():
    if CLOSED:
        # Return closed survey template if applicable
        return render_template('closed.html')
    return render_template('index.html')


# Set the secret key for cookies. keep this really secret, as the integrity of
# the survey relies on its being unknown to clients.
app.secret_key = os.environ['SECRET_KEY']

# import blueprints and register blueprints
from export import export
from form import form
from home import home

app.register_blueprint(export)
app.register_blueprint(form)
app.register_blueprint(home)

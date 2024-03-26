import hashlib
import requests
import json
from functools import wraps
from os import getenv
from flask import Blueprint, redirect, render_template, request, session


import models as models
from app import (
    login_required,
    get_survey,
    cas,
    CLOSED,
    CC_SURVEY_ADMINS,
    DEBUG_USERNAME,
    CMS_API_KEY,
    SAMPLE_POPULATION,
    SURVEY_VERSION
)


form = Blueprint('form', __name__, url_prefix='/form')


def not_configured():
    return render_template('message.html',
                           title='Not configured',
                           message='Survey not configured.')

def hash_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session['hash'] = hash()
        return f(*args, **kwargs)
    return decorated_function


def check_pepper(f):
    @wraps(f)
    def func(*args, **kwargs):
        if getenv('SURVEY_PEPPER') is None and not DEBUG_USERNAME:
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
    pepper = getenv('SURVEY_PEPPER')
    if pepper is None:
        return not_configured()
    username = cas.username if cas.username else DEBUG_USERNAME
    to_hash = username + pepper + str(SURVEY_VERSION)
    return hashlib.md5(to_hash.encode()).hexdigest()

@form.route('/', methods=['GET', 'POST'])
@check_pepper
@login_required
@hash_request
def form_index():
    username = cas.username if cas.username else DEBUG_USERNAME
    if CLOSED:
        # see if this user is in CC_SURVEY_ADMINS
        if request.method == 'GET' and username in CC_SURVEY_ADMINS:
            # allow admins to see the form, but not submit
            pass
        else:
            # Redirect all /form paths to / if survey is closed
            return redirect('/')


    # Check if this user is a student according to CMS
    rcs_id = username.lower()
    if not DEBUG_USERNAME:
        headers = {'Authorization': f'Token {CMS_API_KEY}'}
        r = requests.get(f'https://cms.union.rpi.edu/api/users/view_rcs/{rcs_id}/',
                        headers=headers)
        user_type = r.json()['user_type']
        if user_type != 'Student' or DEBUG_USERNAME:
            if not username in CC_SURVEY_ADMINS and request.method == 'GET':
                return render_template('message.html', message="""This survey is only
                    available to students.""", title='Survey not available')
            if request.method == 'POST':
                return render_template('message.html', message="""This survey is only
                    available to students. Admins may only view.""", title='Survey not available')

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
            form = {}
            for key in request.form.keys():
                lst = request.form.getlist(key)
                if key.endswith('[]'):
                    form[key] = lst
                else:
                    assert(len(lst) == 1)
                    val = lst[0]
                    if val == '':
                        continue
                    form[key] = val
            form_json = json.dumps(form)

            if username in SAMPLE_POPULATION:
                models.Submission().create(form=form_json, version=SURVEY_VERSION, sample=1)
            else:
                models.Submission().create(form=form_json, version=SURVEY_VERSION, sample=0)

            return render_template('message.html', message="""Your submission has
                been recorded anonymously. Thank you for sharing your voice
                and your contribution to improving the student experience at
                Rensselaer.""", title='Submission recorded')

        else:
            survey = get_survey()
            return render_template('form.html',
                                   title='Take survey',
                                   survey=survey)
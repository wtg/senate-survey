from functools import wraps
from flask import (
    abort,
    Flask,
    redirect,
    render_template,
    request,
    Response,
    send_file,
    session,
)
from flask_cas import CAS, login_required
import requests
import xlsxwriter

import csv
import datetime
import functools
import hashlib
import io
import json
import os
import uuid

import models


def get_pepper():
    try:
        return os.environ['SURVEY_PEPPER']
    except KeyError:
        return None


@functools.lru_cache(maxsize=1)
def get_survey():
    with open('survey.json', 'r') as f:
        return json.load(f)


def json_serializer(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError('{} is not JSON serializable'.format(type(obj)))


app = Flask(__name__)
cas = CAS(app)
app.config['CAS_SERVER'] = 'https://cas.auth.rpi.edu/cas/'
app.config['CAS_AFTER_LOGIN'] = 'form'
SURVEY_VERSION = 1

CC_SURVEY_ADMINS = set(os.getenv('SURVEY_ADMINS', '').split(','))
SAMPLE_POPULATION = set(os.getenv('SAMPLE_POPULATION', '').split(','))
CLOSED = os.getenv('SURVEY_CLOSED') == 'True'
CMS_API_KEY = os.getenv('CMS_API_KEY', '')


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


def get_question_for_key(key):
    orig_key = key # keep original key to append to question before return

    # strip list notation from multiple choice questions to get original q
    if key.endswith('[]'):
        key = key[:-2]

    # strip other to get original q
    if key.endswith('other'):
        key = key[:-5]
    survey = get_survey()
    for question in [item for sublist in survey for item in sublist]:
        if question['id'] == key:
            return question['question'] + ' ({})'.format(orig_key)
            if other:
                q += ' (other)'
            return q
    return key


@app.route('/form', methods=['GET', 'POST'])
@check_pepper
@login_required
@hash_request
def form():
    if CLOSED:
        # see if this user is in CC_SURVEY_ADMINS
        if request.method == 'GET' and cas.username in CC_SURVEY_ADMINS:
            # allow admins to see the form, but not submit
            pass
        else:
            # Redirect all /form paths to / if survey is closed
            return redirect('/')


    # Check if this user is a student according to CMS
    rcs_id = cas.username.lower()
    headers = {'Authorization': f'Token {CMS_API_KEY}'}
    r = requests.get(f'https://cms.union.rpi.edu/api/users/view_rcs/{rcs_id}/',
                     headers=headers)
    user_type = r.json()['user_type']
    if user_type != 'Student':
        if not cas.username in CC_SURVEY_ADMINS and request.method == 'GET':
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

            if cas.username in SAMPLE_POPULATION:
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

            if cas.username in SAMPLE_POPULATION:
                models.Submission().create(form=form_json, version=SURVEY_VERSION, sample=1)
            else:
                models.Submission().create(form=form_json, version=SURVEY_VERSION, sample=0)

            return render_template('message.html', message="""Your submission has
                been recorded anonymously. Thank you for your participation in the survey
                and your contribution to improving the student experience at
                Rensselaer.""", title='Submission recorded')

        else:
            return render_template('form.html',
                                   title='Take survey')


@app.route('/export')
# UNCOMMENT
# @login_required
def export():
    # see if this user is in CC_SURVEY_ADMINS
    # UNCOMMENT
    # if cas.username not in CC_SURVEY_ADMINS:
    #     abort(403)
    return render_template('export.html')


@app.route('/export.csv')
@login_required
def export_csv():
    def generate():
        # loop through all submissions
        submissions = models.Submission.select().order_by(models.Submission.time.desc())

        # build header. have to loop through everything because CSV
        header = ['id', 'time', 'version', 'sample'] # CSV header containing all questions/keys
        for submission in submissions:
            # form is stored as JSON, so extract responses
            form_js = json.loads(submission.form)

            # if we only want responses to some questions, include only those
            for key, value in form_js.items():
                if (question_prefix is None and not key.startswith('raffle')) \
                        or (question_prefix is not None and key.startswith(question_prefix)):
                    question = get_question_for_key(key)
                    if question not in header:
                        header.append(question)

        # output CSV
        line = io.StringIO()
        w = csv.DictWriter(line, header)
        w.writeheader()

        # loop through submissions again and stream output to client
        for submission in submissions:
            sub = {}
            sub['id'] = submission.id
            sub['time'] = submission.time
            sub['version'] = submission.version
            sub['sample'] = submission.sample

            # form is stored as JSON, so extract responses
            form_js = json.loads(submission.form)

            # if we only want responses to some questions, include only those
            for key, value in form_js.items():
                if (question_prefix is None and not key.startswith('raffle')) \
                        or (question_prefix is not None and key.startswith(question_prefix)):
                    question = get_question_for_key(key)
                    sub[question] = value

            # write CSV row
            w.writerow(sub)
            line.seek(0)
            yield line.read()
            line.seek(0)
            line.truncate(0)


    # see if this user is in CC_SURVEY_ADMINS
    if cas.username not in CC_SURVEY_ADMINS:
        abort(403)

    question_prefix = request.args.get('question_prefix')
    # attachment filename
    if question_prefix is None:
        filename = 'senate-survey.csv'
    else:
        filename = 'senate-survey-{}.csv'.format(question_prefix)

    response = Response(generate(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=' + filename
    return response


@app.route('/export.xlsx')
# @login_required
def export_xlsx():
    # see if this user is in CC_SURVEY_ADMINS
    # uncomment
    # if cas.username not in CC_SURVEY_ADMINS:
    #     abort(403)

    question_prefix = request.args.get('question_prefix')
    # attachment filename
    if question_prefix is None:
        filename = 'senate-survey.xlsx'
    else:
        filename = 'senate-survey-{}.xlsx'.format(question_prefix)

    # loop through all submissions
    submissions = models.Submission.select().order_by(models.Submission.time.desc())

    # build header. have to loop through everything first
    header = ['id', 'time', 'version', 'sample'] # header containing all questions/keys
    for submission in submissions:
        # form is stored as JSON, so extract responses
        form_js = json.loads(submission.form)

        # if we only want responses to some questions, include only those
        for key, value in form_js.items():
            if (question_prefix is None and not key.startswith('raffle')) \
                    or (question_prefix is not None and key.startswith(question_prefix)):
                question = get_question_for_key(key)
                if question not in header:
                    header.append(question)

    # output Excel file
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'constant_memory': True,
                                            'strings_to_numbers': True})
    worksheet = workbook.add_worksheet()

    # write header
    row, col = 0, 0
    for field in header:
        worksheet.write(row, col, field)
        col += 1
    row += 1

    # loop through submissions again and stream output to client
    for submission in submissions:
        sub = {}
        sub['id'] = submission.id
        sub['time'] = submission.time
        sub['version'] = submission.version
        sub['sample'] = submission.sample

        # form is stored as JSON, so extract responses
        form_js = json.loads(submission.form)

        # if we only want responses to some questions, include only those
        for key, value in form_js.items():
            if (question_prefix is None and not key.startswith('raffle')) \
                    or (question_prefix is not None and key.startswith(question_prefix)):
                question = get_question_for_key(key)
                sub[question] = value

        # write CSV row
        for field, value in sub.items():
            for i in range(len(header)):
                h_field = header[i]
                if h_field == field:
                    worksheet.write(row, i, str(value))
                    break

        row += 1

            # yield output.read()

        # w.writerow(sub)
        # line.seek(0)
        # yield line.read()
        # line.truncate(0)
    workbook.close()

    response = Response(output.getvalue(),
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response.headers['Content-Disposition'] = 'attachment; filename=' + filename
    return response


@app.route('/export.json')
@login_required
def export_json():
    # see if this user is in CC_SURVEY_ADMINS
    if cas.username not in CC_SURVEY_ADMINS:
        abort(403)

    # loop through all submissions and make a dict for each, then append to list
    submissions = models.Submission.select().order_by(models.Submission.time.desc())

    exp = []
    for submission in submissions:
        sub = {}
        sub['id'] = submission.id
        sub['time'] = submission.time
        sub['version'] = submission.version
        sub['sample'] = submission.sample

        # form is stored as JSON, so extract responses
        form_js = json.loads(submission.form)

        # if we only want responses to some questions, include only those, but exclude raffle
        question_prefix = request.args.get('question_prefix')
        for key, value in form_js.items():
            if (question_prefix is None and not key.startswith('raffle')) \
                    or (question_prefix is not None and key.startswith(question_prefix)):
                question = get_question_for_key(key)
                sub[question] = value

        exp.append(sub)

    # output JSON
    f = io.StringIO()
    json.dump({'responses': exp}, f, default=json_serializer)

    # there must be a better way to do this than StringIO -> str -> BytesIO
    return send_file(io.BytesIO(f.getvalue().encode('utf-8')),
                     mimetype='application/json')


@app.route('/')
def index():
    if CLOSED:
        # Return closed survey template if applicable
        return render_template('closed.html')
    return render_template('index.html')


def not_configured():
    return render_template('message.html',
                           title='Not configured',
                           message='Survey not configured.')


# Set the secret key for cookies. keep this really secret, as the integrity of
# the survey relies on its being unknown to clients.
app.secret_key = os.environ['SECRET_KEY']

import csv
import datetime
import io
import json
import uuid

import xlsxwriter
from flask import (
    abort, 
    render_template, 
    send_file,
    request, 
    Blueprint, 
    Response, 
)

import models
from app import (
    get_survey, 
    login_required,
    cas,
    CC_SURVEY_ADMINS, 
    DEBUG_USERNAME,
)

export = Blueprint('export', __name__, url_prefix='/export')


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

def json_serializer(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError('{} is not JSON serializable'.format(type(obj)))

def not_configured():
    return render_template('message.html',
                           title='Not configured',
                           message='Survey not configured.')

@export.route('/')
@login_required
def index():
    username = cas.username if cas.username else DEBUG_USERNAME
    # see if this user is in CC_SURVEY_ADMINS
    if username not in CC_SURVEY_ADMINS and not DEBUG_USERNAME:
        abort(403)
    return render_template('export.html')


@export.route('/export.xlsx')
@login_required
def export_xlsx():
    username = cas.username if cas.username else DEBUG_USERNAME
    # see if this user is in CC_SURVEY_ADMINS
    if username not in CC_SURVEY_ADMINS and not DEBUG_USERNAME:
        abort(403)

    question_prefix = request.args.get('question_prefix')
    # attachment filename
    if question_prefix is None:
        filename = 'senate-survey.xlsx'
    else:
        filename = 'senate-survey-{}.xlsx'.format(question_prefix)

    # loop through all submissions
    submissions = [submission for submission in models.Submission.select()]
    submissions.sort(key=lambda submission: submission.time)

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

@export.route('/export.csv')
@login_required
def export_csv():
    def generate():
        # loop through all submissions
        # TODO could use list - find out which one is more efficient
        submissions = [submission for submission in models.Submission.select()]
        submissions.sort(key=lambda submission: submission.time)

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

    username = cas.username if cas.username else DEBUG_USERNAME

    # see if this user is in CC_SURVEY_ADMINS
    if username not in CC_SURVEY_ADMINS and not DEBUG_USERNAME:
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


@export.route('/export.json')
@login_required
def export_json():
    username = cas.username if cas.username else DEBUG_USERNAME

    # see if this user is in CC_SURVEY_ADMINS
    if username not in CC_SURVEY_ADMINS and not DEBUG_USERNAME:
        abort(403)

    # loop through all submissions and make a dict for each, then append to list
    submissions = list(models.Submission.select())
    submissions.sort(key=lambda submission: submission.time)

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


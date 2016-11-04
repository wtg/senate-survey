# Counseling Center Survey

This survey aims to gather student opinions on the quality of care and the ease of access of counseling at RPI. It is online at https://ccsurvey.union.rpi.edu.

## Anonymity

All survey submissions are stored in a way that prevents a user from submitting
multiple times, but does not link any specific user to a submission.

The user's ID is hashed, along with a pepper and the current survey version, and
stored in a table upon submission. The survey answers are stored in a separate
table without a link to the ID hash. The survey submissions are timestamped, but
the hashes are not. Additionally, the submission and hash database table's
primary keys are randomized and not related in any way to each other.

The benefit of this is that it is not possible to determine who has submitted
a survey, let alone link a specific response with an individual.

A drawback is that it is impossible to edit or delete a specific survey
response.

## Configuration

The following environment variables must be defined:

- **CC_SURVEY_ADMINS** — Comma-separated list of RCS IDs that are permitted to
download submissions from `/export` (e.g. `KOCHMS,ETZINJ`).
- **CC_SURVEY_PEPPER** — Appended to user ID before hashing. This makes it more
difficult to map user IDs to hashes. This must not change or it will be possible
for people to retake the survey.
- **DATABASE_URL** — Database connection URL.
- **SECRET_KEY** — Used to sign session cookies.

## Development

First, ensure that the above environment variables are defined. Then:

```
pip install -r requirements.txt
gunicorn app:app --reload -k gevent
```

It is a good idea to do this inside of a virtual environment.

## Deployment

Counseling Center Survey can be pushed to Dokku or Heroku. It has been tested
with SQLite and Postgres databases.

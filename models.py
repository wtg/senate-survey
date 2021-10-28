import datetime
import uuid
import os

import peewee
import playhouse.db_url

db = playhouse.db_url.connect(os.environ.get('DATABASE_URL') or 'sqlite:///cc-survey.db')

class BaseModel(peewee.Model):

    class Meta:
        database = db


class Submission(BaseModel):
    """Survey submission model.

    Uses a UUID for the ID instead of an integer sequence so that survey
    submissions cannot be linked to user hashes."""
    id = peewee.UUIDField(default=uuid.uuid4, primary_key=True)
    form = peewee.TextField()
    sample = peewee.IntegerField()
    time = peewee.DateTimeField(default=datetime.datetime.now)
    version = peewee.IntegerField()


class UserHash(BaseModel):
    """User hash model."""
    hash = peewee.TextField(primary_key=True)


class AuthorizationKey(BaseModel):
    """Can be created to allow users without RCS IDs to take the survey."""
    key = peewee.TextField(primary_key=True)


db.create_tables([Submission, UserHash, AuthorizationKey], safe=True)

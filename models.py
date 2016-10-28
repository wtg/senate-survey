import datetime
import uuid

import peewee

db = peewee.SqliteDatabase('cc-survey.db')


class BaseModel(peewee.Model):

    class Meta:
        database = db


class Submission(BaseModel):
    """Survey submission model.

    Uses a UUID for the ID instead of an integer sequence so that survey
    submissions cannot be linked to user hashes."""
    id = peewee.UUIDField(default=uuid.uuid4)
    form = peewee.TextField()
    time = peewee.DateTimeField(default=datetime.datetime.now)


class UserHash(BaseModel):
    """User hash model."""
    hash = peewee.TextField(primary_key=True)


class AuthorizationKey(BaseModel):
    """Can be created to allow users without RCS IDs to take the survey."""
    key = peewee.TextField(primary_key=True)


db.create_tables([Submission, UserHash, AuthorizationKey], safe=True)

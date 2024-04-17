from datetime import datetime
from uuid import uuid4
from os import getenv

from peewee import Model, UUIDField, TextField, IntegerField, DateTimeField
import playhouse.db_url

db = playhouse.db_url.connect(getenv('DATABASE_URL', 'sqlite:///cc-survey.db'))

class ModelBase(Model):
    class Meta:
        database = db


class Submission(ModelBase):
    """Survey submission model.

    Uses a UUID for the ID instead of an integer sequence so that survey
    submissions cannot be linked to user hashes."""
    id = UUIDField(default=uuid4, primary_key=True)
    form = TextField()
    sample = IntegerField()
    time = DateTimeField(default=datetime.now)
    version = IntegerField()


class UserHash(ModelBase):
    """User hash model."""
    hash = TextField(primary_key=True)

db.create_tables([Submission, UserHash], safe=True)

from App.database import db
from App.models import Admin, Institution


def initialize():
    db.drop_all()
    db.create_all()
    create_user('bob', 'test', 'bob', 'bob@email.com', 'bobpass')

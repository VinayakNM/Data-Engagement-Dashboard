from App.database import db
from App.models import Admin, Institution
from App.controllers.admin_controller import create_user_by_admin


def initialize():
    db.drop_all()
    db.create_all()
    create_user_by_admin(
        firstname='Bob',
        lastname='Test',
        username='bob',
        email='bob@email.com',
        password='bobpass',
        role='admin'
    )